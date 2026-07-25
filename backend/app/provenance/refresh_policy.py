"""Refresh Policies + Expiry Detection.

TTL defaults are set per `SourceType` first (mirroring the SRS §7 per-agent
cache TTL design — fast-moving sources get short TTLs, static/self-reported
facts get none), with a small set of field-specific overrides for values
everyone in ecommerce knows go stale faster than their source type would
suggest (prices, GST, sourcing terms). Fields not listed keep their
source-type default. A field with no default (None) never expires — an
absence of a policy is not treated as "expires immediately," it's treated
as "no staleness policy exists for this yet," honestly.
"""

from datetime import datetime, timedelta, timezone

from app.provenance.schemas import ExpiryInfo, RefreshStrategy, SourceType

DEFAULT_TTL_DAYS_BY_SOURCE_TYPE: dict[SourceType, int | None] = {
    SourceType.CALCULATED: None,  # recomputed on every edit — "expiry" doesn't apply
    SourceType.USER_ENTERED: None,  # no default staleness assumption for a self-reported fact
    SourceType.AUTO_COLLECTED: 3,  # would-be-connector data — mirrors SRS §7 Pricing/Trend 24-72h
    SourceType.IMPORTED: 30,  # curated/imported reference data
    SourceType.UNKNOWN: None,
}

# Fields known to go stale faster (or slower) than their source type's default,
# regardless of source. Days.
FIELD_SPECIFIC_TTL_DAYS: dict[str, int] = {
    "selling_price": 7,
    "mrp": 7,
    "marketplace_fee_pct": 30,
    "buying_price": 30,
    "moq": 60,
    "lead_time_days": 60,
    "gst_available": 60,
    "gst_pct": 90,
}

_SOURCE_TYPE_TO_REFRESH_STRATEGY: dict[SourceType, RefreshStrategy] = {
    SourceType.CALCULATED: RefreshStrategy.ON_EDIT,
    SourceType.USER_ENTERED: RefreshStrategy.MANUAL_ONLY,
    SourceType.AUTO_COLLECTED: RefreshStrategy.PERIODIC,
    SourceType.IMPORTED: RefreshStrategy.ON_DEMAND,
    SourceType.UNKNOWN: RefreshStrategy.NEVER,
}


def get_refresh_strategy(source_type: SourceType) -> RefreshStrategy:
    return _SOURCE_TYPE_TO_REFRESH_STRATEGY[source_type]


def get_ttl_days(field_key: str, source_type: SourceType) -> int | None:
    if field_key in FIELD_SPECIFIC_TTL_DAYS:
        return FIELD_SPECIFIC_TTL_DAYS[field_key]
    return DEFAULT_TTL_DAYS_BY_SOURCE_TYPE[source_type]


def compute_expiry(
    field_key: str,
    source_type: SourceType,
    last_updated: datetime | None,
    now: datetime | None = None,
) -> ExpiryInfo | None:
    """None means "no expiry policy applies" — distinct from ExpiryInfo with
    `is_expired=False`, which means a policy exists and the value is
    currently within it. A field with no `last_updated` at all (nothing was
    ever collected) has no expiry to compute either.
    """
    if last_updated is None:
        return None
    now = now or datetime.now(timezone.utc)
    ttl_days = get_ttl_days(field_key, source_type)
    if ttl_days is None:
        return ExpiryInfo(ttl_days=None, expires_at=None, is_expired=False, checked_at=now)

    expires_at = last_updated + timedelta(days=ttl_days)
    return ExpiryInfo(ttl_days=ttl_days, expires_at=expires_at, is_expired=now > expires_at, checked_at=now)
