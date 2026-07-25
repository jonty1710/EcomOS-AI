# Knowledge Engine (Phase 3)

**Status:** Implemented — deterministic only, no AI provider wired in.
**Code:** `backend/app/knowledge/`
**Depends on:** nothing but the Python standard library + Pydantic. Zero dependency on `app.ai`, `app.connectors`, `app.collection`, or `app.research` — see `tests/test_knowledge_no_network.py` for the enforced guarantee.
**Depended on by:** `app.research.orchestrator` (Research Engine) and `app.collection.knowledge_bridge` (Data Collection Engine), one direction only.

---

## 1. What this is

The Knowledge Engine sits between the Data Collection Engine (Phase 2) and any future AI provider (Phase 4+). It answers one question, deterministically: **"what does this system already know, in general, about a product like this?"**

It is not the Research Engine (which scores *this specific* product) and not an AI provider (which will eventually reason over both this pack and the product's own evidence). It is a **grounding layer**: curated, versioned, inspectable reference data, assembled the same way every time for the same inputs.

Eight libraries, matching the Phase 3 brief exactly:

| Library | File | Keyed by |
|---|---|---|
| Product Categories | `data/categories.json` | Category name (same taxonomy as `app/research/category_detection.py`) |
| Materials | `data/materials.json` | Canonical material name, with `aliases` |
| Packaging | `data/packaging.json` | `{weight_class}_{fragility}` |
| Logistics | `data/logistics.json` | Weight class |
| Marketplace Rules | `data/marketplace_rules.json` | Marketplace name |
| Supplier Intelligence | `data/supplier_intelligence.json` | Sourcing platform |
| Compliance | `data/compliance.json` | Compliance flag key |
| Research Best Practices | `data/research_best_practices.json` | Category, or `"general"` |

## 2. The core rule: never fabricate

Every lookup resolves to one of four states (`LibraryMatchStatus`, `app/knowledge/schemas.py`):

- **MATCHED** — an entry exists for exactly this key.
- **FALLBACK** — no exact entry; an explicitly-generic entry was used instead (e.g. an unrecognized category falls back to the `"Uncategorized"` entry, tagged as a fallback, never presented as if it were category-specific).
- **NOT_AVAILABLE** — a key was given, but nothing (exact or generic) matches it.
- **NOT_APPLICABLE** — no key was given at all; this library wasn't queried.

This is the same discipline the Data Collection Engine applies to product fields (Phase 2, PRS §17), one layer up: the Knowledge Engine would rather return an honest gap than a plausible-sounding guess. Every `KnowledgePack` carries a `coverage: KnowledgePackCoverage` block reporting exactly which libraries resolved how, plus a single `overall_coverage_pct` (MATCHED=1.0, FALLBACK=0.5, NOT_AVAILABLE=0.0, averaged only over libraries that were actually queried — `NOT_APPLICABLE` dimensions are excluded from the average entirely, the same way the DCE's Confidence % excludes fields with no value).

## 3. Seed knowledge format

Plain JSON, one file per library, under `backend/app/knowledge/data/`. Not YAML, not inline Python dicts:

- **JSON over YAML**: zero new dependency (stdlib `json`), and it's the same format the rest of the API already speaks.
- **JSON over inline Python**: keeps the *content* (a domain-knowledge asset, meant to grow and be edited by a content-literate person, not necessarily an engineer) separate from the *lookup logic* (code). Diffs to `categories.json` read as content changes in git, not code changes — same "auditable diff" principle SRS §5 applies to prompt versioning.

Each file is a JSON object keyed by the lookup key, with values validated against a Pydantic model in `app/knowledge/schemas.py` at load time (`app/knowledge/loader.py`) — a malformed seed entry fails fast at process start, not silently at query time.

**To add a new entry**: add a key to the relevant JSON file matching its Pydantic schema, restart the process (or call `app.knowledge.loader.clear_all_caches()` in a dev/test session). No code change required for new *data*; a code change is only needed to add a new *library* (a new schema + loader function + engine lookup function).

## 4. Lookup engine

`app/knowledge/engine.py`. Public interface:

```python
get_knowledge_pack(signature: KnowledgePackSignature) -> KnowledgePack
get_knowledge_pack_from_fields(category=None, materials=(), marketplace=None,
                                supplier_platform=None, weight_class=None, fragility=None) -> KnowledgePack
classify_detected_marketplace(value: str | None) -> tuple[marketplace, supplier_platform]
```

`KnowledgePackSignature` is every input that can affect a pack's contents (category, materials, marketplace, supplier_platform, weight_class, fragility). Two calls with an identical signature always produce an identical pack — this is both the correctness argument and the cache key.

**Compliance flags are derived, not requested**: a caller never passes compliance flag keys directly. The engine unions `category_knowledge.common_compliance_flags` with each matched material's `common_compliance_flags`, then looks those up. This mirrors the same "don't ask for what can be derived" instinct the DCE's calculated fields already apply (Phase 2 §"Auto Calculated Fields").

**Marketplace vs. supplier routing**: `amazon`/`flipkart`/`meesho` are marketplaces (Marketplace Rules library); `indiamart`/`tradeindia` are sourcing platforms (Supplier Intelligence library) — both come from the same `detected_marketplace` string (`app/collection/marketplace_url.py`'s domain parser doesn't distinguish them), so `classify_detected_marketplace()` routes a raw value into the correct signature slot. Passing `"indiamart"` into the marketplace slot would silently miss — this function exists specifically so no caller has to remember that distinction.

## 5. Caching strategy

Two tiers, matching the two things that are actually expensive:

**Tier 1 — seed data** (`app/knowledge/loader.py`): each `load_*()` function is `functools.lru_cache`-wrapped with no arguments, so every JSON file is read and Pydantic-validated exactly once per process. This is a pure in-memory reference table; there is no reason to re-read it per request.

**Tier 2 — assembled packs** (`app/knowledge/engine.py`): `get_knowledge_pack()` is `functools.lru_cache(maxsize=256)`-wrapped. Assembling a pack is pure computation over data already in memory, so this tier mostly saves repeated Pydantic object construction for popular signatures (e.g. many sellers researching different products in the same category), not I/O. 256 comfortably covers the realistic signature space (12 categories × 10 materials × a handful of marketplace/weight/fragility combinations).

Both tiers expose a clear-cache function for tests and for a future dev-mode hot-reload: `loader.clear_all_caches()` and `engine.clear_pack_cache()`.

**What this deliberately does not do**: no TTL, no external cache (Redis, etc.), no cache invalidation on seed-file edit while the process is running. The data is static per-deploy; a seed-file change ships with a deploy (or a dev-mode reload), not a live invalidation event. If this grows into an admin-editable knowledge base (see §7), that would be the point to add real invalidation — not before.

## 6. Integration points

### Research Engine (`app/research/orchestrator.py`)

Per the Phase 3 brief — *"the Research Engine should consume this Knowledge Pack before any future AI reasoning"* — `run_manual_research()` builds a `KnowledgePackSignature` from the detected category, material, weight class, fragility, and marketplace **before** the agent registry runs, and attaches it to `ResearchContext.knowledge_pack` (`app/research/base_agent.py`), which every agent receives.

Today (no AI yet), consumption is real but bounded to what's honest:

- **`ProfitAgent`** appends the category's typical margin band to its `reasoning`, explicitly labeled as reference data, not a claim about the specific product.
- **`LogisticsPreliminaryAgent`** appends typical RTO causes and packaging cost-band context for the resolved weight/fragility combination.
- **`PlannedForAIPhaseAgent`** (the 9 still-AI-dependent dimensions) surfaces a `knowledge_preview` in `data` — never in `reasoning`, since no reasoning has actually happened yet — showing what grounding context will be available to it once AI is wired in. `demand`, `competitive_landscape`, `pricing_intelligence`, `trend_seasonality`, `brand_positioning`, `supplier_sourcing`, and `compliance_regulatory` all get a preview when relevant knowledge exists; `review_mining` and `keyword_discoverability` don't, because this phase has no review or keyword knowledge library to draw from — no preview is fabricated for them.

The full pack is also attached to `ReportResponse.knowledge_pack` so it's visible in the API/report without waiting for AI.

### Data Collection Engine (`app/collection/knowledge_bridge.py`)

`signature_from_profile(profile) -> KnowledgePackSignature` adapts a `ProductProfile`'s already-resolved `category`, `material`, `weight_class`, `fragility`, and `detected_marketplace` fields into a signature. This is a one-directional dependency (`collection` → `knowledge`); the Knowledge Engine itself never imports from `app.collection`, keeping it a reusable leaf module.

`app/collection/bridge.py` (Product Profile → Research Engine) now also passes `detected_marketplace` through to the research input dict, so the orchestrator's own knowledge lookup can use it — this was a real gap found and fixed during Phase 3 (the field existed on the profile but was previously dropped at the bridge).

### API (`app/api/v1/knowledge.py`)

Two inspection endpoints, useful independent of the DCE/Research Engine flow:

- `GET /api/v1/knowledge/pack/preview?category=&material=&marketplace=&weight_class=&fragility=` — ad-hoc, no saved profile required.
- `GET /api/v1/knowledge/pack/for-profile/{profile_id}` — the exact pack a saved profile would get if sent to research.

## 7. Extension points (not implemented)

- **Category-specific rubric variants** (PRS §18 Future Improvement #1) could read `CategoryKnowledge.typical_margin_band_pct` / `typical_return_rate_pct` as the actual per-category thresholds a future Decision Engine calibration uses, instead of today's flat weight table.
- **Sub-category knowledge**: the category taxonomy has no sub-category detector yet (Phase 2 known gap) — `data/categories.json` has no sub-category-keyed entries because there's nothing to key them from yet.
- **A DB-backed `KnowledgeRepository`**: today's `loader.py` is the only "repository" — a JSON-file reader. If this becomes an admin-editable knowledge base, the natural seam is a `KnowledgeRepository` protocol mirroring `app/db/repository.py`'s pattern (JSON-file default, Supabase-backed alternative), with the cache-invalidation story from §5 revisited at that point.
- **`manufacturer_direct` / `wholesaler` supplier entries** are seeded in `supplier_intelligence.json` but currently unreachable — the DCE has no explicit "sourcing platform" field beyond what's parsed from a marketplace URL (only `indiamart`/`tradeindia` are reachable that way). A future DCE field for supplier type would make them reachable without any Knowledge Engine change.
- **Material signature normalization**: `KnowledgePackSignature.materials` is an unordered-in-practice tuple — `("glass","metal")` and `("metal","glass")` are cached as distinct signatures today (harmless duplication, not a correctness bug, documented and tested). Worth normalizing (e.g. sort the tuple) if multi-material profiles become common enough for the cache duplication to matter.
- **AI provider consumption**: once `app/ai/providers/` has a real implementation, an AI agent reads `context.knowledge_pack` as grounding context alongside the product's own DCE-collected evidence — the pack is already shaped for this (PRS §18), no schema change anticipated.
