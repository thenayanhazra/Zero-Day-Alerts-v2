"""Raw event storage primitives."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RawEvent:
    source: str
    title: str
    payload: dict


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
