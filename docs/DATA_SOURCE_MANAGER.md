# Data Source Manager (Phase 4)

**Status:** Implemented — deterministic only, no AI provider wired in.
**Code:** `backend/app/provenance/`
**Depends on:** `app.collection` (reads `ProductProfile`/`FieldValue`/`FIELD_REGISTRY` directly — one-directional, DSM never mutates them). Zero dependency on `app.ai` or `app.connectors` — see `tests/test_provenance_no_network.py`.
**Frontend:** `/collection/[id]` → **Data Sources** tab.

---

## 1. What this is

For every field in a Product Profile, the DSM answers: where did this value come from, how much should it be trusted, has anyone checked it, is it still fresh, and what happened to it over time. It is a **read-oriented layer built on top of the Data Collection Engine (Phase 2)** — it does not modify `ProductProfile` or `FieldValue`. It derives richer provenance from what's already there, plus a small append-only overlay for the two actions the DCE has no concept of: rejecting a value, and requesting a refresh.

This formalizes ideas that already existed informally in earlier phases — PRS §17's Verified/Estimated/Assumed/Unknown tags, PRS §5's Evidence Hierarchy, and the DCE's own `FieldValue.source`/`confidence`/`verified` — into one dedicated, comprehensive model.

## 2. The core rule: never guess metadata

Exactly the same discipline as every prior phase, applied to *metadata about a value* instead of the value itself: a field whose source can't be determined gets `SourceType.UNKNOWN`, `source_name=None`, `reliability_score=None`, `confidence_score=None` — never a fabricated default. A missing field has **no** metadata at all, honestly, not "Unknown" dressed up as a plausible guess.

## 3. Architecture

```
app/provenance/
├── schemas.py            SourceType, VerificationStatus, RefreshStrategy,
│                          SourceDefinition, FieldProvenance, AuditTrailEntry,
│                          FieldLineage, LineageSummary, DataLineageReport
├── source_registry.py     1. Source Registry — 7 provider definitions
├── reliability.py          3. Reliability Scoring — the confidence formula
├── refresh_policy.py       4. Refresh Policies + 5. Expiry Detection
├── audit_trail.py          7. Field Audit Trail (derived from profile versions)
└── provenance_engine.py    2. Provenance Model assembly + 8. Data Lineage Viewer backend

app/db/provenance_repository.py   append-only event log (reject/clear/refresh-request)
app/services/provenance_service.py
app/api/v1/provenance.py          6. Validation Status is exposed here (verification_status)
```

Numbers above map directly to the Phase 4 brief's "Implement: 1-8" list.

## 4. Source Registry

Seven providers, exactly the examples in the brief: `marketplace`, `manufacturer`, `supplier`, `user`, `calculation_engine`, `knowledge_engine`, `ai_provider`. Each carries a `baseline_reliability` — and these are **not invented for this phase**. They reuse PRS §5's Evidence Hierarchy scores wherever a direct analogue exists:

| Source | Reliability | PRS §5 tier reused |
|---|---|---|
| Calculation Engine | 1.0 | Calculation |
| Manufacturer | 0.9 | Manufacturer |
| Marketplace | 0.85 | Marketplace |
| User | 0.85 | (Phase 2's existing user-input baseline) |
| Knowledge Engine | 0.75 | Industry report |
| Supplier | 0.6 | Supplier |
| Future AI Provider | 0.3 | AI reasoning |

`marketplace`, `manufacturer`, and `ai_provider` are registered but **not reachable today** — no connector or AI provider exists yet (Phase 1/2/3 all reserve these as empty interfaces). The registry exists so nothing structural changes when they become reachable.

## 5. Provenance Model

`FieldProvenance` per field, built by `provenance_engine.build_field_provenance()`. Two things worth calling out:

**Reliability vs. Confidence are different questions**, same "don't collapse distinct questions into one" principle used throughout (PRS §14): `reliability_score` is a static property of the *source* (how trustworthy is "User" as a source, in general). `confidence_score` is dynamic — how much should we trust *this specific value, right now* — computed as:

```
confidence = reliability_score × field's_own_confidence × validity_multiplier × verification_multiplier × freshness_multiplier
```

`field's_own_confidence` is the DCE's own per-field confidence (Phase 2 already computes this — e.g. a category classification's actual keyword-match strength). This was a real bug caught during manual testing: without it, two category detections with different match strength collapsed to the same DSM confidence, throwing away real signal the DCE already had. Fixed with a regression test (`test_field_own_confidence_scales_result`).

**Policy vs. actual source** — `intended_source_hint` carries the field's *design* policy (`field_registry.py`'s existing `source_hint`, e.g. "Marketplace" for Selling Price) separately from `source_name`, which reflects what *actually* happened this time (e.g. `"user"`, since no marketplace connector exists yet). This mirrors the DCE's own `collection_type` vs. `effective_classification` distinction (Phase 2) and the Knowledge Engine's policy-vs-current-capability distinction (Phase 3) — the same pattern, applied a third time.

**Supplier-relay detection**: fields whose `source_hint` is `"Supplier"` (Buying Price, MOQ, Lead Time, GST Available) are attributed to `source_name="supplier"` even though the DCE recorded `FieldValue.source="user"` — the person is a conduit typing in what the supplier told them, not the actual origin of the information.

## 6. Reliability Scoring & 7. Field Audit Trail

Reliability: §5 above. Audit Trail: **mostly derived, not separately written.** The DCE already versions every edit (Phase 2: a new profile row per save, chained via `previous_version_id`, never mutated). `audit_trail.py` diffs consecutive versions of a profile's fields to reconstruct `value_set` / `value_changed` / `verified` / `verification_cleared` events **on read** — no duplicate write path. Only the two DSM-specific actions with no DCE equivalent (`rejected`, `rejection_cleared`, `refresh_requested`) come from a real append-only log (`field_audit_events` table / `provenance_repository.py`), merged in by timestamp.

## 8. Data Lineage Viewer

Backend: `provenance_engine.build_lineage_report()` → `DataLineageReport` (every field's provenance + audit trail + a `LineageSummary` rollup). API: `GET /api/v1/provenance/profiles/{id}/lineage`. Frontend: the **Data Sources** tab on `/collection/[id]` (`components/collection/data-sources-panel.tsx`) — per the brief, shows where each value came from, verification status, confidence, reliability, last updated, and manual-verification-required, grouped by section, with an expandable audit trail and Reject / Clear Rejection / Request Refresh actions per field.

## 9. Refresh & Expiry

TTL defaults are set per `SourceType` first (mirroring SRS §7's per-agent cache TTL design), with field-specific overrides for values everyone in ecommerce knows go stale faster than their type suggests (Selling Price/MRP: 7 days, Buying Price/Marketplace Fee: 30 days, MOQ/Lead Time/GST Available: 60 days, GST %: 90 days). Calculated fields never expire (recomputed on every edit); a field with no `last_updated` at all has no expiry to compute. `Request Refresh` **records intent honestly** — it does not fetch anything (no connector exists), and says so in its own audit note, rather than silently pretending a refresh happened.

## 10. Known limitations (honest, not hidden)

- **Per-field timestamps are approximated.** The DCE (Phase 2) tracks `updated_at` at the *profile* level, not per field. `last_updated` for every field in a profile is currently the profile's own `updated_at` — a true per-field timestamp would require a DCE schema addition, deliberately not made in this phase to avoid touching tested Phase 2 code for a Phase 4 concern.
- **Rejection is scoped to a specific profile version**, not carried forward automatically when a new version is created. This is arguably correct (a rejection is about a specific value; if the value changes in a new version, the old rejection may no longer even apply) but is a real design choice worth knowing about.
- **DSM rejection does not feed back into the DCE's own `ready_for_research`/Data Quality Score.** A rejected Buying Price is visible and flagged in the Data Sources panel but doesn't currently block sending the profile to the Research Engine. Wiring that feedback loop is a natural next step, not done here to keep this phase's blast radius to the DSM itself.
- **`manufacturer`, `marketplace`, and `ai_provider` sources are registered but unreachable** — consistent with every prior phase's "reserve the interface, don't fake the implementation" discipline.
