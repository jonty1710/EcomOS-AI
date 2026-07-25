"""Product Profile persistence — same dual-backend pattern as
app/db/repository.py (Supabase when configured, local JSON file otherwise).

Versioning: `update_profile` never mutates a stored profile in place. It
writes a NEW profile row with `version = old.version + 1` and
`previous_version_id = old.id`, exactly like the SRS's `reports` table is
append-only per report run (SRS §3) — "History: store profiles, allow
editing, track versions" means editing creates history, it doesn't erase it.
"""

import json
import threading
from pathlib import Path
from typing import Protocol

from app.collection.schemas import ProductProfile, ProductProfileSummary
from app.core.config import get_settings

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PROFILES_FILE = DATA_DIR / "profiles.json"


class ProfileRepository(Protocol):
    def create_profile(self, profile: ProductProfile) -> None: ...
    def get_profile(self, profile_id: str) -> ProductProfile | None: ...
    def list_profiles(self, session_id: str | None = None) -> list[ProductProfileSummary]: ...
    def list_versions(self, profile_id: str) -> list[ProductProfileSummary]: ...
    def delete_profile(self, profile_id: str) -> bool: ...


class JsonFileProfileRepository:
    """Local dev/testing fallback — same caveat as JsonFileReportRepository:
    not the approved production data store, see database/schema.sql.
    """

    _lock = threading.Lock()

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROFILES_FILE.exists():
            PROFILES_FILE.write_text(json.dumps({"profiles": {}}, indent=2))

    def _read(self) -> dict:
        with self._lock:
            return json.loads(PROFILES_FILE.read_text())

    def _write(self, data: dict) -> None:
        with self._lock:
            PROFILES_FILE.write_text(json.dumps(data, indent=2, default=str))

    def create_profile(self, profile: ProductProfile) -> None:
        data = self._read()
        data["profiles"][profile.id] = json.loads(profile.model_dump_json())
        self._write(data)

    def get_profile(self, profile_id: str) -> ProductProfile | None:
        data = self._read()
        raw = data["profiles"].get(profile_id)
        return ProductProfile.model_validate(raw) if raw else None

    def list_profiles(self, session_id: str | None = None) -> list[ProductProfileSummary]:
        """Latest version per product-name lineage only — older versions are
        still fetchable via list_versions/get_profile, just not duplicated
        in the main list.
        """
        data = self._read()
        all_profiles = [ProductProfile.model_validate(r) for r in data["profiles"].values()]
        if session_id:
            all_profiles = [p for p in all_profiles if p.session_id == session_id]

        superseded_ids = {p.previous_version_id for p in all_profiles if p.previous_version_id}
        latest_only = [p for p in all_profiles if p.id not in superseded_ids]
        latest_only.sort(key=lambda p: p.updated_at, reverse=True)
        return [
            ProductProfileSummary(
                id=p.id, product_name=p.product_name, version=p.version,
                completeness_pct=p.data_quality.completeness_pct,
                ready_for_research=p.ready_for_research,
                created_at=p.created_at, updated_at=p.updated_at,
            )
            for p in latest_only
        ]

    def list_versions(self, profile_id: str) -> list[ProductProfileSummary]:
        """Walks the previous_version_id chain backward from the given id
        (which should be the latest version) to build the full version history.
        """
        data = self._read()
        by_id = {k: ProductProfile.model_validate(v) for k, v in data["profiles"].items()}
        chain: list[ProductProfile] = []
        current = by_id.get(profile_id)
        seen: set[str] = set()
        while current is not None and current.id not in seen:
            seen.add(current.id)
            chain.append(current)
            current = by_id.get(current.previous_version_id) if current.previous_version_id else None
        return [
            ProductProfileSummary(
                id=p.id, product_name=p.product_name, version=p.version,
                completeness_pct=p.data_quality.completeness_pct,
                ready_for_research=p.ready_for_research,
                created_at=p.created_at, updated_at=p.updated_at,
            )
            for p in chain
        ]

    def delete_profile(self, profile_id: str) -> bool:
        data = self._read()
        if profile_id in data["profiles"]:
            del data["profiles"][profile_id]
            self._write(data)
            return True
        return False


class SupabaseProfileRepository:
    """Maps to the `product_profiles` table (database/schema.sql). Same
    honesty pattern as SupabaseReportRepository (app/db/repository.py): the
    write path is implemented; full relational read-path reassembly is
    deferred to when a real Supabase project is available to test against.
    """

    def __init__(self) -> None:
        from supabase import Client, create_client

        settings = get_settings()
        self._client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def create_profile(self, profile: ProductProfile) -> None:
        self._client.table("product_profiles").insert(
            {
                "id": profile.id,
                "session_id": profile.session_id,
                "product_name": profile.product_name,
                "source_url": profile.source_url,
                "detected_marketplace": profile.detected_marketplace,
                "version": profile.version,
                "previous_version_id": profile.previous_version_id,
                "fields": json.loads(profile.model_dump_json(include={"fields"}))["fields"],
                "cost_structure": profile.cost_structure,
                "data_quality": profile.data_quality.model_dump(),
                "missing_required": profile.missing_required,
                "missing_optional": profile.missing_optional,
                "ready_for_research": profile.ready_for_research,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat(),
            }
        ).execute()

    def get_profile(self, profile_id: str) -> ProductProfile | None:
        raise NotImplementedError(
            "SupabaseProfileRepository.get_profile: full reassembly pending a provisioned "
            "Supabase project to test against — same known gap as SupabaseReportRepository "
            "(app/db/repository.py). The JSON fallback repository is complete."
        )

    def list_profiles(self, session_id: str | None = None) -> list[ProductProfileSummary]:
        query = self._client.table("product_profiles").select("*")
        if session_id:
            query = query.eq("session_id", session_id)
        rows = query.order("updated_at", desc=True).execute()
        superseded_ids = {r["previous_version_id"] for r in rows.data if r.get("previous_version_id")}
        latest_only = [r for r in rows.data if r["id"] not in superseded_ids]
        return [
            ProductProfileSummary(
                id=r["id"], product_name=r["product_name"], version=r["version"],
                completeness_pct=r["data_quality"]["completeness_pct"],
                ready_for_research=r["ready_for_research"],
                created_at=r["created_at"], updated_at=r["updated_at"],
            )
            for r in latest_only
        ]

    def list_versions(self, profile_id: str) -> list[ProductProfileSummary]:
        raise NotImplementedError("See get_profile note above.")

    def delete_profile(self, profile_id: str) -> bool:
        result = self._client.table("product_profiles").delete().eq("id", profile_id).execute()
        return bool(result.data)


_profile_repository_instance: ProfileRepository | None = None


def get_profile_repository() -> ProfileRepository:
    global _profile_repository_instance
    if _profile_repository_instance is not None:
        return _profile_repository_instance

    settings = get_settings()
    if settings.supabase_configured:
        _profile_repository_instance = SupabaseProfileRepository()
    else:
        _profile_repository_instance = JsonFileProfileRepository()
    return _profile_repository_instance
