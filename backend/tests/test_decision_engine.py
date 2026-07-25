from app.scoring.decision import DIMENSION_WEIGHTS, compute_composite, compute_research_completeness


def test_weight_table_sums_to_100():
    assert sum(DIMENSION_WEIGHTS.values()) == 100


def test_phase1_research_completeness_below_hard_floor():
    completeness = compute_research_completeness()
    assert completeness < 40.0


def test_phase1_always_yields_insufficient_data():
    result = compute_composite(financial_sub_score=90.0, preliminary_risk_level="Low")
    assert result.recommendation == "Insufficient Data"
    assert result.overall_score is None
