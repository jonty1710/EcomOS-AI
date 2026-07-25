"""Reliability Scoring — two distinct numbers, same "don't collapse distinct
questions into one" principle used throughout this codebase (PRS §14):

- `reliability_score`: how trustworthy is this KIND of source, in general?
  A static property of the Source Registry entry (source_registry.py) — it
  does not change based on what's happening with any specific value.
- `confidence_score`: how much should we trust THIS SPECIFIC VALUE, right
  now? Derived from reliability, discounted by verification state, data
  validity, and staleness. This is the number that actually answers "should
  I act on this."
"""

from app.collection.schemas import FieldStatus
from app.provenance.schemas import VerificationStatus

_VERIFICATION_MULTIPLIER: dict[VerificationStatus, float] = {
    VerificationStatus.VERIFIED: 1.0,
    VerificationStatus.NOT_REQUIRED: 1.0,
    VerificationStatus.PENDING: 0.7,
    VerificationStatus.REJECTED: 0.1,
}

_EXPIRED_FRESHNESS_MULTIPLIER = 0.5
_FRESH_FRESHNESS_MULTIPLIER = 1.0


def compute_confidence(
    reliability_score: float | None,
    verification_status: VerificationStatus,
    field_status: FieldStatus,
    is_expired: bool,
    field_own_confidence: float | None = None,
) -> float | None:
    """None in, None out — a field with no determinable source has no basis
    for a confidence claim either (never defaults to a guessed mid-range
    number, PRS §17).

    `field_own_confidence` is the DCE's own per-field confidence (Phase 2,
    `FieldValue.confidence` — e.g. a category classification's actual
    keyword-match strength, not just "some deterministic thing produced
    this"). Folded in as a multiplier so two values from the same source
    TYPE (e.g. two keyword-classified categories with different match
    strength) don't collapse to an identical DSM confidence — source
    reliability is a ceiling, not the whole story.
    """
    if reliability_score is None:
        return None
    if field_status == FieldStatus.MISSING:
        return None  # nothing was collected — there is no value to be confident about

    validity_multiplier = 1.0 if field_status == FieldStatus.FILLED else 0.1  # INVALID
    verification_multiplier = _VERIFICATION_MULTIPLIER[verification_status]
    freshness_multiplier = _EXPIRED_FRESHNESS_MULTIPLIER if is_expired else _FRESH_FRESHNESS_MULTIPLIER
    own_confidence_multiplier = field_own_confidence if field_own_confidence is not None else 1.0

    confidence = (
        reliability_score * own_confidence_multiplier
        * validity_multiplier * verification_multiplier * freshness_multiplier
    )
    return round(min(1.0, max(0.0, confidence)), 3)
