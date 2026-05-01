from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from difflib import SequenceMatcher
from hashlib import sha256

from .schema import CanonicalEvent


class DedupeEngine:
    def __init__(
        self,
        similarity_threshold: float = 0.78,
        cve_overlap_weight: float = 0.2,
        collapse_window_hours: int = 72,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.cve_overlap_weight = cve_overlap_weight
        self.collapse_window = timedelta(hours=collapse_window_hours)

    @staticmethod
    def fingerprint(event: CanonicalEvent) -> str:
        fields = [
            event.title.lower().strip(),
            " ".join(sorted(c.lower().strip() for c in event.cve_ids)),
            " ".join(sorted(v.lower().strip() for v in event.vendors)),
            " ".join(sorted(p.lower().strip() for p in event.products)),
            str(event.poc_available),
            str(event.exploitation_in_wild),
        ]
        material = "|".join(fields)
        return sha256(material.encode("utf-8")).hexdigest()

    def should_merge(self, a: CanonicalEvent, b: CanonicalEvent) -> bool:
        if not self._in_time_window(a, b):
            return False

        title_score = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
        content_score = SequenceMatcher(
            None,
            a.description.lower(),
            b.description.lower(),
        ).ratio()
        text_score = max(title_score, content_score)

        cve_overlap = self._jaccard(set(a.cve_ids), set(b.cve_ids))
        combined_score = text_score + (cve_overlap * self.cve_overlap_weight)

        return combined_score >= self.similarity_threshold

    def merge(self, primary: CanonicalEvent, incoming: CanonicalEvent) -> CanonicalEvent:
        merged = replace(primary)
        merged.title = primary.title if len(primary.title) >= len(incoming.title) else incoming.title
        merged.description = (
            primary.description
            if len(primary.description) >= len(incoming.description)
            else incoming.description
        )
        merged.published_at = min(
            [d for d in [primary.published_at, incoming.published_at] if d is not None],
            default=None,
        )
        merged.observed_at = min(
            [d for d in [primary.observed_at, incoming.observed_at] if d is not None],
            default=None,
        )
        merged.source_refs = sorted(set(primary.source_refs) | set(incoming.source_refs))
        merged.cve_ids = sorted(set(primary.cve_ids) | set(incoming.cve_ids))
        merged.vendors = sorted(set(primary.vendors) | set(incoming.vendors))
        merged.products = sorted(set(primary.products) | set(incoming.products))
        merged.iocs = sorted(set(primary.iocs) | set(incoming.iocs))
        merged.poc_available = primary.poc_available or incoming.poc_available
        merged.exploitation_in_wild = (
            primary.exploitation_in_wild or incoming.exploitation_in_wild
        )
        merged.confidence = max(primary.confidence, incoming.confidence)
        return merged

    def _in_time_window(self, a: CanonicalEvent, b: CanonicalEvent) -> bool:
        a_time = a.observed_at or a.published_at
        b_time = b.observed_at or b.published_at
        if a_time is None or b_time is None:
            return True
        return abs(a_time - b_time) <= self.collapse_window

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left and not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)
