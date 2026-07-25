"""Provenance event persistence — append-only, same dual-backend pattern as
app/db/repository.py and app/db/profile_repository.py.

Only three event types are ever written here: `rejected`, `rejection_cleared`,
`refresh_requested` — the DCE's own version chain (Phase 2) already captures
everything else (value changes, verification toggles), so this store stays
deliberately small. Never mutated in place — "current state" for a field
(e.g. "is it currently rejected") is always derived by reading the latest
relevant event, not by updating a row.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.provenance.schemas import ProvenanceEventRecord

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PROVENANCE_EVENTS_FILE = DATA_DIR / "provenance_events.json"


class ProvenanceEventRepository(Protocol):
    def append_event(self, profile_id: str, field_key: str, event_type: str, note: str | None, actor: str) -> ProvenanceEventRecord: ...
    def list_events(self, profile_id: str) -> list[ProvenanceEventRecord]: ...


class JsonFileProvenanceEventRepository:
    """Local dev/testing fallback — same caveat as the other JSON-file
    repositories: not the approved production data store, see
    database/schema.sql `field_audit_events`.
    """

    _lock = threading.Lock()

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROVENANCE_EVENTS_FILE.exists():
            PROVENANCE_EVENTS_FILE.write_text(json.dumps({"events": []}, indent=2))

    def _read(self) -> dict:
        with self._lock:
            return json.loads(PROVENANCE_EVENTS_FILE.read_text())

    def _write(self, data: dict) -> None:
        with self._lock:
            PROVENANCE_EVENTS_FILE.write_text(json.dumps(data, indent=2, default=str))

    def append_event(self, profile_id: str, field_key: str, event_type: str, note: str | None, actor: str) -> ProvenanceEventRecord:
        record = ProvenanceEventRecord(
            id=str(uuid.uuid4()), profile_id=profile_id, field_key=field_key,
            event_type=event_type, note=note, actor=actor,
            created_at=datetime.now(timezone.utc),
        )
        data = self._read()
        data["events"].append(json.loads(record.model_dump_json()))
        self._write(data)
        return record

    def list_events(self, profile_id: str) -> list[ProvenanceEventRecord]:
        data = self._read()
        records = [ProvenanceEventRecord.model_validate(e) for e in data["events"] if e["profile_id"] == profile_id]
        records.sort(key=lambda r: r.created_at)
        return records


class SupabaseProvenanceEventRepository:
    """Maps to the `field_audit_events` table (database/schema.sql)."""

    def __init__(self) -> None:
        from supabase import Client, create_client

        settings = get_settings()
        self._client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def append_event(self, profile_id: str, field_key: str, event_type: str, note: str | None, actor: str) -> ProvenanceEventRecord:
        record = ProvenanceEventRecord(
            id=str(uuid.uuid4()), profile_id=profile_id, field_key=field_key,
            event_type=event_type, note=note, actor=actor,
            created_at=datetime.now(timezone.utc),
        )
        self._client.table("field_audit_events").insert(
            {
                "id": record.id, "profile_id": record.profile_id, "field_key": record.field_key,
                "event_type": record.event_type, "note": record.note, "actor": record.actor,
                "created_at": record.created_at.isoformat(),
            }
        ).execute()
        return record

    def list_events(self, profile_id: str) -> list[ProvenanceEventRecord]:
        rows = (
            self._client.table("field_audit_events")
            .select("*").eq("profile_id", profile_id).order("created_at").execute()
        )
        return [ProvenanceEventRecord.model_validate(r) for r in rows.data]


_provenance_event_repository_instance: ProvenanceEventRepository | None = None


def get_provenance_event_repository() -> ProvenanceEventRepository:
    global _provenance_event_repository_instance
    if _provenance_event_repository_instance is not None:
        return _provenance_event_repository_instance

    settings = get_settings()
    if settings.supabase_configured:
        _provenance_event_repository_instance = SupabaseProvenanceEventRepository()
    else:
        _provenance_event_repository_instance = JsonFileProvenanceEventRepository()
    return _provenance_event_repository_instance
