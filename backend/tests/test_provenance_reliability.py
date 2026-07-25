from app.collection.schemas import FieldStatus
from app.provenance.reliability import compute_confidence
from app.provenance.schemas import VerificationStatus


def test_none_reliability_yields_none_confidence():
    assert compute_confidence(None, VerificationStatus.VERIFIED, FieldStatus.FILLED, False) is None


def test_missing_field_yields_none_confidence_even_with_reliability():
    assert compute_confidence(0.9, VerificationStatus.NOT_REQUIRED, FieldStatus.MISSING, False) is None


def test_verified_scores_higher_than_pending():
    verified = compute_confidence(0.6, VerificationStatus.VERIFIED, FieldStatus.FILLED, False)
    pending = compute_confidence(0.6, VerificationStatus.PENDING, FieldStatus.FILLED, False)
    assert verified > pending


def test_rejected_scores_lowest_of_all_verification_states():
    rejected = compute_confidence(0.9, VerificationStatus.REJECTED, FieldStatus.FILLED, False)
    pending = compute_confidence(0.9, VerificationStatus.PENDING, FieldStatus.FILLED, False)
    verified = compute_confidence(0.9, VerificationStatus.VERIFIED, FieldStatus.FILLED, False)
    assert rejected < pending < verified


def test_invalid_field_status_heavily_discounted():
    valid = compute_confidence(0.85, VerificationStatus.NOT_REQUIRED, FieldStatus.FILLED, False)
    invalid = compute_confidence(0.85, VerificationStatus.NOT_REQUIRED, FieldStatus.INVALID, False)
    assert invalid < valid


def test_expired_lowers_confidence():
    fresh = compute_confidence(0.85, VerificationStatus.NOT_REQUIRED, FieldStatus.FILLED, False)
    expired = compute_confidence(0.85, VerificationStatus.NOT_REQUIRED, FieldStatus.FILLED, True)
    assert expired < fresh


def test_field_own_confidence_scales_result():
    high = compute_confidence(1.0, VerificationStatus.NOT_REQUIRED, FieldStatus.FILLED, False, field_own_confidence=0.95)
    low = compute_confidence(1.0, VerificationStatus.NOT_REQUIRED, FieldStatus.FILLED, False, field_own_confidence=0.3)
    assert low < high
    assert low == 0.3


def test_confidence_never_exceeds_one_or_drops_below_zero():
    result = compute_confidence(1.0, VerificationStatus.VERIFIED, FieldStatus.FILLED, False, field_own_confidence=1.0)
    assert 0.0 <= result <= 1.0
