from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(slots=True)
class RawPayload:
    """Normalized raw payload persisted before enrichment/scoring."""

    source_name: str
    source_type: str
    fetched_at: str
    raw_id: str
    raw_content: dict[str, Any]
    raw_url: str | None
    collector_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceMetadata:
    source_name: str
    source_type: str
    collector_version: str


class Collector(ABC):
    """Base collector contract.

    Collectors return normalized ``RawPayload`` objects that include source
    metadata required for durable raw persistence.
    """

    source_name: str
    source_type: str
    collector_version: str = "1.0.0"

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def normalize_raw_item(
        self,
        *,
        raw_id: str,
        raw_content: dict[str, Any],
        raw_url: str | None = None,
        fetched_at: str | None = None,
    ) -> RawPayload:
        return RawPayload(
            source_name=self.source_name,
            source_type=self.source_type,
            fetched_at=fetched_at or self.now_iso(),
            raw_id=raw_id,
            raw_content=raw_content,
            raw_url=raw_url,
            collector_version=self.collector_version,
        )

    @abstractmethod
    def fetch(self) -> Iterable[RawPayload]:
        """Collect source records and return normalized raw payloads."""
