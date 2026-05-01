"""Scoring engine for determining vulnerability handling priority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping

from .rules import DEFAULT_WEIGHTS, RULES, get_effective_weights


@dataclass(frozen=True)
class ScoringResult:
    severity_score: int
    priority_tier: str
    explanation: List[str]


def _to_component_score(value: object, weight: float) -> float:
    if isinstance(value, bool):
        return weight if value else 0.0
    if isinstance(value, (int, float)):
        normalized = max(0.0, min(float(value), 1.0))
        return normalized * weight
    return 0.0


def _tier_for_score(score: int) -> str:
    if score >= 75:
        return "P1"
    if score >= 40:
        return "P2"
    return "P3"


def score_alert(
    signals: Mapping[str, object],
    weights: Mapping[str, float] | None = None,
) -> ScoringResult:
    """Compute severity score, tier, and explanation from normalized signals.

    Signals can be booleans or normalized numeric values in [0, 1].
    """

    effective_weights: Dict[str, float] = get_effective_weights(weights)
    total_weight = sum(effective_weights.values()) or sum(DEFAULT_WEIGHTS.values())

    raw_score = 0.0
    explanation: List[str] = []

    for key, rule in RULES.items():
        value = signals.get(key, False)
        component = _to_component_score(value, effective_weights[key])
        raw_score += component
        if component > 0:
            explanation.append(
                f"{rule.description} (+{component:.1f}/{effective_weights[key]:.1f})"
            )

    normalized_score = int(round((raw_score / total_weight) * 100))
    normalized_score = max(0, min(normalized_score, 100))

    return ScoringResult(
        severity_score=normalized_score,
        priority_tier=_tier_for_score(normalized_score),
        explanation=explanation,
    )
