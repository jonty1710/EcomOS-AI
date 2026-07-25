import pytest

from app.collection.bridge import profile_to_research_input
from app.collection.collector import collect
from app.core.errors import AppError


def test_bridge_refuses_incomplete_profile():
    profile = collect("s1", {"product_name": "X"})
    with pytest.raises(AppError) as exc_info:
        profile_to_research_input(profile)
    assert exc_info.value.code == "PROFILE_INCOMPLETE"


def test_bridge_converts_ready_profile():
    profile = collect("s1", {
        "product_name": "Drawer Organizer", "selling_price": 499, "buying_price": 180,
        "shipping_cost": 40, "packaging_cost": 10, "supplier_name": "Acme Traders",
        "weight_grams": 400, "material": "plastic",
    })
    payload = profile_to_research_input(profile)
    assert payload["product_name"] == "Drawer Organizer"
    assert payload["selling_price"] == 499
    assert payload["category_hint"] == profile.fields["category"].value


def test_bridge_omits_unset_optional_fields_rather_than_passing_none():
    # Regression test: passing an explicit None for e.g. marketplace_fee_pct
    # broke the Research Engine's `mi.get(key, default)` fallback downstream
    # (a present-but-None key short-circuits .get()'s default), crashing
    # arithmetic in app/research/agents.py. The bridge must omit the key
    # entirely when there's no value, not pass None.
    profile = collect("s1", {
        "product_name": "Drawer Organizer", "selling_price": 499, "buying_price": 180,
        "shipping_cost": 40, "packaging_cost": 10, "supplier_name": "Acme Traders",
        "weight_grams": 400,
    })
    payload = profile_to_research_input(profile)
    assert "marketplace_fee_pct" not in payload
    assert "material" not in payload
    assert None not in payload.values()
