"""Service-layer integration: provenance_service coordinates profile_service
(existing profile persistence) with the new provenance event repository.
Both singletons are reset to fresh, isolated, tmp-path-backed instances per
test so this never touches the real backend/data/*.json files.

Also forces SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY empty for the duration of
each test: if a developer has a local `.env` with real Supabase credentials
(needed to run the app against a real project), `get_settings()` would
otherwise pick them up here too and route these tests at the real
Supabase-backed repository instead of the JSON fallback they're designed to
exercise — env vars take precedence over `.env` in pydantic-settings, so
setting them empty here reliably forces the JSON path regardless of what's
on disk locally.
"""

import app.core.config as config_module
import app.db.profile_repository as profile_repository_module
import app.db.provenance_repository as provenance_repository_module
from app.services import profile_service, provenance_service


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_repository_module, "PROFILES_FILE", tmp_path / "profiles.json")
    monkeypatch.setattr(profile_repository_module, "_profile_repository_instance", None)
    monkeypatch.setattr(provenance_repository_module, "PROVENANCE_EVENTS_FILE", tmp_path / "provenance_events.json")
    monkeypatch.setattr(provenance_repository_module, "_provenance_event_repository_instance", None)
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    config_module.get_settings.cache_clear()


def _make_profile():
    return profile_service.create_profile("s1", {
        "product_name": "Ceramic Mug", "selling_price": 349, "buying_price": 120,
        "shipping_cost": 30, "packaging_cost": 20, "supplier_name": "PotteryCo",
        "weight_grams": 300, "material": "ceramic",
    })


def test_lineage_report_for_unknown_profile_returns_none(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert provenance_service.get_lineage_report("nonexistent") is None


def test_lineage_report_reflects_saved_profile(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile = _make_profile()
    report = provenance_service.get_lineage_report(profile.id)
    assert report is not None
    assert report.product_name == "Ceramic Mug"
    assert report.summary.total_fields == len(profile.fields)


def test_reject_field_then_lineage_shows_rejected_status(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile = _make_profile()
    event = provenance_service.reject_field(profile.id, "buying_price", "Quoted price looked inflated")
    assert event is not None
    assert event.event_type == "rejected"

    report = provenance_service.get_lineage_report(profile.id)
    buying_price = next(f for f in report.fields if f.field_key == "buying_price")
    assert buying_price.provenance.verification_status.value == "rejected"
    assert any(e.event_type == "rejected" for e in buying_price.audit_trail)


def test_clear_rejection_restores_pending_status(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile = _make_profile()
    provenance_service.reject_field(profile.id, "buying_price", "note")
    provenance_service.clear_rejection(profile.id, "buying_price")

    report = provenance_service.get_lineage_report(profile.id)
    buying_price = next(f for f in report.fields if f.field_key == "buying_price")
    assert buying_price.provenance.verification_status.value == "pending"  # back to pending, not verified


def test_request_refresh_is_recorded_but_never_fabricates_a_new_value(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile = _make_profile()
    original_value = profile.fields["selling_price"].value
    event = provenance_service.request_refresh(profile.id, "selling_price")
    assert event.event_type == "refresh_requested"

    report = provenance_service.get_lineage_report(profile.id)
    selling_price = next(f for f in report.fields if f.field_key == "selling_price")
    assert selling_price.value == original_value  # unchanged — no connector to fetch a "fresh" one
    assert any(e.event_type == "refresh_requested" for e in selling_price.audit_trail)


def test_reject_unknown_field_key_returns_none(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile = _make_profile()
    assert provenance_service.reject_field(profile.id, "not_a_real_field", None) is None


def test_reject_on_unknown_profile_returns_none(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert provenance_service.reject_field("nonexistent", "buying_price", None) is None
