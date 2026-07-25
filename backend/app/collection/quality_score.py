"""Data Quality Score — four independent metrics, computed deterministically
from the field registry + the per-field state the collector has already
resolved. Mirrors PRS §14's "four distinct numbers, four distinct questions"
principle, applied one layer earlier in the pipeline (at collection time,
not decision time).
"""

from app.collection.field_registry import FIELD_REGISTRY, INPUT_FIELD_KEYS
from app.collection.schemas import DataQualityScore, FieldStatus, FieldValue


def compute_data_quality(fields: dict[str, FieldValue]) -> DataQualityScore:
    return DataQualityScore(
        completeness_pct=_completeness(fields),
        validation_pct=_validation(fields),
        confidence_pct=_confidence(fields),
        verification_pending_pct=_verification_pending(fields),
    )


def _completeness(fields: dict[str, FieldValue]) -> float:
    """Required fields count double — a profile with every optional field
    blank but all required fields filled should read as mostly complete,
    not 50%.
    """
    total_weight = 0.0
    filled_weight = 0.0
    for key in INPUT_FIELD_KEYS:
        definition = FIELD_REGISTRY[key]
        weight = 2.0 if definition.required else 1.0
        total_weight += weight
        fv = fields.get(key)
        if fv is not None and fv.status == FieldStatus.FILLED:
            filled_weight += weight
    if total_weight == 0:
        return 100.0
    return round(filled_weight / total_weight * 100, 1)


def _validation(fields: dict[str, FieldValue]) -> float:
    attempted = [fv for fv in fields.values() if fv.status in (FieldStatus.FILLED, FieldStatus.INVALID)]
    if not attempted:
        return 100.0
    valid = sum(1 for fv in attempted if fv.status == FieldStatus.FILLED)
    return round(valid / len(attempted) * 100, 1)


def _confidence(fields: dict[str, FieldValue]) -> float:
    scored = [fv.confidence for fv in fields.values() if fv.confidence is not None]
    if not scored:
        return 0.0
    return round(sum(scored) / len(scored) * 100, 1)


def _verification_pending(fields: dict[str, FieldValue]) -> float:
    needs_verification = [fv for fv in fields.values() if FIELD_REGISTRY[fv.key].requires_manual_verification]
    if not needs_verification:
        return 0.0
    pending = sum(1 for fv in needs_verification if not fv.verified)
    return round(pending / len(needs_verification) * 100, 1)
