from __future__ import annotations

from src.normalization.schema import CanonicalEvent


class ContextEnricher:
    """Adds stable exploit evidence signals for downstream consumers."""

    def enrich(self, event: CanonicalEvent) -> dict[str, list[str]]:
        exploit_evidence: list[str] = []
        if event.exploitation_in_wild:
            exploit_evidence.append("active_exploitation_reported")
        if event.poc_available:
            exploit_evidence.append("public_poc_available")
        if not exploit_evidence and event.cve_ids:
            exploit_evidence.append("cve_reported_no_exploit_confirmation")

        return {
            "exploit_evidence": exploit_evidence,
            "affected_vendors": sorted(set(event.vendors)),
            "affected_products": sorted(set(event.products)),
        }
