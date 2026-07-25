from app.collection.calculations import calculate_all, calculate_discount_pct, calculate_physical, calculate_pricing


def test_discount_pct_basic():
    assert calculate_discount_pct(500, 400) == 20.0


def test_discount_pct_none_without_mrp():
    assert calculate_discount_pct(None, 400) is None


def test_pricing_returns_empty_without_selling_and_buying_price():
    result = calculate_pricing({"mrp": 500})
    assert "net_cost" not in result


def test_pricing_full_computation():
    result = calculate_pricing({
        "selling_price": 500, "buying_price": 200, "shipping_cost": 30,
        "packaging_cost": 10, "marketplace_fee_pct": 10, "gst_pct": 18,
    })
    assert result["net_cost"] > 0
    assert result["expected_profit"] == round(500 - result["net_cost"], 2)
    assert 0 <= result["profitability_score"] <= 100
    assert sum(result["cost_structure"].values()) > 0


def test_physical_fragility_and_packaging():
    result = calculate_physical({"weight_grams": 300, "material": "glass"})
    assert result["fragility"] == "High"
    assert result["weight_class"] == "Medium"
    assert result["fragility_score"] == 75


def test_physical_handles_missing_inputs_without_crashing():
    result = calculate_physical({})
    assert result["weight_class"] == "Unknown"
    assert result["fragility"] == "Unknown"


def test_calculate_all_does_not_crash_on_empty_input():
    result = calculate_all({})
    assert isinstance(result, dict)
