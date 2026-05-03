"""Storage backend factory."""

from __future__ import annotations

from pathlib import Path

from src.config import Settings

from .raw_event_store import InMemoryRawEventStore, RawEventStore, SQLiteEventStore


def build_raw_event_store(settings: Settings) -> RawEventStore:
    if settings.storage_backend == "sqlite":
        db_path = Path(settings.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return SQLiteEventStore(str(db_path))
    return InMemoryRawEventStore()
