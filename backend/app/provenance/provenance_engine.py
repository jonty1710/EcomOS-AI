"""Provenance Engine — the Data Source Manager's assembly logic. Ties the
Source Registry, Reliability Scoring, and Refresh/Expiry policy together
into one `FieldProvenance` per field, and rolls all fields up into a
`DataLineageReport` (the Data Lineage Viewer's backend, app/api/v1/provenance.py
is the presentation of it).
"""

from datetime import datetime, timezone

from app.collection.field_registry import FIELD_REGISTRY
from app.collection.schemas import FieldStatus, FieldValue, ProductProfile
from app.provenance.audit_trail import derive_field_audit_trail
from app.provenance.reliability import compute_confidence
from app.provenance.refresh_policy import compute_expiry, get_refresh_strategy
from app.provenance.schemas import (
    DataLineageReport,
    FieldLineage,
    FieldProvenance,
    LineageSummary,
    ProvenanceEventRecord,
    SourceType,
    VerificationStatus,
)
from app.provenance.source_registry import SOURCE_REGISTRY

# Maps the DCE's own FieldValue.source strings (app/collection/collector.py)
# onto (source_registry key, SourceType, collection_method). Any source
# string not listed here — including "unavailable" — resolves to
# (None, SourceType.UNKNOWN, None), never a guess.
_DCE_SOURCE_MAP: dict[str, tuple[str, SourceType, str]] = {
    "calculated": ("calculation_engine", SourceType.CALCULATED, "deterministic_calculation"),
    "deterministic_detection": ("calculation_engine", SourceType.AUTO_COLLECTED, "keyword_classification"),
    "user": ("user", SourceType.USER_ENTERED, "manual_form_entry"),
}

# Fields whose field_registry.py `source_hint` is "Supplier" — the DCE
# collects these via the USER typing them in, but the actual origin of the
# information is the supplier relationship, not the user's own knowledge.
_SUPPLIER_RELAY_FIELD_KEYS = frozenset(k for k, d in FIELD_REGISTRY.items() if d.source_hint == "Supplier")


def _resolve_source(field_key: str, field_value: FieldValue) -> tuple[str | None, SourceType, str | None]:
    mapped = _DCE_SOURCE_MAP.get(field_value.source)
    if mapped is None:
        return None, SourceType.UNKNOWN, None

    source_key, source_type, collection_method = mapped
    if source_key == "user" and field_key in _SUPPLIER_RELAY_FIELD_KEYS:
        return "supplier", source_type, "manual_form_entry_relayed_from_supplier"
    return source_key, source_type, collection_method


def _resolve_verification_status(
    field_key: str,
    field_value: FieldValue,
    requires_manual_verification: bool,
    is_rejected: bool,
) -> VerificationStatus:
    if is_rejected:
        return VerificationStatus.REJECTED
    if not requires_manual_verification:
        return VerificationStatus.NOT_REQUIRED
    return VerificationStatus.VERIFIED if field_value.verified else VerificationStatus.PENDING


def build_field_provenance(
    field_key: str,
    field_value: FieldValue,
    profile_updated_at: datetime,
    is_rejected: bool,
    now: datetime | None = None,
) -> FieldProvenance:
    definition = FIELD_REGISTRY[field_key]
    now = now or datetime.now(timezone.utc)

    if field_value.status == FieldStatus.MISSING:
        # Nothing was collected — every metadata field is honestly Unknown,
        # never a guessed default (Phase 4 brief: "do not guess missing metadata").
        return FieldProvenance(
            field_key=field_key, source_type=SourceType.UNKNOWN, source_name=None, collection_method=None,
            intended_source_hint=definition.source_hint, reliability_score=None, confidence_score=None,
            last_updated=None,
            verification_status=VerificationStatus.PENDING if definition.requires_manual_verification else VerificationStatus.NOT_REQUIRED,
            refresh_strategy=get_refresh_strategy(SourceType.UNKNOWN), expiry=None,
            requires_manual_verification=definition.requires_manual_verification,
        )

    source_key, source_type, collection_method = _resolve_source(field_key, field_value)
    source_def = SOURCE_REGISTRY.get(source_key) if source_key else None
    reliability_score = source_def.baseline_reliability if source_def else None

    verification_status = _resolve_verification_status(field_key, field_value, definition.requires_manual_verification, is_rejected)
    refresh_strategy = get_refresh_strategy(source_type)
    # Per-field timestamps aren't tracked by the DCE (Phase 2) — approximated
    # as the profile's own `updated_at`. See docs/DATA_SOURCE_MANAGER.md §6
    # "Known limitations" for why, and what a true fix looks like.
    last_updated = profile_updated_at
    expiry = compute_expiry(field_key, source_type, last_updated, now)
    confidence_score = compute_confidence(
        reliability_score, verification_status, field_value.status,
        expiry.is_expired if expiry else False,
        field_own_confidence=field_value.confidence,
    )

    return FieldProvenance(
        field_key=field_key, source_type=source_type, source_name=source_key, collection_method=collection_method,
        intended_source_hint=definition.source_hint, reliability_score=reliability_score, confidence_score=confidence_score,
        last_updated=last_updated, verification_status=verification_status, refresh_strategy=refresh_strategy,
        expiry=expiry, requires_manual_verification=definition.requires_manual_verification,
    )


def _latest_rejection_state(field_key: str, override_events: list[ProvenanceEventRecord]) -> bool:
    relevant = [e for e in override_events if e.field_key == field_key and e.event_type in ("rejected", "rejection_cleared")]
    if not relevant:
        return False
    return relevant[-1].event_type == "rejected"  # events are pre-sorted by the repository/service


def build_lineage_report(
    profile: ProductProfile,
    version_chain_oldest_first: list[ProductProfile],
    override_events: list[ProvenanceEventRecord],
) -> DataLineageReport:
    fields: list[FieldLineage] = []
    now = datetime.now(timezone.utc)

    for field_key, field_value in profile.fields.items():
        definition = FIELD_REGISTRY[field_key]
        is_rejected = _latest_rejection_state(field_key, override_events)
        provenance = build_field_provenance(field_key, field_value, profile.updated_at, is_rejected, now)
        audit_trail = derive_field_audit_trail(field_key, version_chain_oldest_first, override_events)
        fields.append(FieldLineage(
            field_key=field_key, label=definition.label, section=definition.section,
            value=field_value.value, provenance=provenance, audit_trail=audit_trail,
        ))

    summary = _summarize(fields)
    return DataLineageReport(
        profile_id=profile.id, product_name=profile.product_name, profile_version=profile.version,
        generated_at=now, fields=fields, summary=summary,
    )


def _summarize(fields: list[FieldLineage]) -> LineageSummary:
    reliabilities = [f.provenance.reliability_score for f in fields if f.provenance.reliability_score is not None]
    confidences = [f.provenance.confidence_score for f in fields if f.provenance.confidence_score is not None]
    source_type_breakdown: dict[str, int] = {}
    for f in fields:
        key = f.provenance.source_type.value
        source_type_breakdown[key] = source_type_breakdown.get(key, 0) + 1

    return LineageSummary(
        total_fields=len(fields),
        traceable_fields=sum(1 for f in fields if f.provenance.source_type != SourceType.UNKNOWN),
        unknown_fields=sum(1 for f in fields if f.provenance.source_type == SourceType.UNKNOWN),
        verified_fields=sum(1 for f in fields if f.provenance.verification_status == VerificationStatus.VERIFIED),
        pending_verification_fields=sum(1 for f in fields if f.provenance.verification_status == VerificationStatus.PENDING),
        rejected_fields=sum(1 for f in fields if f.provenance.verification_status == VerificationStatus.REJECTED),
        expired_fields=sum(1 for f in fields if f.provenance.expiry is not None and f.provenance.expiry.is_expired),
        average_reliability=round(sum(reliabilities) / len(reliabilities), 3) if reliabilities else None,
        average_confidence=round(sum(confidences) / len(confidences), 3) if confidences else None,
        source_type_breakdown=source_type_breakdown,
    )
