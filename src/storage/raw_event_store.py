"""Raw event storage primitives."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(slots=True)
class RawEvent:
    source: str
    title: str
    payload: dict


@dataclass(slots=True)
class ProcessedEvent:
    event_id: str
    source: str
    title: str
    payload: dict
    status: str = "new"
    updated_at: datetime | None = None


class RawEventStore(Protocol):
    """Storage contract for persisting raw collector events."""

    def write_many(self, events: Iterable[RawEvent]) -> int: ...


class InMemoryRawEventStore:
    """Temporary storage adapter for local development."""

    def __init__(self) -> None:
        self._events: list[RawEvent] = []

    def write_many(self, events: Iterable[RawEvent]) -> int:
        chunk = list(events)
        self._events.extend(chunk)
        return len(chunk)

    def count(self) -> int:
        return len(self._events)

    def all(self) -> list[RawEvent]:
        return list(self._events)


class SQLiteEventStore:
    """SQLite-backed storage adapter for raw and processed events."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._bootstrap()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _bootstrap(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    UNIQUE(source, title, payload_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_raw_events_ingested_at ON raw_events(ingested_at);

                CREATE TABLE IF NOT EXISTS processed_events (
                    event_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_processed_events_status ON processed_events(status);
                CREATE INDEX IF NOT EXISTS idx_processed_events_updated_at ON processed_events(updated_at);
                """
            )

    def _payload_json(self, payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def write_many(self, events: Iterable[RawEvent]) -> int:
        rows: list[tuple[str, str, str, str, str]] = []
        ingested_at = datetime.now(timezone.utc).isoformat()
        for event in events:
            payload_json = self._payload_json(event.payload)
            payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            rows.append((event.source, event.title, payload_json, payload_hash, ingested_at))

        if not rows:
            return 0

        with self._connect() as conn:
            cursor = conn.executemany(
                """
                INSERT OR IGNORE INTO raw_events(source, title, payload_json, payload_hash, ingested_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            return cursor.rowcount if cursor.rowcount != -1 else 0

    def all(self) -> list[RawEvent]:
        with self._connect() as conn:
            rows = conn.execute("SELECT source, title, payload_json FROM raw_events ORDER BY id ASC").fetchall()
            return [RawEvent(source=row["source"], title=row["title"], payload=json.loads(row["payload_json"])) for row in rows]

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM raw_events").fetchone()
            return int(row["c"])

    def upsert_processed_event(self, event: ProcessedEvent) -> ProcessedEvent:
        now = datetime.now(timezone.utc).isoformat()
        updated_at = event.updated_at.isoformat() if event.updated_at else now
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_events(event_id, source, title, payload_json, status, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    source=excluded.source,
                    title=excluded.title,
                    payload_json=excluded.payload_json,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (event.event_id, event.source, event.title, self._payload_json(event.payload), event.status, now, updated_at),
            )
        return self.get_processed_event(event.event_id)

    def get_processed_event(self, event_id: str) -> ProcessedEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT event_id, source, title, payload_json, status, updated_at FROM processed_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        return ProcessedEvent(
            event_id=row["event_id"],
            source=row["source"],
            title=row["title"],
            payload=json.loads(row["payload_json"]),
            status=row["status"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete_processed_event(self, event_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM processed_events WHERE event_id = ?", (event_id,))
            return cursor.rowcount > 0

    def list_processed_events(self, limit: int = 100, offset: int = 0) -> list[ProcessedEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, source, title, payload_json, status, updated_at
                FROM processed_events
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            ProcessedEvent(
                event_id=row["event_id"],
                source=row["source"],
                title=row["title"],
                payload=json.loads(row["payload_json"]),
                status=row["status"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
