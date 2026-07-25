from datetime import datetime, timedelta, timezone

from app.provenance.refresh_policy import compute_expiry, get_refresh_strategy, get_ttl_days
from app.provenance.schemas import RefreshStrategy, SourceType


def test_calculated_fields_never_expire_by_default():
    assert get_ttl_days("net_cost", SourceType.CALCULATED) is None


def test_field_specific_override_beats_source_type_default():
    # selling_price is USER_ENTERED (no default TTL) but has a 7-day override
    assert get_ttl_days("selling_price", SourceType.USER_ENTERED) == 7


def test_refresh_strategy_mapping():
    assert get_refresh_strategy(SourceType.CALCULATED) == RefreshStrategy.ON_EDIT
    assert get_refresh_strategy(SourceType.USER_ENTERED) == RefreshStrategy.MANUAL_ONLY
    assert get_refresh_strategy(SourceType.AUTO_COLLECTED) == RefreshStrategy.PERIODIC
    assert get_refresh_strategy(SourceType.IMPORTED) == RefreshStrategy.ON_DEMAND
    assert get_refresh_strategy(SourceType.UNKNOWN) == RefreshStrategy.NEVER


def test_no_last_updated_means_no_expiry_info_at_all():
    assert compute_expiry("selling_price", SourceType.USER_ENTERED, None) is None


def test_no_ttl_policy_means_never_expired():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    info = compute_expiry("product_name", SourceType.USER_ENTERED, now, now=now)
    assert info.ttl_days is None
    assert info.expires_at is None
    assert info.is_expired is False


def test_fresh_value_within_ttl_is_not_expired():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    last_updated = now - timedelta(days=1)
    info = compute_expiry("selling_price", SourceType.USER_ENTERED, last_updated, now=now)
    assert info.ttl_days == 7
    assert info.is_expired is False


def test_value_past_ttl_is_expired():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    last_updated = now - timedelta(days=10)
    info = compute_expiry("selling_price", SourceType.USER_ENTERED, last_updated, now=now)
    assert info.is_expired is True


def test_value_exactly_at_ttl_boundary_is_not_yet_expired():
    now = datetime(2026, 1, 8, tzinfo=timezone.utc)
    last_updated = now - timedelta(days=7)  # exactly 7 days = exactly at expires_at
    info = compute_expiry("selling_price", SourceType.USER_ENTERED, last_updated, now=now)
    assert info.expires_at == now
    assert info.is_expired is False  # strictly greater-than, not >=
