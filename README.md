# EcomOS AI

**Phase 4 (Data Source Manager) — no AI providers wired in.** Deterministic research + data collection + knowledge grounding + provenance tracking only. See `docs/SRS.md`, `docs/FBP.md`, `docs/PRS.md` for the approved specs this build follows, `docs/KNOWLEDGE_ENGINE.md` for Phase 3, and `docs/DATA_SOURCE_MANAGER.md` for Phase 4.

## What's here

- `backend/app/provenance/` — the Data Source Manager: Source Registry, Provenance Model, Reliability Scoring, Refresh/Expiry policy, Field Audit Trail, Data Lineage Viewer backend. See `docs/DATA_SOURCE_MANAGER.md`.
- `backend/app/knowledge/` — the Knowledge Engine: 8 seed knowledge libraries, deterministic lookup engine, two-tier caching. See `docs/KNOWLEDGE_ENGINE.md`.
- `backend/app/collection/` — the Data Collection Engine: field registry, validation engine, calculations engine, data quality scoring, the collector workflow, and the bridge into the Research Engine.
- `backend/` — FastAPI, deterministic Research Engine, Scoring Engine, Report Engine, DB layer.
- `frontend/` — Next.js 15 (App Router) + TypeScript + Tailwind, shadcn-style components, dark mode by default.
- `database/schema.sql` — full approved Supabase schema (SRS §3) + `product_profiles` (Phase 2) + `field_audit_events` (Phase 4), no sample data.
- `docs/` — SRS, FBP, PRS (approved specs), KNOWLEDGE_ENGINE (Phase 3), DATA_SOURCE_MANAGER (Phase 4).

## Running locally

### Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate          # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Without `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` set (copy `.env.example` to `.env` to configure), the backend automatically uses a local JSON file store at `backend/data/db.json` — the app is fully functional with zero external dependencies. Set both env vars to switch to real Supabase with no code changes (`app/db/repository.py`).

Run tests: `pytest` (136 tests — Phase 1 deterministic scoring/category logic + Phase 2 Data Collection Engine + Phase 3 Knowledge Engine + Phase 4 Data Source Manager).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`. Copy `.env.example` to `.env.local` if your backend isn't on `localhost:8000`.

### Database (optional — only needed to test against real Supabase)

Run `database/schema.sql` against a Supabase project's SQL editor. No seed/sample data is included by design.

## Deployment

- **Frontend → Vercel**: `frontend/vercel.json` included. Set `NEXT_PUBLIC_API_BASE_URL` to your deployed backend's `/api/v1` URL in Vercel project env vars.
- **Backend → Railway**: `backend/railway.json` + `backend/Procfile` included.
- **Backend → Render**: `render.yaml` included at repo root (Render Blueprint). Set `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `CORS_ORIGINS` in the Render dashboard.

## Phase 1 scope

No AI provider is called anywhere in this codebase. Every AI-dependent research dimension (9 of the 11 scored dimensions — Demand, Competitive Landscape, Pricing, Trend & Seasonality, Review Mining, Keyword & Discoverability, Supplier Sourcing, Compliance & Regulatory, Brand & Positioning) returns a `planned_for_ai_phase` status and renders as "Not yet connected" in the UI — never a fabricated value. Only Profit & Unit Economics and a preliminary slice of Logistics & Fulfillment Risk are computed, both 100% deterministic. See `backend/app/ai/providers/base_provider.py` for the interface the next phase plugs into.

## Phase 2 scope — Data Collection Engine

Every product field (53 across 5 sections) is classified as **Auto Detect**, **User Input Required**, **Manual Verification Required**, or **Calculated** — never guessed. The single canonical field list lives in `backend/app/collection/field_registry.py` and is served to the frontend via `GET /api/v1/collection/field-registry`, so the form is generated from the same source of truth the validation/scoring logic uses.

- **Validation Engine** (`app/collection/validation.py`): rejects negative prices, impossible weights, empty product names; warns on suspicious GST rates, Selling Price < Buying Price, and negative margin.
- **Calculations Engine** (`app/collection/calculations.py`): Discount %, Net Cost, Expected Profit, Margin, ROI, Break Even, Weight Class, Fragility (+ Fragility Score), Packaging Suggestion, Profitability Score — all 100% deterministic Python, reusing the exact same formulas as the Phase 1 Research Engine (`app/scoring/profit.py`, `app/research/logistics.py`), not a forked copy.
- **Data Quality Score** (`app/collection/quality_score.py`): four independent numbers — Completeness %, Validation %, Confidence %, Verification Pending % — never collapsed into one figure.
- **Product Profile** (`app/collection/schemas.py`): the single source of truth handed to the Research Engine via `app/collection/bridge.py`. Versioned and append-only — editing creates a new version, never overwrites.
- **Reserved connector interfaces** (`app/connectors/product_connector.py`, `app/connectors/supplier_connector.py`): Amazon/Flipkart/Meesho and IndiaMART/TradeIndia/Manufacturer APIs — ABC + empty registry, zero implementations, same pattern as the AI provider interface.
- **UI**: `/collection` (list), `/collection/new`, `/collection/[id]` (editor with live debounced validation, Data Quality panel, Missing Fields panel, version history).

## Phase 3 scope — Knowledge Engine

Sits between the Data Collection Engine and any future AI provider. Eight deterministic knowledge libraries (Product Categories, Materials, Packaging, Logistics, Marketplace Rules, Supplier Intelligence, Compliance, Research Best Practices), seeded as JSON under `backend/app/knowledge/data/`, loaded and cached once per process. Full architecture writeup: `docs/KNOWLEDGE_ENGINE.md`.

- **Deterministic, no network**: every lookup either matches a real entry, falls back to an explicitly-generic one, or comes back empty — never a fabricated answer. Enforced mechanically, not just documented — see `tests/test_knowledge_no_network.py`.
- **`KnowledgePack`** (`app/knowledge/schemas.py`): the single output type, with a `coverage` block reporting exactly which of the 8 libraries matched, fell back, or had nothing for this product.
- **Two-tier caching**: seed JSON loaded once per process (`app/knowledge/loader.py`), assembled packs cached by signature (`app/knowledge/engine.py`, `lru_cache(maxsize=256)`).
- **Consumed by the Research Engine before any AI reasoning**, per the Phase 3 brief: `app/research/orchestrator.py` attaches a `KnowledgePack` to every agent's context. The two real deterministic agents (Profit, Logistics) already enrich their reasoning with it today; the 9 still-planned AI agents surface a `knowledge_preview` showing what grounding context will be available to them once AI is wired in.
- **Reachable from the DCE too**: `app/collection/knowledge_bridge.py` adapts a `ProductProfile` into a knowledge lookup; `GET /api/v1/knowledge/pack/for-profile/{id}` and `GET /api/v1/knowledge/pack/preview` expose it directly.

## Phase 4 scope — Data Source Manager

Tracks where every field in a Product Profile came from — a read-oriented layer built on top of the DCE (Phase 2), never modifying it. Full architecture writeup: `docs/DATA_SOURCE_MANAGER.md`.

- **Source Registry** (`app/provenance/source_registry.py`): 7 providers (Marketplace, Manufacturer, Supplier, User, Calculation Engine, Knowledge Engine, Future AI Provider), each with a `baseline_reliability` reused directly from PRS §5's Evidence Hierarchy, not invented fresh.
- **Provenance Model** (`app/provenance/schemas.py`, `provenance_engine.py`): every field gets a `FieldProvenance` — Source Type (Auto Collected/User Entered/Calculated/Imported/Unknown), Source Name, Collection Method, Reliability, Confidence, Last Updated, Verification Status, Refresh Strategy, Expiry — never guessed; a field with no determinable source is honestly `Unknown`, not a fabricated default.
- **Reliability vs. Confidence**: reliability is a static property of the source; confidence is dynamic — `reliability × the DCE's own per-field confidence × validity × verification × freshness`. Two category detections with different keyword-match strength get different DSM confidence, not the same one (a real bug caught and fixed during testing, with a regression test).
- **Field Audit Trail** (`app/provenance/audit_trail.py`): mostly *derived* by diffing the DCE's existing profile version chain, not a duplicate write path — only Reject/Clear-Rejection/Refresh-Request (things the DCE has no concept of) come from a real append-only log (`field_audit_events`).
- **Data Lineage Viewer**: `GET /api/v1/provenance/profiles/{id}/lineage` + the **Data Sources** tab on `/collection/[id]` — source, verification, confidence, reliability, last updated, manual-verification-required, expiry, and full audit trail per field, with Reject/Clear/Request-Refresh actions.
- **No network, no AI**: enforced mechanically — `tests/test_provenance_no_network.py`.

## Known gaps (honest, not hidden)

- `SupabaseReportRepository`/`SupabaseProfileRepository` `.get_*`/`.toggle_favorite` methods (`backend/app/db/repository.py`, `backend/app/db/profile_repository.py`) are stubbed with `NotImplementedError` — full read-path reassembly from Supabase's relational tables needs a provisioned project to test against. The JSON fallback repositories are complete and are what the frontend is validated against.
- No automated frontend tests yet (backend has pytest coverage for all scoring/category/collection/knowledge/provenance logic — 136 tests).
- Session bookkeeping is simplified (`X-Session-Id` header echoed back, no `sessions` table upsert yet) — full SRS §18 session middleware is deferred.
- `GET /collection/profiles/{id}/versions` walks the version chain backward (ancestors) from the given id, not forward — querying with an old version's id won't surface newer versions. The frontend always re-points at the newest id after a save, so this doesn't surface in normal use, but it's a real API limitation worth knowing about.
- Category Detection has no sub-category classifier yet (`sub_category` is a real registry field but always falls through to manual entry) — so `data/categories.json` has no sub-category-keyed entries either.
- `manufacturer_direct`/`wholesaler` supplier knowledge entries are seeded but currently unreachable from a real profile — the DCE has no explicit "sourcing platform" field beyond what's parsed from a marketplace URL (`indiamart`/`tradeindia` only). See `docs/KNOWLEDGE_ENGINE.md` §7.
- Knowledge Pack coverage is not yet surfaced anywhere in the frontend UI (it's fully available via the API and via `ReportResponse.knowledge_pack`, just not rendered in a dedicated panel yet).
- DSM per-field `last_updated` is approximated as the profile's own `updated_at` (the DCE doesn't track per-field timestamps yet); DSM field rejection is advisory only and doesn't yet feed back into the DCE's `ready_for_research` gate. See `docs/DATA_SOURCE_MANAGER.md` §10.
- `manufacturer` and `marketplace` Source Registry entries are registered but unreachable (no connector exists yet), same pattern as every other reserved-but-unimplemented interface in this codebase.
