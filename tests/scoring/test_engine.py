from src.scoring.engine import score_alert


def test_empty_signals_is_p3_zero_score():
    result = score_alert({})
    assert result.severity_score == 0
    assert result.priority_tier == "P3"
    assert result.explanation == []


def test_high_risk_combination_is_p1():
    result = score_alert(
        {
            "kev_presence": True,
            "active_exploitation_claims": True,
            "poc_availability": True,
            "exploit_kit_mention": True,
            "vendor_criticality": 1.0,
            "source_trust_score": 1.0,
        }
    )
    assert result.severity_score == 100
    assert result.priority_tier == "P1"
    assert len(result.explanation) == 6


def test_mixed_weighted_signals_are_normalized_and_tiered():
    result = score_alert(
        {
            "kev_presence": True,
            "vendor_criticality": 0.5,
            "source_trust_score": 0.5,
        }
    )
    assert result.severity_score == 46
    assert result.priority_tier == "P2"


def test_custom_weights_affect_score():
    result = score_alert(
        {"poc_availability": True},
        weights={"poc_availability": 50},
    )
    assert result.severity_score == 36
    assert result.priority_tier == "P3"
