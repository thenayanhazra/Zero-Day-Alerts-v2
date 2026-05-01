"""Normalization pipeline for converting raw security alerts into canonical events."""

from .schema import CanonicalEvent, RawRecord, RawToCanonicalMapping
from .parser import parse_indicators
from .dedupe import DedupeEngine
from .store import EventStore

__all__ = [
    "CanonicalEvent",
    "RawRecord",
    "RawToCanonicalMapping",
    "parse_indicators",
    "DedupeEngine",
    "EventStore",
]
