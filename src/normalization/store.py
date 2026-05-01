from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .dedupe import DedupeEngine
from .schema import CanonicalEvent, RawRecord, RawToCanonicalMapping


class EventStore:
    """In-memory store for raw records, canonical events, and mapping edges."""

    def __init__(self, dedupe_engine: DedupeEngine | None = None) -> None:
        self.dedupe_engine = dedupe_engine or DedupeEngine()
        self.raw_records: dict[str, RawRecord] = {}
        self.canonical_events: dict[str, CanonicalEvent] = {}
        self.raw_to_canonical: list[RawToCanonicalMapping] = []

    def ingest(self, raw: RawRecord, candidate: CanonicalEvent) -> CanonicalEvent:
        self.raw_records[raw.raw_id] = raw

        existing_id = self._find_merge_target(candidate)
        if existing_id is None:
            self.canonical_events[candidate.event_id] = replace(candidate)
            mapped_event_id = candidate.event_id
        else:
            current = self.canonical_events[existing_id]
            self.canonical_events[existing_id] = self.dedupe_engine.merge(current, candidate)
            mapped_event_id = existing_id

        self.raw_to_canonical.append(
            RawToCanonicalMapping(
                raw_id=raw.raw_id,
                event_id=mapped_event_id,
                mapped_at=datetime.utcnow(),
            )
        )
        return self.canonical_events[mapped_event_id]

    def _find_merge_target(self, candidate: CanonicalEvent) -> str | None:
        candidate_fp = self.dedupe_engine.fingerprint(candidate)
        for event_id, event in self.canonical_events.items():
            if self.dedupe_engine.fingerprint(event) == candidate_fp:
                return event_id
        for event_id, event in self.canonical_events.items():
            if self.dedupe_engine.should_merge(event, candidate):
                return event_id
        return None
