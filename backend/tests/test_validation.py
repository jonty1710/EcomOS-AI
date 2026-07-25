from app.collection.validation import validate_computed_margin, validate_field


def test_rejects_negative_selling_price():
    errors, _ = validate_field("selling_price", -5, {})
    assert errors


def test_rejects_empty_product_name():
    errors, _ = validate_field("product_name", "   ", {})
    assert errors


def test_rejects_impossible_weight():
    errors, _ = validate_field("weight_grams", 5_000_000, {})
    assert errors


def test_warns_on_heavy_but_plausible_weight():
    errors, warnings = validate_field("weight_grams", 80_000, {})
    assert not errors
    assert warnings


def test_accepts_tiny_weight_with_no_warning():
    errors, warnings = validate_field("weight_grams", 1, {})
    assert not errors
    assert not warnings


def test_warns_on_suspicious_gst():
    _, warnings = validate_field("gst_pct", 45, {})
    assert warnings


def test_no_warning_on_standard_gst():
    _, warnings = validate_field("gst_pct", 18, {})
    assert not warnings


def test_warns_when_selling_price_below_buying_price():
    _, warnings = validate_field("selling_price", 50, {"buying_price": 100})
    assert warnings


def test_negative_margin_warning():
    assert validate_computed_margin(-10.0)
    assert not validate_computed_margin(10.0)
    assert not validate_computed_margin(None)


def test_non_numeric_value_for_number_field_is_rejected():
    errors, _ = validate_field("selling_price", "not a number", {})
    assert errors
