"""Data Source Manager (DSM) — schemas.

The DSM answers, for every field in a Product Profile: where did this value
come from, how much should it be trusted, has anyone checked it, is it
still fresh, and what happened to it over time. It is a read-oriented layer
built ON TOP of the Data Collection Engine (Phase 2) — it does not modify
`ProductProfile`/`FieldValue` (app/collection/schemas.py), it derives richer
provenance from what's already there plus its own small append-only overlay
(app/db/provenance_repository.py) for actions the DCE has no concept of
(rejecting a value, requesting a refresh).

Same non-fabrication discipline as every prior phase: a field whose source
can't be determined is tagged SourceType.UNKNOWN with no reliability score
and no source name — never a guessed default (PRS §17, applied here to
metadata about a value, not just the value itself).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """The Phase 4 brief's own five-way distinction."""

    AUTO_COLLECTED = "auto_collected"
    USER_ENTERED = "user_entered"
    CALCULATED = "calculated"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"  # a human checked it and it was WRONG — distinct from "not yet checked"


class RefreshStrategy(str, Enum):
    NEVER = "never"  # nothing to refresh (Unknown, or a fact with no natural staleness)
    ON_EDIT = "on_edit"  # recomputed automatically whenever the profile is edited (Calculated fields)
    PERIODIC = "periodic"  # should be re-verified/re-fetched after its TTL elapses
    ON_DEMAND = "on_demand"  # a human or a future connector must explicitly trigger it
    MANUAL_ONLY = "manual_only"  # only re-entering the value updates it; no automatic trigger


class SourceDefinition(BaseModel):
    """One entry in the Source Registry (app/provenance/source_registry.py) —
    a known PROVIDER, not a specific value. `baseline_reliability` is this
    provider's inherent trust ceiling; a specific field's `reliability_score`
    starts here and is never pushed above it.
    """

    key: str
    label: str
    default_source_type: SourceType
    baseline_reliability: float = Field(ge=0, le=1)
    description: str
    typically_requires_verification: bool
    default_refresh_strategy: RefreshStrategy
    evidence_tier_reference: str  # cross-reference note to PRS §5 Evidence Hierarchy, for consistency


class ExpiryInfo(BaseModel):
    ttl_days: int | None
    expires_at: datetime | None
    is_expired: bool
    checked_at: datetime


class AuditTrailEntry(BaseModel):
    """One event in a field's history. Most entries are DERIVED by diffing
    the Product Profile's existing version chain (Phase 2 versioning) rather
    than written separately — see app/provenance/audit_trail.py. Reject/
    clear-rejection/refresh-request entries come from the DSM's own
    append-only event log (app/db/provenance_repository.py), since the DCE
    has no concept of those actions.
    """

    timestamp: datetime
    event_type: str  # value_set | value_changed | verified | verification_cleared | rejected | rejection_cleared | refresh_requested
    field_key: str
    previous_value: Any | None = None
    new_value: Any | None = None
    actor: str
    notes: str | None = None
    profile_version: int | None = None


class FieldProvenance(BaseModel):
    field_key: str
    source_type: SourceType
    source_name: str | None  # Source Registry key, or None when source_type is UNKNOWN
    collection_method: str | None
    intended_source_hint: str  # field_registry.py's `source_hint` — the field's DESIGN policy, not necessarily what happened this time
    reliability_score: float | None = Field(default=None, ge=0, le=1)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    last_updated: datetime | None
    verification_status: VerificationStatus
    refresh_strategy: RefreshStrategy
    expiry: ExpiryInfo | None
    requires_manual_verification: bool


class FieldLineage(BaseModel):
    field_key: str
    label: str
    section: str
    value: Any | None
    provenance: FieldProvenance
    audit_trail: list[AuditTrailEntry] = Field(default_factory=list)


class LineageSummary(BaseModel):
    total_fields: int
    traceable_fields: int  # source_type != UNKNOWN
    unknown_fields: int
    verified_fields: int
    pending_verification_fields: int
    rejected_fields: int
    expired_fields: int
    average_reliability: float | None
    average_confidence: float | None
    source_type_breakdown: dict[str, int]


class ProvenanceEventRecord(BaseModel):
    """A stored override event — the DSM's own append-only log for actions
    the DCE has no concept of (app/db/provenance_repository.py). Distinct
    from `AuditTrailEntry`, which is the read-side view merging these events
    with the profile's own version-chain history.
    """

    id: str
    profile_id: str
    field_key: str
    event_type: str  # "rejected" | "rejection_cleared" | "refresh_requested"
    note: str | None = None
    actor: str = "user"
    created_at: datetime


class DataLineageReport(BaseModel):
    profile_id: str
    product_name: str
    profile_version: int
    generated_at: datetime
    fields: list[FieldLineage]
    summary: LineageSummary
