"""Processed event storage primitives."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class ProcessedEvent:
    event_id: str
    source: str
    title: str
    description: str
    severity: str
    risk_score: float
    confidence: float
    cve_ids: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    exploit_evidence: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    processed_at: datetime | None = None


class ProcessedEventStore(Protocol):
    """Storage contract for persisting processed events."""

    def upsert_many(self, events: Iterable[ProcessedEvent]) -> int: ...


class InMemoryProcessedEventStore:
    """Temporary storage adapter for processed events in local development."""

    def __init__(self) -> None:
        self._events: dict[str, ProcessedEvent] = {}

    def upsert_many(self, events: Iterable[ProcessedEvent]) -> int:
        count = 0
        for event in events:
            self._events[event.event_id] = event
            count += 1
        return count

    def count(self) -> int:
        return len(self._events)

    def all(self) -> list[ProcessedEvent]:
        return list(self._events.values())
