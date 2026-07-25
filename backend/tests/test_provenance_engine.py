from app.collection.collector import collect
from app.provenance.provenance_engine import build_field_provenance, build_lineage_report
from app.provenance.schemas import SourceType, VerificationStatus


def _profile(**overrides):
    base = {
        "product_name": "Ceramic Mug", "selling_price": 349, "buying_price": 120,
        "shipping_cost": 30, "packaging_cost": 20, "supplier_name": "PotteryCo",
        "weight_grams": 300, "material": "ceramic",
    }
    base.update(overrides)
    return collect("s1", base)


def test_missing_field_is_explicitly_unknown_never_guessed():
    profile = collect("s1", {"product_name": "X"})
    fv = profile.fields["buying_price"]
    prov = build_field_provenance("buying_price", fv, profile.updated_at, is_rejected=False)
    assert prov.source_type == SourceType.UNKNOWN
    assert prov.source_name is None
    assert prov.reliability_score is None
    assert prov.confidence_score is None


def test_calculated_field_attributes_to_calculation_engine():
    profile = _profile()
    fv = profile.fields["net_cost"]
    prov = build_field_provenance("net_cost", fv, profile.updated_at, is_rejected=False)
    assert prov.source_type == SourceType.CALCULATED
    assert prov.source_name == "calculation_engine"
    assert prov.reliability_score == 1.0


def test_supplier_relay_field_attributes_to_supplier_not_user():
    profile = _profile()
    fv = profile.fields["buying_price"]
    prov = build_field_provenance("buying_price", fv, profile.updated_at, is_rejected=False)
    assert prov.source_name == "supplier"
    assert prov.intended_source_hint == "Supplier"
    assert prov.reliability_score == 0.6


def test_plain_user_field_attributes_to_user():
    profile = _profile()
    fv = profile.fields["product_name"]
    prov = build_field_provenance("product_name", fv, profile.updated_at, is_rejected=False)
    assert prov.source_name == "user"
    assert prov.reliability_score == 0.85


def test_category_detection_attributes_to_calculation_engine_as_auto_collected():
    profile = collect("s1", {"product_name": "Yoga Mat for home workout"})
    fv = profile.fields["category"]
    prov = build_field_provenance("category", fv, profile.updated_at, is_rejected=False)
    assert prov.source_type == SourceType.AUTO_COLLECTED
    assert prov.source_name == "calculation_engine"
    assert prov.collection_method == "keyword_classification"


def test_verification_required_field_pending_by_default():
    profile = _profile()
    fv = profile.fields["buying_price"]
    prov = build_field_provenance("buying_price", fv, profile.updated_at, is_rejected=False)
    assert prov.verification_status == VerificationStatus.PENDING


def test_verification_required_field_becomes_verified():
    profile = _profile(buying_price_verified=True)
    fv = profile.fields["buying_price"]
    prov = build_field_provenance("buying_price", fv, profile.updated_at, is_rejected=False)
    assert prov.verification_status == VerificationStatus.VERIFIED


def test_is_rejected_overrides_everything_else():
    profile = _profile(buying_price_verified=True)
    fv = profile.fields["buying_price"]
    prov = build_field_provenance("buying_price", fv, profile.updated_at, is_rejected=True)
    assert prov.verification_status == VerificationStatus.REJECTED


def test_lineage_report_covers_every_registry_field():
    profile = _profile()
    report = build_lineage_report(profile, [profile], [])
    assert report.summary.total_fields == len(profile.fields)
    assert len(report.fields) == len(profile.fields)


def test_lineage_report_does_not_crash_on_empty_profile():
    profile = collect("s1", {})
    report = build_lineage_report(profile, [profile], [])
    # Weight Class / Fragility / Packaging Type / Fragility Score are always
    # computed by build_logistics_profile even with no inputs (Phase 2's
    # documented "Unknown" defaults, not a gap) — those 4 stay traceable
    # (CALCULATED) even on a fully empty profile; everything else is Unknown.
    assert report.summary.traceable_fields == 4
    assert report.summary.unknown_fields == report.summary.total_fields - 4
    assert report.summary.average_reliability == 1.0  # only calculation_engine-sourced fields contributed
    assert report.summary.average_confidence == 1.0


def test_lineage_summary_counts_are_internally_consistent():
    profile = _profile()
    report = build_lineage_report(profile, [profile], [])
    s = report.summary
    assert s.traceable_fields + s.unknown_fields == s.total_fields
    assert sum(s.source_type_breakdown.values()) == s.total_fields
