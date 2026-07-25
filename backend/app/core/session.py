"""Anonymous session handling (SRS §18) — simplified for Phase 1.

No login, no accounts. The frontend generates a UUIDv4 and sends it as
`X-Session-Id` on every request; this dependency just reads it back (falling
back to a fresh one if absent, e.g. for direct API testing via curl/Swagger).
Full session bookkeeping (a `sessions` row with `last_seen_at` upserts) is a
DB-layer concern deferred to the AI phase's session middleware — Phase 1's
JSON repository does not persist sessions separately, it only scopes reports
by whatever session id is passed.
"""

import uuid

from fastapi import Header


def get_session_id(x_session_id: str | None = Header(default=None)) -> str:
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    return str(uuid.uuid4())
