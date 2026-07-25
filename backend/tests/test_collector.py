"""Covers every scenario the Phase 2 brief's TESTING section names explicitly:
empty form, complete form, invalid values, extreme values, large products,
tiny products — asserting no crashes and correct classification throughout.
"""

from app.collection.collector import collect
from app.collection.schemas import FieldStatus


def test_empty_form_does_not_crash_and_flags_everything_missing():
    profile = collect("s1", {})
    assert profile.data_quality.completeness_pct == 0.0
    assert set(profile.missing_required) == {
        "product_name", "selling_price", "buying_price", "shipping_cost",
        "packaging_cost", "weight_grams", "supplier_name",
    }
    assert profile.ready_for_research is False


def test_complete_form_is_ready_for_research():
    profile = collect("s1", {
        "product_name": "Drawer Organizer", "selling_price": 499, "buying_price": 180,
        "shipping_cost": 40, "packaging_cost": 10, "supplier_name": "Acme Traders",
        "weight_grams": 400, "material": "plastic", "mrp": 599, "gst_pct": 18,
        "marketplace_fee_pct": 15, "closing_fee": 5, "ad_cost": 20,
        "brand": "Acme", "sku": "DO-100", "moq": 100, "lead_time_days": 15,
    })
    assert profile.ready_for_research is True
    assert profile.missing_required == []
    assert profile.fields["net_cost"].status == FieldStatus.FILLED
    assert profile.fields["margin_pct"].value is not None
    assert profile.data_quality.completeness_pct > 0


def test_invalid_values_are_flagged_not_silently_accepted():
    profile = collect("s1", {"product_name": "X", "selling_price": -100, "buying_price": 10, "weight_grams": -5})
    assert profile.fields["selling_price"].status == FieldStatus.INVALID
    assert profile.fields["weight_grams"].status == FieldStatus.INVALID
    # An invalid required field must never be treated as "ready"
    assert profile.ready_for_research is False


def test_extreme_impossible_weight_rejected_without_crash():
    profile = collect("s1", {"product_name": "X", "weight_grams": 10_000_000})
    assert profile.fields["weight_grams"].status == FieldStatus.INVALID


def test_large_expensive_product_does_not_crash():
    profile = collect("s1", {
        "product_name": "Industrial Machine", "selling_price": 950_000, "buying_price": 600_000,
        "shipping_cost": 15_000, "packaging_cost": 5_000, "supplier_name": "HeavyCo",
        "weight_grams": 150_000, "material": "metal",
    })
    assert profile.ready_for_research is True
    assert profile.fields["weight_class"].value == "Heavy"
    assert profile.fields["weight_grams"].warnings  # unusually heavy, but plausible


def test_tiny_cheap_product_does_not_crash():
    profile = collect("s1", {
        "product_name": "Tiny Bead", "selling_price": 9, "buying_price": 2,
        "shipping_cost": 1, "packaging_cost": 0.5, "supplier_name": "BeadCo",
        "weight_grams": 1,
    })
    assert profile.ready_for_research is True
    assert profile.fields["weight_class"].value == "Light"
    assert profile.fields["net_cost"].value is not None


def test_category_auto_detected_deterministically():
    profile = collect("s1", {"product_name": "Yoga Mat for home workout"})
    assert profile.fields["category"].value == "Fitness & Sports"
    assert profile.fields["category"].source == "deterministic_detection"
    assert profile.fields["category"].effective_classification.value == "auto_detect"


def test_calculated_fields_never_come_from_raw_input():
    # Even if the caller tries to inject a calculated field directly, it must
    # be recomputed, never taken at face value — this is the DCE's core
    # "never fabricate" guarantee applied to its own inputs.
    profile = collect("s1", {
        "product_name": "X", "selling_price": 100, "buying_price": 50,
        "shipping_cost": 5, "packaging_cost": 5, "supplier_name": "Y", "weight_grams": 100,
        "margin_pct": 9999,  # attempted injection
    })
    assert profile.fields["margin_pct"].value != 9999


def test_source_url_marketplace_detection_without_fetching():
    profile = collect("s1", {"product_name": "X", "source_url": "https://www.amazon.in/dp/B000123"})
    assert profile.detected_marketplace == "amazon"
    # No connector exists — marketplace detection must never fabricate field values.
    assert profile.fields["brand"].status == FieldStatus.MISSING


def test_manual_verification_flag_is_respected():
    profile = collect("s1", {
        "product_name": "X", "selling_price": 100, "buying_price": 50,
        "shipping_cost": 5, "packaging_cost": 5, "supplier_name": "Y", "weight_grams": 100,
        "buying_price_verified": True,
    })
    assert profile.fields["buying_price"].verified is True
