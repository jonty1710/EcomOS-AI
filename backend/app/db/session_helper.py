"""Shared helper for Supabase-backed repositories: `sessions` rows are the FK
target for `reports.session_id` and `product_profiles.session_id` (SRS §18).
Session bookkeeping itself stays intentionally minimal for Phase 1-4 (no
`sessions` middleware, no `last_seen_at` tracking beyond this) — this only
exists so a first-time session id doesn't violate the foreign key constraint
the first time it's used. Discovered live: the JSON-file fallback repository
never enforces this FK, so the gap was invisible until a real Supabase
project was connected.
"""

from datetime import datetime, timezone


def ensure_session_exists(client, session_id: str) -> None:
    client.table("sessions").upsert(
        {"id": session_id, "last_seen_at": datetime.now(timezone.utc).isoformat()},
        on_conflict="id",
    ).execute()
