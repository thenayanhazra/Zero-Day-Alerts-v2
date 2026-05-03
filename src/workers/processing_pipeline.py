from __future__ import annotations

from datetime import datetime, timezone

from src.enrichment import ContextEnricher
from src.normalization.dedupe import DedupeEngine
from src.normalization.parser import normalize_raw_event
from src.normalization.store import EventStore
from src.scoring import RiskScorer
from src.storage.processed_event_store import ProcessedEvent
from src.storage.raw_event_store import RawEvent


class ProcessingPipeline:
    """Transforms raw collector events into deduped, scored, enriched processed events."""

    def __init__(self) -> None:
        self.normalized_store = EventStore(dedupe_engine=DedupeEngine())
        self.risk_scorer = RiskScorer()
        self.enricher = ContextEnricher()

    def process(self, raw_events: list[RawEvent]) -> list[ProcessedEvent]:
        processed: list[ProcessedEvent] = []
        for raw in raw_events:
            canonical = normalize_raw_event(raw)
            merged = self.normalized_store.ingest(
                raw=self._to_raw_record(raw),
                candidate=canonical,
            )
            risk_score, severity = self.risk_scorer.score(merged)
            context = self.enricher.enrich(merged)
            processed.append(
                ProcessedEvent(
                    event_id=merged.event_id,
                    source=raw.source,
                    title=merged.title,
                    description=merged.description,
                    severity=severity,
                    risk_score=risk_score,
                    confidence=merged.confidence,
                    cve_ids=merged.cve_ids,
                    vendors=context["affected_vendors"],
                    products=context["affected_products"],
                    exploit_evidence=context["exploit_evidence"],
                    references=merged.source_refs,
                    processed_at=datetime.now(timezone.utc),
                )
            )
        unique = {event.event_id: event for event in processed}
        return list(unique.values())

    @staticmethod
    def _to_raw_record(raw: RawEvent):
        from src.normalization.schema import RawRecord
        from src.normalization.parser import stable_text_digest

        return RawRecord(
            raw_id=f"raw-{stable_text_digest(str(raw.payload) + raw.title)[:18]}",
            source=raw.source,
            payload=raw.payload,
            ingested_at=datetime.now(timezone.utc),
        )
