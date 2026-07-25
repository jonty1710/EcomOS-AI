from app.collection.collector import collect
from app.provenance.audit_trail import derive_field_audit_trail
from app.provenance.schemas import ProvenanceEventRecord
from datetime import datetime, timezone


def test_single_version_produces_a_value_set_event():
    profile = collect("s1", {"product_name": "Ceramic Mug", "selling_price": 349})
    trail = derive_field_audit_trail("selling_price", [profile], [])
    assert len(trail) == 1
    assert trail[0].event_type == "value_set"
    assert trail[0].new_value == 349


def test_missing_field_produces_no_events():
    profile = collect("s1", {"product_name": "Ceramic Mug"})
    trail = derive_field_audit_trail("buying_price", [profile], [])
    assert trail == []


def test_value_change_across_versions_is_detected():
    v1 = collect("s1", {"product_name": "Ceramic Mug", "selling_price": 300}, version=1)
    v2 = collect("s1", {"product_name": "Ceramic Mug", "selling_price": 350}, version=2, previous_version_id=v1.id)
    trail = derive_field_audit_trail("selling_price", [v1, v2], [])
    event_types = [e.event_type for e in trail]
    assert "value_set" in event_types
    assert "value_changed" in event_types
    changed = next(e for e in trail if e.event_type == "value_changed")
    assert changed.previous_value == 300
    assert changed.new_value == 350


def test_verification_toggle_across_versions_is_detected():
    v1 = collect("s1", {"product_name": "X", "buying_price": 100}, version=1)
    v2 = collect("s1", {"product_name": "X", "buying_price": 100, "buying_price_verified": True}, version=2, previous_version_id=v1.id)
    trail = derive_field_audit_trail("buying_price", [v1, v2], [])
    assert any(e.event_type == "verified" for e in trail)


def test_override_events_are_merged_and_sorted_chronologically():
    profile = collect("s1", {"product_name": "X", "buying_price": 100})
    override = ProvenanceEventRecord(
        id="e1", profile_id=profile.id, field_key="buying_price", event_type="rejected",
        note="Price looked wrong", actor="user", created_at=datetime.now(timezone.utc),
    )
    trail = derive_field_audit_trail("buying_price", [profile], [override])
    assert trail[-1].event_type == "rejected"  # happened after value_set
    assert trail == sorted(trail, key=lambda e: e.timestamp)


def test_override_events_for_other_fields_are_excluded():
    profile = collect("s1", {"product_name": "X", "buying_price": 100})
    override = ProvenanceEventRecord(
        id="e1", profile_id=profile.id, field_key="weight_grams", event_type="rejected",
        note=None, actor="user", created_at=datetime.now(timezone.utc),
    )
    trail = derive_field_audit_trail("buying_price", [profile], [override])
    assert all(e.field_key == "buying_price" for e in trail)
