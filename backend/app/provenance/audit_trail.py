"""Field Audit Trail — derived, not separately written.

Most of a field's history is already captured by the Data Collection
Engine's own versioning (Phase 2: editing a profile creates a new version,
chained via `previous_version_id`, never mutated in place). Rather than
duplicate that into a second write path, this module DIFFS consecutive
versions of a profile's fields to reconstruct `value_set` / `value_changed` /
`verified` / `verification_cleared` events on read.

Only the three DSM-specific actions with no DCE equivalent (reject,
clear-rejection, refresh-request) come from a real separate log
(app/db/provenance_repository.py) — merged in here by timestamp.
"""

from app.collection.schemas import FieldStatus, FieldValue, ProductProfile
from app.provenance.schemas import AuditTrailEntry, ProvenanceEventRecord


def derive_field_audit_trail(
    field_key: str,
    version_chain_oldest_first: list[ProductProfile],
    override_events: list[ProvenanceEventRecord],
) -> list[AuditTrailEntry]:
    entries: list[AuditTrailEntry] = []
    previous: FieldValue | None = None

    for profile in version_chain_oldest_first:
        current = profile.fields.get(field_key)
        if current is None:
            continue

        if previous is None:
            if current.status == FieldStatus.FILLED:
                entries.append(AuditTrailEntry(
                    timestamp=profile.created_at, event_type="value_set", field_key=field_key,
                    previous_value=None, new_value=current.value,
                    actor=current.source or "system", profile_version=profile.version,
                ))
        else:
            if current.value != previous.value and current.status == FieldStatus.FILLED:
                entries.append(AuditTrailEntry(
                    timestamp=profile.created_at, event_type="value_changed", field_key=field_key,
                    previous_value=previous.value, new_value=current.value,
                    actor=current.source or "system", profile_version=profile.version,
                ))
            if current.verified and not previous.verified:
                entries.append(AuditTrailEntry(
                    timestamp=profile.created_at, event_type="verified", field_key=field_key,
                    actor="user", profile_version=profile.version,
                ))
            if previous.verified and not current.verified:
                entries.append(AuditTrailEntry(
                    timestamp=profile.created_at, event_type="verification_cleared", field_key=field_key,
                    actor="user", profile_version=profile.version,
                ))

        previous = current

    for event in override_events:
        if event.field_key != field_key:
            continue
        entries.append(AuditTrailEntry(
            timestamp=event.created_at, event_type=event.event_type, field_key=field_key,
            actor=event.actor, notes=event.note, profile_version=None,
        ))

    entries.sort(key=lambda e: e.timestamp)
    return entries
