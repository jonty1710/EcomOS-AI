from app.collection.field_registry import FIELD_REGISTRY
from app.collection.quality_score import compute_data_quality
from app.collection.schemas import EffectiveClassification, FieldStatus, FieldValue


def _empty_fields() -> dict:
    return {
        key: FieldValue(
            key=key, value=None, status=FieldStatus.MISSING,
            effective_classification=EffectiveClassification.USER_INPUT_REQUIRED,
            confidence=None, verified=False, source="unavailable",
        )
        for key in FIELD_REGISTRY
    }


def test_all_missing_yields_zero_completeness():
    quality = compute_data_quality(_empty_fields())
    assert quality.completeness_pct == 0.0
    assert quality.confidence_pct == 0.0
    assert quality.verification_pending_pct >= 0.0  # fields exist but none verified


def test_validation_pct_100_when_nothing_attempted():
    quality = compute_data_quality(_empty_fields())
    assert quality.validation_pct == 100.0


def test_invalid_field_lowers_validation_pct():
    fields = _empty_fields()
    fields["selling_price"] = FieldValue(
        key="selling_price", value=-5, status=FieldStatus.INVALID,
        effective_classification=EffectiveClassification.AUTO_DETECT,
        confidence=None, verified=False, source="user",
        errors=["Selling Price cannot be negative."],
    )
    quality = compute_data_quality(fields)
    assert quality.validation_pct < 100.0


def test_verification_pending_reaches_zero_once_all_verified():
    fields = _empty_fields()
    for key, definition in FIELD_REGISTRY.items():
        if definition.requires_manual_verification:
            fields[key] = FieldValue(
                key=key, value="x", status=FieldStatus.FILLED,
                effective_classification=EffectiveClassification.MANUAL_VERIFICATION_REQUIRED,
                confidence=0.9, verified=True, source="user",
            )
    quality = compute_data_quality(fields)
    assert quality.verification_pending_pct == 0.0
