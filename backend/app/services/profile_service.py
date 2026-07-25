from app.collection.collector import collect
from app.collection.schemas import ProductProfile, ProductProfileSummary
from app.db.profile_repository import get_profile_repository


def preview_profile(session_id: str, raw_input: dict) -> ProductProfile:
    """Compute a profile WITHOUT persisting — lets the frontend show live
    validation/quality-score feedback before the user explicitly saves.
    """
    return collect(session_id, raw_input)


def create_profile(session_id: str, raw_input: dict) -> ProductProfile:
    profile = collect(session_id, raw_input)
    get_profile_repository().create_profile(profile)
    return profile


def update_profile(session_id: str, existing_id: str, raw_input: dict) -> ProductProfile | None:
    """Editing never mutates the stored profile — it creates a new version
    chained via `previous_version_id`, per the Phase 2 brief's versioning
    requirement and this codebase's existing auditability principle
    (SRS §3 append-only history tables, PRS §10 History §10 "never silently
    rewritten").
    """
    existing = get_profile_repository().get_profile(existing_id)
    if existing is None:
        return None
    new_profile = collect(
        session_id, raw_input,
        profile_id=None, version=existing.version + 1, previous_version_id=existing.id,
    )
    get_profile_repository().create_profile(new_profile)
    return new_profile


def get_profile(profile_id: str) -> ProductProfile | None:
    return get_profile_repository().get_profile(profile_id)


def list_profiles(session_id: str | None) -> list[ProductProfileSummary]:
    return get_profile_repository().list_profiles(session_id=session_id)


def list_versions(profile_id: str) -> list[ProductProfileSummary]:
    return get_profile_repository().list_versions(profile_id)


def delete_profile(profile_id: str) -> bool:
    return get_profile_repository().delete_profile(profile_id)
