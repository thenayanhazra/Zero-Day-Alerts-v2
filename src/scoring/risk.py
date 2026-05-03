from __future__ import annotations

from src.normalization.schema import CanonicalEvent


class RiskScorer:
    """Assigns a normalized 0-100 risk score and severity label."""

    def score(self, event: CanonicalEvent) -> tuple[float, str]:
        score = 15.0
        score += min(len(event.cve_ids), 4) * 10
        score += min(len(event.vendors), 3) * 3
        score += min(len(event.products), 3) * 3
        if event.poc_available:
            score += 18
        if event.exploitation_in_wild:
            score += 32
        score += min(max(event.confidence, 0.0), 1.0) * 19

        bounded = max(0.0, min(100.0, score))
        return bounded, self._severity_from_score(bounded)

    @staticmethod
    def _severity_from_score(score: float) -> str:
        if score >= 85:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 45:
            return "medium"
        return "low"
