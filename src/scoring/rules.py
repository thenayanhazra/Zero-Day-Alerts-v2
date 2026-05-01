"""Scoring rules and default weights for alert prioritization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class SignalRule:
    """Represents a single weighted signal used for severity scoring."""

    key: str
    weight: float
    description: str


DEFAULT_WEIGHTS: Dict[str, float] = {
    "kev_presence": 35.0,
    "active_exploitation_claims": 20.0,
    "poc_availability": 12.0,
    "exploit_kit_mention": 10.0,
    "vendor_criticality": 15.0,
    "source_trust_score": 8.0,
}


RULES: Dict[str, SignalRule] = {
    "kev_presence": SignalRule(
        key="kev_presence",
        weight=DEFAULT_WEIGHTS["kev_presence"],
        description="Included in CISA KEV catalog",
    ),
    "active_exploitation_claims": SignalRule(
        key="active_exploitation_claims",
        weight=DEFAULT_WEIGHTS["active_exploitation_claims"],
        description="Credible active exploitation claim observed",
    ),
    "poc_availability": SignalRule(
        key="poc_availability",
        weight=DEFAULT_WEIGHTS["poc_availability"],
        description="Public proof-of-concept exploit is available",
    ),
    "exploit_kit_mention": SignalRule(
        key="exploit_kit_mention",
        weight=DEFAULT_WEIGHTS["exploit_kit_mention"],
        description="Exploit kit or framework mentions this vulnerability",
    ),
    "vendor_criticality": SignalRule(
        key="vendor_criticality",
        weight=DEFAULT_WEIGHTS["vendor_criticality"],
        description="Impacted vendor/product has high business criticality or prevalence",
    ),
    "source_trust_score": SignalRule(
        key="source_trust_score",
        weight=DEFAULT_WEIGHTS["source_trust_score"],
        description="High trust reporting source",
    ),
}


def get_effective_weights(overrides: Mapping[str, float] | None = None) -> Dict[str, float]:
    """Return merged defaults + overrides for known weight keys."""

    merged = dict(DEFAULT_WEIGHTS)
    if overrides:
        for key, value in overrides.items():
            if key in merged:
                merged[key] = float(value)
    return merged
