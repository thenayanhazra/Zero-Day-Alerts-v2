from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class CanonicalEvent:
    """Canonical representation of a normalized security event."""

    event_id: str
    title: str
    description: str
    published_at: datetime | None = None
    observed_at: datetime | None = None
    source_refs: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    iocs: list[str] = field(default_factory=list)
    poc_available: bool = False
    exploitation_in_wild: bool = False
    confidence: float = 0.0


@dataclass(slots=True)
class RawRecord:
    """Raw source payload kept for auditability and traceability."""

    raw_id: str
    source: str
    payload: dict[str, Any]
    ingested_at: datetime


@dataclass(slots=True)
class RawToCanonicalMapping:
    """Many-to-one mapping from raw records to canonical event ids."""

    raw_id: str
    event_id: str
    mapped_at: datetime
