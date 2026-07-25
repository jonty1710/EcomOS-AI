from app.scoring.profit import ProfitInputs, compute_profit, compute_scenarios, financial_sub_score


def test_compute_profit_basic():
    inputs = ProfitInputs(
        selling_price=499,
        buying_price=180,
        shipping_cost=40,
        packaging_cost=10,
        marketplace_fee_pct=15,
        ad_cost=30,
        gst_pct=18,
        return_cost=25,
        rto_cost=35,
    )
    result = compute_profit(inputs)
    assert result.marketplace_fee == round(499 * 0.15, 2)
    assert result.gst_amount == round(499 * 0.18, 2)
    assert result.net_profit == round(499 - result.total_cost, 2)
    assert result.margin_pct == round(result.net_profit / 499 * 100, 2)


def test_zero_buying_price_roi_is_none():
    inputs = ProfitInputs(selling_price=100, buying_price=0)
    result = compute_profit(inputs)
    assert result.roi_pct is None


def test_breakeven_none_when_unprofitable():
    inputs = ProfitInputs(selling_price=10, buying_price=50, gst_pct=0)
    result = compute_profit(inputs)
    assert result.net_profit < 0
    assert result.breakeven_units is None


def test_scenarios_worst_case_is_never_better_than_best_case():
    inputs = ProfitInputs(selling_price=500, buying_price=200, return_cost=20, rto_cost=15, ad_cost=25, gst_pct=18)
    scenarios = compute_scenarios(inputs)
    assert scenarios.worst_case.net_profit <= scenarios.expected_case.net_profit <= scenarios.best_case.net_profit


def test_financial_sub_score_caps_when_worst_case_is_a_loss():
    inputs = ProfitInputs(selling_price=100, buying_price=20, return_cost=5, rto_cost=5, gst_pct=18)
    scenarios = compute_scenarios(inputs)
    score = financial_sub_score(scenarios)
    if scenarios.worst_case.net_profit < 0:
        assert score <= 60.0
