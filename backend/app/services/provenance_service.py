from app.collection.field_registry import FIELD_REGISTRY
from app.db.provenance_repository import get_provenance_event_repository
from app.provenance.provenance_engine import build_lineage_report
from app.provenance.schemas import DataLineageReport, ProvenanceEventRecord
from app.services import profile_service


def get_lineage_report(profile_id: str) -> DataLineageReport | None:
    profile = profile_service.get_profile(profile_id)
    if profile is None:
        return None

    # list_versions walks the chain backward (newest -> oldest, including
    # `profile` itself); the audit trail needs oldest -> newest to diff forward.
    version_summaries = profile_service.list_versions(profile_id)
    version_chain_oldest_first = [
        v for v in (profile_service.get_profile(s.id) for s in reversed(version_summaries)) if v is not None
    ]
    if not version_chain_oldest_first:
        version_chain_oldest_first = [profile]

    events = get_provenance_event_repository().list_events(profile_id)
    return build_lineage_report(profile, version_chain_oldest_first, events)


def reject_field(profile_id: str, field_key: str, note: str | None, actor: str = "user") -> ProvenanceEventRecord | None:
    if field_key not in FIELD_REGISTRY:
        return None
    if profile_service.get_profile(profile_id) is None:
        return None
    return get_provenance_event_repository().append_event(profile_id, field_key, "rejected", note, actor)


def clear_rejection(profile_id: str, field_key: str, actor: str = "user") -> ProvenanceEventRecord | None:
    if field_key not in FIELD_REGISTRY:
        return None
    if profile_service.get_profile(profile_id) is None:
        return None
    return get_provenance_event_repository().append_event(profile_id, field_key, "rejection_cleared", None, actor)


def request_refresh(profile_id: str, field_key: str, actor: str = "user") -> ProvenanceEventRecord | None:
    if field_key not in FIELD_REGISTRY:
        return None
    if profile_service.get_profile(profile_id) is None:
        return None
    # Recorded honestly as intent — there is no connector to actually fetch a
    # fresh value from yet (Phase 4 brief: no scraping, no marketplace
    # automation). The event exists so a future connector implementation has
    # a real queue of "someone asked for this to be refreshed" to work from.
    return get_provenance_event_repository().append_event(
        profile_id, field_key, "refresh_requested",
        "No automated data source is connected yet — re-enter the value manually, or wait for a future connector.",
        actor,
    )
