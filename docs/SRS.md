# EcomOS AI — Software Requirement Specification (SRS)

**Product framing:** An Ecom Intelligence Operating System — a persistent, accumulating intelligence layer for ecommerce product decisions, not a one-shot AI report generator.
**Scope:** 7-Day MVP
**Status:** DRAFT v0.2 — revised per review. Pending approval. No implementation until sign-off.
**Document version:** 0.2 (supersedes 0.1 — see §22 Changelog)

---

## 0. Product Vision & Repositioning

v0.1 framed EcomOS AI as a tool: enter a product, get a report. That framing undersells what the data model should actually support.

**v0.2 framing: EcomOS AI is an Operating System, not a tool.**

The distinction is architectural, not marketing:
- A *tool* run produces a report and forgets. An *OS* accumulates: every analysis writes to durable history tables (pricing history, trend history, supplier catalog, competitor catalog) that outlive the single report that created them, so the 50th time someone researches "Drawer Organizer" the system has a longitudinal view, not just a fresh LLM call.
- A *tool* has fixed features. An *OS* has a **module/agent interface** and a **connector interface** — new intelligence capabilities and new data sources plug in without touching the core.
- A *tool*'s output is opaque. An *OS* is auditable: every score is traceable to the exact prompt version, sources, and deterministic rubric that produced it.

This SRS is written to that standard from day one, even though the MVP's *feature surface* (7-day scope) stays disciplined — see §19 Roadmap and the "never overengineer" guardrails carried over from v0.1 (§1.4).

---

## 1. Overall Architecture

### 1.1 High-level system diagram (textual)

```
┌───────────────────────┐        HTTPS/JSON only        ┌────────────────────────────────┐
│  Next.js 15 Frontend  │ ─────────────────────────────▶ │      FastAPI Backend           │
│  (Vercel)             │ ◀───────────────────────────── │      (Render / Railway)        │
│  - No auth UI         │   X-Session-Id header (anon)     │  ┌───────────────────────────┐ │
│  - App Router, TS     │                                   │  │ Orchestrator             │ │
│  - Tailwind + shadcn  │                                   │  │  - 12 Agent Interface    │ │
│  - Recharts           │                                   │  │  - asyncio.gather        │ │
└───────────────────────┘                                   │  │  - partial-failure logic │ │
                                                              │  └──────────┬────────────────┘ │
                                                              │             │                  │
                                                              │  ┌──────────▼────────────────┐ │
                                                              │  │ Cache Layer (analysis_cache)│ │
                                                              │  └──────────┬────────────────┘ │
                                                              │             │                  │
                                                              │  ┌──────────▼────────────────┐ │
                                                              │  │ Prompt Registry (versioned)│ │
                                                              │  └──────────┬────────────────┘ │
                                                              │             │                  │
                                                              │  ┌──────────▼────────────────┐ │
                                                              │  │ Connector Layer (interfaces │ │
                                                              │  │ only — NullConnector in MVP)│ │
                                                              │  └──────────┬────────────────┘ │
                                                              └─────────────┼──────────────────┘
                                                                            │
                                                          ┌─────────────────┼─────────────────┐
                                                          ▼                 ▼                 ▼
                                              ┌────────────────┐ ┌──────────────────┐ ┌───────────────┐
                                              │  Supabase       │ │  OpenAI GPT-5.5   │ │ (Future)       │
                                              │  Postgres only  │ │  API              │ │ Marketplace    │
                                              │  (service role, │ │  (reasoning only  │ │ APIs / feeds   │
                                              │  no client-side │ │  — never the      │ │ via Connector  │
                                              │  Supabase Auth) │ │  scorer, see §6)  │ │ interface      │
                                              └────────────────┘ └──────────────────┘ └───────────────┘
```

### 1.2 Key architectural changes from v0.1

| Change | Reason |
|---|---|
| **Auth removed.** Frontend never talks to Supabase directly; all DB access goes through the FastAPI backend using the Supabase **service role** key. | Review requirement: anonymous MVP. Side effect: simpler security model (no client-side RLS to get wrong under time pressure — see v0.1 Risk R9), single point of validation/rate-limiting. Anonymous scoping uses an app-generated `session_id`, not Postgres RLS (§18). |
| **6 modules → 12 agents.** | Review requirement. See §11 for the full roster and §1.4 for why this doesn't imply 12x the infrastructure. |
| **Scoring rubric layer added between agent output and numeric score.** | Review requirement: "LLMs provide reasoning only." Agents now return structured qualitative *signals*, not numbers. A deterministic `scoring/rubrics.py` maps signals → 0–100 sub-scores. See §6. |
| **Evidence Score added alongside Confidence Score.** | Review requirement. See §6. |
| **Prompt registry moved into Postgres (`prompts` table), versioned.** | Review requirement: prompt versioning with full reproducibility — every `module_results` row references the exact prompt version used. See §5. |
| **Cache layer (`analysis_cache`) added.** | Review requirement: repeated-product-analysis caching. See §7. |
| **Connector interface layer added (`MarketplaceConnector` ABC + `NullConnector`).** | Review requirement: future marketplace integrations without implementing scraping now. See §8. |
| **History tables added: `suppliers`, `competitors`, `pricing_history`, `trend_history`.** | Review requirement: future-proof DB. See §3. |
| **`agent_logs` table added** for raw execution/audit trail, separate from the clean `module_results` business output. | Observability requirement (§15 NFR). |

### 1.3 Architectural style (unchanged principles from v0.1, still correct)

- **Clean/layered backend**: `api/` → `services/` (orchestration, cache, rubric scoring) → `ai/agents/` (12 agent implementations) → `connectors/` → `db/` (repositories) → `core/` (config, errors, rate limiting).
- **Modular monolith**, not microservices — still one deployable FastAPI app. 12 agents is more reason to keep this a single process with a clean interface, not less: a network boundary per agent would multiply the 7-day operational burden for no MVP benefit.
- **Async job pattern, no external queue** — `asyncio.gather` + Postgres status polling, as in v0.1. Confirmed still sufficient at 12 agents (see §1.4).

### 1.4 Why 12 agents doesn't mean 12x complexity (guardrail against overengineering)

The review asks for 12 agents, not 12 microservices, 12 queues, or 12 prompt-engineering subprojects. The scaling discipline:
- All 12 implement one `ResearchAgent` interface (§4) — the orchestrator code does not grow per agent, it iterates a registry.
- All 12 run inside the same `asyncio.gather` batch, same timeout/partial-failure handling already designed in v0.1 (§1.2 there, carried forward here).
- Prompts are data (rows in `prompts`, §5), not 12 bespoke code paths.
- Two of the 12 (**Profit & Unit Economics**, **Decision Synthesis**) are deterministic/aggregating and make **zero** GPT-5.5 calls for their scoring — only Decision Synthesis makes one LLM call, for the narrative (strengths/weaknesses prose), never for the number.
- Net new infra for 12 vs. 6: one more DB table category (§3), a rubric-mapping module (§6), a prompt registry (§5), a cache layer (§7), a connector ABC (§8). All are still single-process, still Postgres-only, still no new external system.

---

## 2. Folder Structure

```
ecomos-ai/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                       # Home
│   │   ├── report/[id]/page.tsx           # Report view
│   │   ├── reports/page.tsx               # Recent + saved (session-scoped)
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                            # shadcn/ui primitives
│   │   ├── home/                          # SearchBox, RecentSearches, SavedReports
│   │   ├── report/                        # AgentCard, ScoreGauge, EvidenceBadge, ConfidenceBadge, RiskBadge
│   │   └── profit-calculator/
│   ├── lib/
│   │   ├── api-client.ts                  # typed fetch wrapper (adds X-Session-Id header)
│   │   ├── session.ts                     # generates/persists anonymous session id (localStorage)
│   │   └── formatters.ts
│   ├── types/                             # mirrors backend Pydantic ModuleResponse schema
│   └── hooks/                             # useReportPolling, useRecentSearches
│
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── reports.py
│   │   │   ├── profit_calculator.py
│   │   │   └── recent_searches.py
│   │   ├── services/
│   │   │   ├── orchestrator.py            # runs 12 agents, merges results
│   │   │   ├── cache_service.py           # analysis_cache read/write, TTL policy
│   │   │   ├── prompt_registry.py         # loads active prompt version per agent
│   │   │   └── report_service.py
│   │   ├── scoring/
│   │   │   ├── rubrics.py                 # deterministic signal → sub-score mapping (per agent)
│   │   │   ├── evidence.py                # deterministic Evidence Score computation
│   │   │   └── decision.py                # weighted roll-up (§6 table) → overall score/band
│   │   ├── ai/
│   │   │   ├── base_agent.py              # ResearchAgent interface (ABC)
│   │   │   ├── gpt_client.py              # GPT-5.5 wrapper: retries, timeouts, JSON-schema mode
│   │   │   ├── schemas.py                 # ModuleResponse, SourceRef (shared response schema, §4)
│   │   │   └── agents/
│   │   │       ├── demand_agent.py
│   │   │       ├── competition_agent.py
│   │   │       ├── pricing_agent.py
│   │   │       ├── trend_seasonality_agent.py
│   │   │       ├── review_mining_agent.py
│   │   │       ├── keyword_discoverability_agent.py
│   │   │       ├── supplier_sourcing_agent.py
│   │   │       ├── logistics_risk_agent.py
│   │   │       ├── compliance_agent.py
│   │   │       ├── brand_positioning_agent.py
│   │   │       ├── profit_agent.py         # deterministic, no LLM call
│   │   │       └── decision_synthesis_agent.py
│   │   ├── connectors/
│   │   │   ├── base_connector.py           # MarketplaceConnector interface (ABC)
│   │   │   └── null_connector.py           # MVP default: "unavailable, manual verification"
│   │   ├── db/
│   │   │   └── repositories/               # one repo per table in §3
│   │   ├── core/
│   │   │   ├── config.py                   # env vars only
│   │   │   ├── session.py                  # anonymous session middleware
│   │   │   ├── rate_limit.py                # per-session + per-IP limiter
│   │   │   └── errors.py                    # friendly error mapping (§17)
│   │   └── main.py
│   └── requirements.txt
│
├── shared/
│   └── scoring.md                          # weight table, single source of truth (§6)
│
├── prompts/                                # seed source for the `prompts` table (git-versioned text,
│   │                                        # loaded into DB by a migration/seed script — DB is the
│   │                                        # runtime source of truth, git is the review/diff trail)
│   ├── demand_v1.md
│   ├── competition_v1.md
│   ├── pricing_v1.md
│   ├── trend_seasonality_v1.md
│   ├── review_mining_v1.md
│   ├── keyword_discoverability_v1.md
│   ├── supplier_sourcing_v1.md
│   ├── logistics_risk_v1.md
│   ├── compliance_v1.md
│   ├── brand_positioning_v1.md
│   └── decision_synthesis_v1.md
│
├── docs/
│   ├── SRS.md                              # this document
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── ROADMAP.md
│   └── INSTALL.md
│
├── tests/
│   ├── backend/                            # pytest: unit (rubrics, evidence, cache) + API tests
│   └── frontend/                           # vitest/RTL
│
├── README.md
└── .env.example
```

---

## 3. Database Schema (Supabase / Postgres)

All access is via the backend's Supabase **service role** key (no client-side Supabase Auth, no RLS — see §18 for why). All tables use `uuid` primary keys and `created_at` timestamps.

```sql
-- Anonymous session tracking (replaces the users/profiles table from v0.1)
create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  product_name text not null,
  normalized_name text not null,                 -- lowercased/trimmed; cache + history key
  category text,                                  -- nullable, future classification
  created_at timestamptz not null default now()
);
create index on public.products (normalized_name);

-- Research history: one row per analysis run. This table itself IS the research history —
-- no separate "history" table is needed, every run is preserved, never overwritten.
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete set null,
  product_id uuid references public.products(id) on delete cascade,
  status text not null default 'pending',          -- pending|running|partial|completed|failed
  overall_score numeric(5,2),
  risk_level text,
  recommendation text,
  is_saved boolean not null default false,
  served_from_cache boolean not null default false,
  prompt_bundle jsonb,                              -- {agent_type: prompt_version} used for this run
  error_message text,
  pdf_url text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);
create index on public.reports (session_id, created_at desc);
create index on public.reports (product_id, created_at desc);

-- Prompt versioning (review requirement)
create table public.prompts (
  id uuid primary key default gen_random_uuid(),
  agent_type text not null,                         -- one of the 12 agent identifiers
  version integer not null,
  template text not null,
  change_notes text,
  is_active boolean not null default false,
  created_at timestamptz not null default now(),
  unique (agent_type, version)
);
create unique index one_active_prompt_per_agent
  on public.prompts (agent_type) where (is_active);

-- Standardized module output (shared response schema, §4), now with Evidence + Confidence
create table public.module_results (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  agent_type text not null,
  status text not null default 'pending',           -- pending|running|completed|failed
  data jsonb not null default '{}',
  signals jsonb not null default '{}',               -- structured qualitative judgments the rubric consumes
  reasoning text,
  confidence_score numeric(4,3),                     -- 0-1, LLM self-assessed + heuristic discount
  evidence_score numeric(4,3),                        -- 0-1, deterministically computed (§6)
  sub_score numeric(5,2),                             -- 0-100, deterministic rubric output
  sources jsonb not null default '[]',                 -- [{type,name,url,retrieved_at}]
  requires_manual_verification boolean not null default false,
  prompt_id uuid references public.prompts(id),
  latency_ms integer,
  token_usage jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  unique (report_id, agent_type)
);

-- Supplier catalog — reusable across products/reports, not a one-off jsonb blob (review requirement)
create table public.suppliers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  source text not null,                              -- IndiaMART|TradeIndia|manual|other
  location text,
  moq text,
  approx_price_min numeric(10,2),
  approx_price_max numeric(10,2),
  sample_available boolean,
  contact_info jsonb,
  verification_status text not null default 'unverified', -- unverified|manual_pending|manual_verified|rejected
  notes text,
  created_at timestamptz not null default now()
);

-- Join table: which report surfaced which supplier lead (a supplier can recur across products)
create table public.supplier_leads (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  supplier_id uuid references public.suppliers(id) on delete cascade,
  confidence_score numeric(4,3),
  evidence_score numeric(4,3),
  created_at timestamptz not null default now(),
  unique (report_id, supplier_id)
);

-- Competitor catalog (review requirement)
create table public.competitors (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  name text not null,                                 -- brand/seller name
  marketplace text not null,                          -- amazon|flipkart|meesho|shopify(future)
  rating numeric(3,2),
  review_count integer,
  source text not null,                               -- llm_reasoning|web_search|connector|manual
  created_at timestamptz not null default now()
);

-- Pricing history — append-only time series (review requirement)
create table public.pricing_history (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  competitor_id uuid references public.competitors(id) on delete set null, -- null = aggregate market price point
  report_id uuid references public.reports(id) on delete set null,
  marketplace text not null,
  price numeric(10,2) not null,
  observed_at timestamptz not null default now(),
  source text not null,
  created_at timestamptz not null default now()
);
create index on public.pricing_history (product_id, observed_at desc);

-- Trend history — append-only time series (review requirement)
create table public.trend_history (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  report_id uuid references public.reports(id) on delete set null,
  signal_date date not null,
  demand_sub_score numeric(5,2),
  trend_label text,                                    -- Growing|Stable|Declining
  source text not null,
  created_at timestamptz not null default now()
);
create index on public.trend_history (product_id, signal_date desc);

-- Profit calculator (unchanged from v0.1, still deterministic, still report-scoped)
create table public.profit_calculations (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  selling_price numeric(10,2) not null,
  buying_price numeric(10,2) not null,
  shipping_cost numeric(10,2) not null default 0,
  packaging_cost numeric(10,2) not null default 0,
  marketplace_fee_pct numeric(5,2) not null default 0,
  ad_cost numeric(10,2) not null default 0,
  gst_pct numeric(5,2) not null default 18,
  return_cost numeric(10,2) not null default 0,
  rto_cost numeric(10,2) not null default 0,
  net_profit numeric(10,2),
  margin_pct numeric(5,2),
  breakeven_units integer,
  roi_pct numeric(6,2),
  created_at timestamptz not null default now()
);

create table public.recent_searches (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete cascade,
  product_name text not null,
  report_id uuid references public.reports(id) on delete cascade,
  searched_at timestamptz not null default now()
);

-- Cache layer (review requirement, §7)
create table public.analysis_cache (
  id uuid primary key default gen_random_uuid(),
  cache_key text not null unique,                     -- hash(normalized_name + agent_type + prompt_version)
  agent_type text,                                     -- null = reserved for future full-report cache
  payload jsonb not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index on public.analysis_cache (expires_at);

-- Raw execution/audit log — separate from module_results' clean business output (review requirement)
create table public.agent_logs (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  agent_type text not null,
  prompt_id uuid references public.prompts(id),
  status text not null,                                -- success|error|timeout|cache_hit
  latency_ms integer,
  error_message text,
  created_at timestamptz not null default now()
);
create index on public.agent_logs (report_id);

-- Future marketplace connector registry — config only, no scraping implementation (review requirement, §8)
create table public.connector_configs (
  id uuid primary key default gen_random_uuid(),
  marketplace text not null unique,                    -- amazon|flipkart|meesho|shopify
  connector_type text not null default 'none',          -- none|api|partner_feed
  is_enabled boolean not null default false,
  config jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- Rate limiting (anonymous, session + IP scoped)
create table public.rate_limit_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete cascade,
  ip_address text,
  endpoint text not null,
  window_start timestamptz not null,
  request_count integer not null default 1
);
```

**Design notes:**
- No Postgres RLS anywhere — there's no Supabase Auth JWT to key it on. Anonymous scoping (`session_id`) is enforced entirely in the FastAPI layer, which is the only thing holding the service-role key. This is a deliberate simplification enabled by removing auth (§1.2, §18) — it removes v0.1's Risk R9 (RLS misconfiguration) instead of needing to get RLS right under time pressure.
- `pricing_history` and `trend_history` are **append-only** and populated only on a genuine fresh agent run — a cache hit does *not* write a new history row, because a cache hit is not a new observation (§7). This keeps the longitudinal data honest.
- `module_results.signals` (structured judgments) vs `module_results.sub_score` (the number): this split is the mechanism behind "LLMs provide reasoning only" — see §6.

---

## 4. Shared Response Schema (Standardized Module Output)

Every one of the 12 agents — LLM-driven or deterministic — returns the same Pydantic envelope. The orchestrator, cache layer, and frontend `AgentCard` component all work against this one shape, regardless of agent:

```python
class SourceRef(BaseModel):
    type: Literal["llm_reasoning", "web_search", "connector", "manual", "deterministic"]
    name: str
    url: Optional[str] = None
    retrieved_at: Optional[datetime] = None

class ModuleResponse(BaseModel):
    agent_type: str
    schema_version: str            # bump when `data`/`signals` shape changes
    prompt_version: Optional[int]  # null for deterministic agents
    data: dict                     # agent-specific payload (still validated against a
                                    #   per-agent Pydantic sub-schema registered in schemas.py —
                                    #   jsonb in Postgres, strongly typed at the API boundary)
    signals: dict                  # structured qualitative judgments consumed by scoring/rubrics.py
    reasoning: str
    confidence_score: float        # 0.0-1.0
    evidence_score: float          # 0.0-1.0
    sub_score: float               # 0-100, computed by scoring/rubrics.py, NEVER by the LLM directly
    sources: list[SourceRef]
    requires_manual_verification: bool = False
    generated_at: datetime
```

`ResearchAgent` interface every agent implements:

```python
class ResearchAgent(ABC):
    agent_type: str
    scored: bool = True   # False only for Decision Synthesis, which aggregates rather than scores itself

    @abstractmethod
    async def run(self, context: ReportContext) -> ModuleResponse: ...
```

A new (13th, 14th...) agent is: one class implementing this interface, one row added to the agent registry, one prompt seeded into `prompts`, one rubric function added to `scoring/rubrics.py`. Nothing else in the system changes — this is what "future modular AI agents" means concretely.

---

## 5. Prompt Versioning Strategy

- Prompts live as git-tracked markdown in `/prompts/*_v{n}.md` for review/diff, but the **runtime source of truth is the `prompts` table**. A seed script upserts file content into rows on deploy.
- Exactly one `is_active = true` row per `agent_type` (enforced by the partial unique index in §3). `prompt_registry.py` loads the active version at orchestration time.
- Every `module_results` row stores the exact `prompt_id` used, and every `reports` row stores the full `prompt_bundle` (map of agent_type → version) for that run — so **any past report is fully reproducible**: you can see precisely which prompt wording produced which score.
- Bumping a prompt version is additive (insert new row, flip `is_active`), never an in-place edit of an existing version — past reports must keep referencing the exact wording that generated them.
- Rolling back = flip `is_active` back to a prior version. No deploy needed for wording changes; a deploy is only needed when a prompt's *schema* (the `signals` shape it must produce) changes, which also requires a matching `scoring/rubrics.py` update and a `schema_version` bump in §4.

---

## 6. Confidence Score vs. Evidence Score — and Why Scoring Stays Deterministic

Two distinct numbers, computed two distinct ways, so they can never be conflated:

| | Confidence Score | Evidence Score |
|---|---|---|
| **Question it answers** | "How certain does the model say it is?" | "How much can we actually verify this claim?" |
| **Computed by** | LLM self-report, then heuristically discounted by the backend (e.g., halved if the agent had to fall back to pure model knowledge with zero sources) | 100% deterministic backend formula — the LLM never reports this number |
| **Inputs** | Model's stated certainty + fallback-mode discount | `sources` list: source type mix, source count, cross-agent corroboration |
| **Failure mode it guards against** | An overconfident model | A confident-*sounding* answer with nothing behind it |

**Evidence Score formula** (`scoring/evidence.py`, illustrative — tunable but fixed in code, not left to the model):

```
source_type_weight = { connector: 1.0, manual: 0.9, web_search: 0.7, llm_reasoning: 0.3 }
type_component   = average(source_type_weight[s.type] for s in sources)      # 0-1
count_component  = min(1.0, len(sources) / 3)                                 # 0-1, caps at 3+ sources
corroboration    = 0.2 if another agent's data independently agrees, else 0   # e.g. Pricing vs Competition
                    price ranges overlap

evidence_score = clamp(0.5*type_component + 0.3*count_component + corroboration, 0, 1)
```

### Scoring stays deterministic — the mechanism

Per the review's explicit requirement, **no agent is ever asked to output the number that drives the launch/reject decision.** Instead:

1. An LLM-driven agent's prompt asks only for **structured qualitative signals** — e.g., the Demand agent returns `signals = {"search_interest_trend": "increasing", "category_maturity": "emerging", "review_velocity": "moderate", ...}`, never `"demand_score": 7`.
2. `scoring/rubrics.py` contains one pure function per agent, e.g. `score_demand(signals: dict) -> float`, implemented as a fixed lookup/rule table (e.g., `increasing` + `emerging` → base 70, `+10` if review velocity is `moderate` or `high`, capped at 100). Same signals in → same score out, always, with no model variance.
3. The agent's `sub_score` field (§3, §4) is that rubric's output, not anything the LLM wrote.
4. **Decision Synthesis Agent** (`scoring/decision.py`) takes the 11 scored agents' `sub_score` × weight (table below) → `overall_score`, then maps to a band. This arithmetic is plain Python. Decision Synthesis *also* makes one LLM call, but only to generate the human-readable strengths/weaknesses narrative — that call never touches the number.

This means: two runs with identical `signals` always produce an identical `overall_score`, even across different prompt wording, model versions, or days — reproducibility and auditability were the point of the review comment, and this is the concrete mechanism.

### Scoring weight table (12 agents, 100 points, `shared/scoring.md` is the single source of truth)

| # | Agent | Weight | Scored? |
|---|---|---|---|
| 1 | Demand Intelligence | 15 | Yes |
| 2 | Competitive Landscape | 10 | Yes |
| 3 | Pricing Intelligence | 8 | Yes |
| 4 | Trend & Seasonality | 7 | Yes |
| 5 | Review Mining | 8 | Yes |
| 6 | Keyword & Discoverability | 5 | Yes |
| 7 | Supplier Sourcing | 8 | Yes |
| 8 | Logistics & Fulfillment Risk | 12 | Yes |
| 9 | Compliance & Regulatory | 8 | Yes |
| 10 | Brand & Positioning | 8 | Yes |
| 11 | Profit & Unit Economics | 11 | Yes (deterministic, no LLM) |
| 12 | Decision Synthesis | — | No (aggregator + narrative only) |
| | **Total** | **100** | |

Bands unchanged from v0.1: **90+ Launch · 80–89 Strong Candidate · 70–79 Test First · <70 Reject.**

---

## 7. Caching Strategy

**Goal:** avoid re-paying for GPT-5.5 calls (and re-waiting ~seconds per agent) when the same product is analyzed again soon after, while keeping the accumulating history tables (§3) honest.

- **Cache key:** `hash(normalized_product_name + agent_type + active_prompt_version)`. Per-agent, not per-report — if only the Compliance prompt was bumped, Demand/Competition/etc. still hit cache.
- **TTL is agent-specific**, reflecting how fast that data actually goes stale:
  - Pricing Intelligence, Trend & Seasonality: 24h (fast-moving)
  - Demand, Competition, Review Mining, Keyword, Brand: 72h
  - Supplier Sourcing, Compliance & Regulatory: 14 days (slow-moving)
  - Profit, Decision Synthesis: never cached — cheap/instant (Profit) or must reflect the freshest inputs (Decision Synthesis)
- **On a new report request**, the orchestrator checks `analysis_cache` per agent before calling GPT-5.5. A hit: reuse the payload, write a `module_results` row with `status=completed` and log an `agent_logs` row with `status=cache_hit` (so latency/cost dashboards can see the hit rate) — but **do not** write a new `pricing_history`/`trend_history` row, since nothing new was actually observed.
- **`reports.served_from_cache`** is set true if *any* agent in that run was served from cache, and the report UI shows a small "Partially/fully cached — last refreshed <time>" indicator rather than presenting cached data as if freshly generated. Never silently disguise cache as a live call.
- **Cache invalidation:** flipping a prompt's `is_active` version implicitly invalidates old cache entries (the cache key includes prompt version, so a new version simply misses). No manual cache-busting needed.

---

## 8. Connector Interfaces (Future Marketplace Integrations)

Per the review: build the **interface**, not scraping. This preserves the v0.1 decision to avoid scraping Amazon/Flipkart/Meesho (ToS/legal risk, v0.1 Risk R2/R3) while making the eventual "plug in a real data provider" story a config change, not a rewrite.

```python
class ConnectorResult(BaseModel):
    available: bool
    data: dict | None
    source: str            # e.g. "amazon_partner_api"
    retrieved_at: datetime | None

class MarketplaceConnector(ABC):
    marketplace: str

    @abstractmethod
    async def fetch_competitor_snapshot(self, product_name: str) -> ConnectorResult: ...

    @abstractmethod
    async def fetch_price_points(self, product_name: str) -> ConnectorResult: ...
```

- **MVP ships exactly one implementation: `NullConnector`**, which returns `available=False` for every marketplace. Agents that consult a connector (Competitive Landscape, Pricing Intelligence) check this first; when unavailable, they fall back to GPT-5.5 reasoning-only mode and their `SourceRef.type` is `llm_reasoning` (lowering their Evidence Score honestly, per §6 — the system doesn't pretend connector data exists when it doesn't).
- `connector_configs` (§3) is the registry of what marketplaces/connector types exist and whether they're enabled — populated with `is_enabled=false` rows for `amazon`, `flipkart`, `meesho` in the MVP seed data, so turning one on later is a config + one new class, not a schema change.
- **Explicitly out of scope for the 7-day MVP:** any real scraping or API integration code. This section is architecture-readiness only.

---

## 9. API Design / API Contracts

Base path `/api/v1`. Every request carries an `X-Session-Id` header (see §18); the backend creates a `sessions` row transparently on first sight of a new id. Error envelope unchanged from v0.1 (friendly, never a stack trace — full policy in §17):

```json
{ "error": { "code": "AGENT_TIMEOUT", "message": "We couldn't finish the pricing analysis in time. The rest of your report is ready." } }
```

### `POST /reports`
Request:
```json
{ "product_name": "Drawer Organizer" }
```
Response `202 Accepted`:
```json
{ "report_id": "b3f1...", "status": "pending" }
```

### `GET /reports/{id}`
Response (mid-run example — partial, progressive):
```json
{
  "report_id": "b3f1...",
  "status": "running",
  "served_from_cache": false,
  "agents": [
    { "agent_type": "demand", "status": "completed", "sub_score": 78.0,
      "confidence_score": 0.81, "evidence_score": 0.62,
      "reasoning": "...", "requires_manual_verification": false },
    { "agent_type": "pricing", "status": "running" },
    { "agent_type": "compliance", "status": "pending" }
  ],
  "overall_score": null,
  "recommendation": null
}
```
Response (completed example, abbreviated):
```json
{
  "report_id": "b3f1...",
  "status": "completed",
  "served_from_cache": true,
  "overall_score": 82.4,
  "risk_level": "medium",
  "recommendation": "Strong Candidate",
  "agents": [ "...12 entries, shape as above with status=completed..." ],
  "manual_verification_checklist": [
    "Supplier MOQ and pricing must be confirmed directly with each supplier.",
    "GST/BIS compliance flags are estimates — confirm with a customs/compliance professional."
  ]
}
```

### `POST /reports/{id}/profit-calculator`
Request:
```json
{ "selling_price": 499, "buying_price": 180, "shipping_cost": 40, "packaging_cost": 10,
  "marketplace_fee_pct": 15, "ad_cost": 30, "gst_pct": 18, "return_cost": 25, "rto_cost": 35 }
```
Response `200 OK`:
```json
{ "net_profit": 121.35, "margin_pct": 24.3, "breakeven_units": 42, "roi_pct": 67.4 }
```
Deterministic, no LLM call, safe to call on every debounced keystroke.

### `GET /reports/{id}/pdf`
Response: `{ "pdf_url": "https://.../signed-url" }` (generated on first request, cached to Supabase Storage thereafter).

### `GET /recent-searches`
Scoped by `X-Session-Id`. Response: list of `{ product_name, report_id, searched_at }`, most recent first.

### `GET /reports?saved=true`
Session-scoped saved reports list, paginated.

---

## 10. Frontend Pages & Wireframes

### 10.1 Home (`/`)

```
┌──────────────────────────────────────────────────────────┐
│  EcomOS AI                                                │
│  The AI Operating System for Ecommerce Product Decisions │
│                                                            │
│  ┌──────────────────────────────────────┐  ┌──────────┐  │
│  │ e.g. Drawer Organizer                 │  │ Analyze  │  │
│  └──────────────────────────────────────┘  └──────────┘  │
│                                                            │
│  Recent Searches                                          │
│  [ Drawer Organizer ] [ Yoga Mat ] [ Car Phone Holder ]   │
│                                                            │
│  Saved Reports                                            │
│  ┌────────────────────┐ ┌────────────────────┐            │
│  │ Drawer Organizer    │ │ Yoga Mat            │            │
│  │ 82 · Strong Cand.   │ │ 61 · Test First     │            │
│  └────────────────────┘ └────────────────────┘            │
└──────────────────────────────────────────────────────────┘
```

### 10.2 Report page (`/report/[id]`) — running state

```
┌──────────────────────────────────────────────────────────┐
│  ← Back            Drawer Organizer                       │
│  Analyzing... (7 / 12 agents complete)                    │
│                                                            │
│  ✓ Demand              ✓ Competitive Landscape             │
│  ✓ Pricing             ✓ Trend & Seasonality               │
│  ✓ Review Mining       ⏳ Keyword & Discoverability        │
│  ⏳ Supplier Sourcing   … Logistics Risk   … Compliance     │
│  … Brand Positioning   … Profit            … Decision      │
└──────────────────────────────────────────────────────────┘
```

### 10.3 Report page — completed state

```
┌──────────────────────────────────────────────────────────┐
│  Drawer Organizer                     [Save] [Download PDF]│
│  Fully cached · refreshed 3h ago                           │
│                                                            │
│   ┌────────────┐   Overall Score: 82.4 / 100               │
│   │   ▓▓▓▓▓▓▓  │   Recommendation: Strong Candidate         │
│   │   82.4     │   Risk: Medium                             │
│   └────────────┘                                            │
│                                                            │
│  ▸ Demand              Confidence 0.81   Evidence 0.62      │
│  ▸ Competitive Landscape                                    │
│  ▸ Pricing Intelligence                                     │
│  ▸ Trend & Seasonality                                      │
│  ▸ Review Mining                                             │
│  ▸ Keyword & Discoverability                                 │
│  ▸ Supplier Sourcing              [Manual verification req.]│
│  ▸ Logistics & Fulfillment Risk                              │
│  ▸ Compliance & Regulatory        [Manual verification req.]│
│  ▸ Brand & Positioning                                       │
│  ▸ Profit & Unit Economics (edit your costs ↓)               │
│  ▸ Risks & Manual Verification Checklist                     │
└──────────────────────────────────────────────────────────┘
```

### 10.4 Profit Calculator panel (inline, editable)

```
┌──────────────────────────────────────────┐
│ Selling Price  [ 499 ]   Buying Price [180]│
│ Shipping [40]  Packaging [10]  Ads [30]    │
│ Marketplace Fee % [15]  GST % [18]         │
│ Return Cost [25]  RTO Cost [35]            │
│                                            │
│ Net Profit: ₹121.35   Margin: 24.3%        │
│ Breakeven: 42 units   ROI: 67.4%           │
│                                            │
│ [ Re-run recommendation with these costs ] │
└────────────────────────────────────────────┘
```

Every `AgentCard` (expanded) shows, uniformly across all 12 agents per the shared schema (§4): sub-score, confidence badge, evidence badge, reasoning text, source list, and a manual-verification flag when applicable — one component, driven by data, not 12 bespoke layouts.

---

## 11. Backend Modules — The 12 AI Agents

Each row: what it analyzes, its `signals` (what the LLM actually returns — never a raw score), and its rubric basis.

| # | Agent | Analyzes | Example signals (LLM output) | Deterministic rubric basis |
|---|---|---|---|---|
| 1 | **Demand Intelligence** | Category demand, growth direction | `search_interest_trend`, `category_maturity`, `review_velocity` | Lookup table over signal combinations → 0-100 |
| 2 | **Competitive Landscape** | Amazon/Flipkart seller density, brand dominance | `seller_density`, `brand_dominance_level`, `differentiation_headroom` | Lookup table; connector data (§8) preferred over reasoning-only when available |
| 3 | **Pricing Intelligence** | Price band, price volatility, undercut risk | `price_band_estimate`, `price_spread`, `discount_frequency` | Range-based scoring; writes `pricing_history` rows on fresh runs |
| 4 | **Trend & Seasonality** | Seasonal pattern, momentum | `seasonality_pattern`, `momentum_direction` | Lookup table; writes `trend_history` rows on fresh runs |
| 5 | **Review Mining** | Customer sentiment on existing listings | `top_complaints[]`, `top_praises[]`, `missing_features[]`, `expectation_gap_size` | Complaint/praise ratio + gap-size → score |
| 6 | **Keyword & Discoverability** | Search-term coverage, listing SEO headroom | `keyword_coverage_level`, `search_term_competitiveness` | Coverage/competitiveness matrix |
| 7 | **Supplier Sourcing** | Manufacturers/wholesalers/importers (IndiaMART/TradeIndia) | `supplier_count_found`, `moq_flexibility`, `price_spread_across_suppliers` | Count/spread → readiness score; **always** `requires_manual_verification=true`; writes `suppliers`/`supplier_leads` |
| 8 | **Logistics & Fulfillment Risk** | Shipping cost profile, RTO risk, packaging fragility, return proneness | `fragility_level`, `rto_risk_level`, `return_proneness`, `shipping_cost_tier` | Weighted penalty table (this agent alone folds in what v0.1 scored as 4 separate line items: Shipping/Packaging/Return/RTO) |
| 9 | **Compliance & Regulatory** | GST applicability, BIS/import certification flags, safety flags for India | `gst_category`, `certification_flags[]`, `import_restriction_flag` | Flag-count penalty table; **always** `requires_manual_verification=true` |
| 10 | **Brand & Positioning** | Whitespace for a differentiated brand, private-label potential | `whitespace_level`, `differentiation_potential` | Lookup table |
| 11 | **Profit & Unit Economics** | User-entered costs → margin/ROI | *(no signals — pure arithmetic)* | 100% deterministic formula, no LLM call at all |
| 12 | **Decision Synthesis** | Aggregates 1–11, writes narrative | *(consumes others' `sub_score`+`signals`; one LLM call for prose only)* | `scoring/decision.py` weighted roll-up (§6) — the LLM call here never touches the number |

This directly supersedes v0.1's 6-module list; v0.1's Modules 1–6 map onto agents 1, 2, 5, 7, 11, 12 above, with the new agents (3, 4, 6, 8, 9, 10) filling gaps the review identified as missing intelligence surface for a real "Ecom Intelligence OS" (pricing history, seasonality, SEO, consolidated logistics risk, India-specific compliance, brand whitespace).

---

## 12. Data Flow

```
1. Frontend generates/reuses an anonymous session_id (localStorage), sends it as X-Session-Id on every call.
2. POST /reports → backend upserts `sessions` row (last_seen_at), creates/reuses `products` row,
   creates `reports` row (status=pending), creates 12 `module_results` rows (status=pending).
3. Background task starts orchestrator:
   a. status → running
   b. For each of the 11 scored agents (parallel, asyncio.gather):
        - check analysis_cache (§7) first
        - on miss: check connector (§8) if applicable → else GPT-5.5 call via gpt_client.py,
          using the active prompt_registry.py version for that agent_type
        - validate response against the agent's Pydantic sub-schema; on failure, retry once, then
          mark module_results.status=failed, requires_manual_verification=true
        - compute sub_score via scoring/rubrics.py, evidence_score via scoring/evidence.py
        - write module_results row; write agent_logs row; on a genuine (non-cache) Pricing/Trend
          run, also append pricing_history/trend_history rows
   c. Profit agent runs with either user-supplied costs or, if none yet, estimated defaults seeded
      from the Pricing agent's price band (clearly marked "Estimated — edit to your own costs")
   d. Decision Synthesis agent: scoring/decision.py computes overall_score/band from the 11 sub_scores
      (deterministic), then one GPT-5.5 call produces the strengths/weaknesses narrative only
4. reports.status → completed (all agents ok) / partial (≥1 agent failed, rest usable) /
   failed (Decision Synthesis itself could not run)
5. Frontend polls GET /reports/{id} every ~2-3s while pending/running, renders progressively (§10.2)
6. User edits Profit Calculator → POST /reports/{id}/profit-calculator → instant recompute, no LLM call.
   User may explicitly click "Re-run recommendation" to have Decision Synthesis re-aggregate with the
   new profit sub_score (not automatic, to avoid surprising repeated LLM calls on every keystroke)
7. User saves report / downloads PDF (server-rendered from completed report data, cached to Storage)
```

---

## 13. User Flow

```
Home page (no login, ever)
  → types "Drawer Organizer" → clicks Analyze
  → redirected to /report/{id}, sees 12-agent progress checklist fill in live
  → Decision Synthesis produces Overall Score + recommendation band
  → reviews Demand → Competitive Landscape → Pricing → Trend & Seasonality → Review Mining →
     Keyword & Discoverability → Supplier Sourcing → Logistics Risk → Compliance → Brand & Positioning
  → edits Profit Calculator with real costs → sees Net Profit/Margin/ROI update instantly
  → optionally clicks "Re-run recommendation" to fold in the new profit number
  → reads Risks + Manual Verification Checklist (Supplier + Compliance always listed here)
  → Saves report and/or Downloads PDF
  → returns to Home → sees it under Recent Searches / Saved Reports (scoped to their browser session)
```

---

## 14. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | User can submit a product name and receive a full 12-agent analysis without creating an account. |
| FR-2 | System transparently creates an anonymous session on first use and scopes recent/saved reports to it. |
| FR-3 | All 11 scored agents execute in parallel; total report time is not the sum of individual agent latencies. |
| FR-4 | Report view updates progressively as each agent completes, without requiring a full page reload. |
| FR-5 | If one or more agents fail, the report still completes in `partial` status with the remaining agents' data usable. |
| FR-6 | Every agent's output displays both a Confidence Score and an Evidence Score, distinctly labeled. |
| FR-7 | Supplier Sourcing and Compliance & Regulatory outputs are always flagged "manual verification required." |
| FR-8 | Profit Calculator inputs can be edited and recomputed instantly, independent of any AI call. |
| FR-9 | User can explicitly trigger Decision Synthesis to re-run using updated Profit Calculator numbers. |
| FR-10 | User can save a report and revisit it later from the same browser session. |
| FR-11 | User can download any completed report as a PDF. |
| FR-12 | Repeated analysis of the same (or near-identical, normalized) product name within an agent's TTL window is served from cache, visibly marked as cached. |
| FR-13 | Every scored number in a report is traceable to the exact prompt version that produced its inputs. |
| FR-14 | The system never renders raw JSON, AI prompts, or stack traces to the user. |
| FR-15 | Rate limiting applies per anonymous session (and per IP as a backstop) on report-creation. |

## 15. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Performance | A full 12-agent report (cache-miss case) completes in under ~60s end-to-end, given parallel execution. |
| NFR-2 | Performance | Profit Calculator recompute responds in under 300ms (no LLM involved). |
| NFR-3 | Scalability | Backend is stateless; horizontal scaling requires no session affinity (state lives in Postgres). |
| NFR-4 | Reliability | Single-agent failure never fails the whole report (§1.4, FR-5). |
| NFR-5 | Reliability | If the GPT-5.5 API is entirely unreachable, the report fails with one clear message, not 11 separate per-agent errors. |
| NFR-6 | Security | No API keys or secrets ever reach the frontend bundle; all AI/DB calls are backend-mediated. |
| NFR-7 | Security | Anonymous session ids are unguessable UUIDv4s; report ids likewise — no sequential ids. |
| NFR-8 | Privacy | No PII is collected in the anonymous MVP; sessions store no identity data. |
| NFR-9 | Observability | Every agent invocation (cache hit or miss, success or failure) is logged in `agent_logs` with latency. |
| NFR-10 | Maintainability | Adding a 13th agent requires no change to the orchestrator loop, only a new class + registry entry + prompt row + rubric function (§4). |
| NFR-11 | Cost control | Caching (§7) and per-session rate limiting (§9, FR-15) bound GPT-5.5 spend per unit time. |
| NFR-12 | Accessibility/UX | Dark mode by default, responsive down to mobile widths, no motion-heavy animation. |
| NFR-13 | Data retention | Anonymous session data (sessions, recent_searches, unsaved reports) has a documented retention window (e.g., 90 days) before eligible for purge — to be finalized with the user (§22 Open Questions carries this forward). |
| NFR-14 | Reproducibility | Any two reports run against identical `signals` and the same prompt/rubric versions always yield an identical `overall_score`. |

## 16. User Stories & Acceptance Criteria

**US-1 — Anonymous analysis**
As a seller with no account, I want to analyze a product immediately, so I don't hit a signup wall before seeing any value.
- AC1: Given no `X-Session-Id` exists client-side, when I load the Home page, then one is generated and persisted locally with no visible login/signup prompt anywhere in the flow.
- AC2: Given I submit a product name, when the request is sent, then a report begins processing without any authentication step.

**US-2 — Progressive report visibility**
As a seller, I want to see agents complete one by one, so I know the system is working and can start reading early results.
- AC1: Given a report is `running`, when I view `/report/{id}`, then completed agents render immediately while pending ones show a distinct in-progress state (§10.2).
- AC2: Given the page is open during processing, when an agent completes, then its section appears within one polling interval (~2-3s) without a manual refresh.

**US-3 — Trustworthy scoring**
As a seller, I want to distinguish "the AI sounds sure" from "this is actually backed by something," so I don't over-trust an unverified claim.
- AC1: Given any agent's output, when I view its card, then Confidence Score and Evidence Score are shown as two separate, separately labeled values.
- AC2: Given an agent had zero real sources (pure LLM reasoning), when I view its Evidence Score, then it is visibly low regardless of how confident the reasoning text sounds.

**US-4 — Manual verification transparency**
As a seller, I want supplier and compliance information clearly marked as unverified, so I don't act on it as fact.
- AC1: Given the Supplier Sourcing or Compliance & Regulatory agent completes, when I view the report, then both are flagged "Manual verification required" and both appear in the Manual Verification Checklist section.

**US-5 — Editable profit economics**
As a seller, I want to plug in my real costs and see profit update instantly, so I can iterate on pricing without waiting on AI.
- AC1: Given I change any cost field, when I stop typing (debounced), then Net Profit/Margin/Breakeven/ROI update within 300ms with no loading spinner tied to an AI call.
- AC2: Given I've changed profit inputs, when I want the overall score to reflect them, then I must explicitly click "Re-run recommendation" — it does not happen automatically.

**US-6 — Cache transparency**
As a seller researching a popular product, I want faster results when it's been analyzed recently, so I'm not stuck waiting for a duplicate AI run.
- AC1: Given a product was analyzed within an agent's cache TTL, when I request analysis again, then that agent's result returns near-instantly and the report visibly indicates it was served from cache with a timestamp.
- AC2: Given a report is fully or partially served from cache, when I view it, then cached data is never presented indistinguishably from a freshly generated result.

**US-7 — Partial resilience**
As a seller, I want a single failed analysis component to not ruin the whole report, so a transient AI hiccup doesn't waste my time.
- AC1: Given one agent errors or times out, when the report finishes, then its status is `partial`, the failing agent shows a friendly error state, and all other agents' data is fully usable.

## 17. Error Handling Strategy

| Internal condition | User-facing code | User-facing message | Logged where |
|---|---|---|---|
| Invalid/empty product name | `VALIDATION_ERROR` | "Please enter a product name." | Not logged (client-side catch expected, backend still validates) |
| Single agent timeout | `AGENT_TIMEOUT` | "We couldn't finish the {agent} analysis in time. The rest of your report is ready." | `agent_logs` (status=timeout) |
| Agent response fails schema validation (after 1 retry) | `AGENT_INVALID_RESPONSE` | Same as above, generic per-agent friendly message | `agent_logs` (status=error) |
| GPT-5.5 API entirely unreachable | `AI_SERVICE_UNAVAILABLE` | "Our AI analysis service is temporarily unavailable. Please try again shortly." | `agent_logs` for every affected agent, single surfaced error on `reports.error_message` |
| Rate limit exceeded | `RATE_LIMITED` | "You've reached the analysis limit for now. Please try again in a bit." | `rate_limit_logs` |
| PDF generation failure | `PDF_GENERATION_FAILED` | "We couldn't generate the PDF right now — your report is still saved and viewable online." | `agent_logs`-equivalent app log |
| Unknown/unexpected exception | `INTERNAL_ERROR` | "Something went wrong on our end. Please try again." | Full exception logged server-side only, never sent to client |

Principles carried forward from v0.1 and reinforced: never a raw stack trace or exception message to the client; every error has a stable `code` for the frontend to key UI off of and a friendly `message`; every error path writes enough server-side context (via `report_id`/`agent_type` correlation) to debug without ever exposing that detail to the user.

---

## 18. Anonymous Usage Model (No Auth)

- **No Supabase Auth, no login/signup pages, no password storage.**
- Frontend generates a UUIDv4 on first load, persists it in `localStorage`, and sends it as `X-Session-Id` on every API call. `lib/session.ts` owns this.
- Backend's `core/session.py` middleware upserts a `sessions` row for any new id it sees (touches `last_seen_at` on every request) — this is bookkeeping, not identity.
- **Report access model:** a report is reachable by anyone with its `report_id` (like an unlisted link), consistent with "no accounts." `recent_searches` and the saved-reports list (`is_saved`) are filtered by `session_id` so a given browser only sees *its own* history on the Home/Reports pages — but this is a convenience index, not a security boundary (there being no accounts to secure against each other in the first place).
- Rate limiting (§9 FR-15) is the actual abuse control, keyed on `session_id` with IP as a backstop against session-id churn.
- Clearing browser storage = starting over with a fresh anonymous identity; this is accepted as expected behavior for an accountless MVP, not a bug.
- This model is designed to upgrade later (§21): if accounts are added post-MVP, `sessions.id` can become the migration seam — a `profiles` table could later reference session ids to "claim" prior anonymous history, without restructuring `reports`/`recent_searches`.

---

## 19. Development Roadmap — 7 Days

| Day | Focus | Deliverables |
|---|---|---|
| **1** | Foundation | Repo scaffold (§2), Supabase schema migration (§3, no RLS), anonymous session middleware, FastAPI skeleton + health check, Next.js skeleton with dark-mode shell + Home UI (non-functional), `ResearchAgent`/`ModuleResponse` interfaces (§4) stubbed, `prompts` table seeded from `/prompts/*_v1.md`, deploy pipelines verified (Vercel + Render/Railway) with a hello-world round trip. |
| **2** | Orchestrator + Cache + first 3 agents | `orchestrator.py` with `asyncio.gather` + partial-failure handling, `cache_service.py` (§7), `prompt_registry.py` (§5), Demand / Competitive Landscape / Pricing agents + rubrics (§6) + `NullConnector` wired in. `POST /reports` + `GET /reports/{id}` working end-to-end for these 3. |
| **3** | Agents 4–7 | Trend & Seasonality, Review Mining, Keyword & Discoverability, Supplier Sourcing (+ `suppliers`/`supplier_leads` writes). All rubrics + evidence scoring (§6) wired for these. |
| **4** | Agents 8–10 + Profit + Decision Synthesis | Logistics & Fulfillment Risk, Compliance & Regulatory, Brand & Positioning; Profit & Unit Economics (pure functions, unit-tested edge cases); Decision Synthesis (`scoring/decision.py` weighted roll-up + narrative LLM call). Full 12-agent pipeline working end-to-end. |
| **5** | Frontend Report Page | Progressive rendering (§10.2/10.3), `AgentCard` generic component driven by the shared schema, Profit Calculator interactive panel (§10.4), Score/Recommendation gauge (Recharts), Manual Verification Checklist, cache-indicator UI. |
| **6** | PDF Export, Rate Limiting, Polish | Server-side PDF generation + Storage upload, rate limiting (session+IP), friendly error states for every case in §17, loading skeletons, responsive + dark-mode audit, `pricing_history`/`trend_history` write-on-fresh-run logic double-checked against cache hits. |
| **7** | Testing, Bugfix, Deploy, Docs | Backend pytest (rubrics determinism tests, evidence formula tests, cache TTL tests, API tests), minimal frontend component tests, full manual run-through + P0/P1 fixes, finalize README/INSTALL/ARCHITECTURE/API/ROADMAP docs, production deploy + smoke test. |

Buffer strategy unchanged in spirit from v0.1: Day 6 (polish) compresses first if a day slips; the 12-agent pipeline (Days 1–4) and deterministic scoring correctness (§6) are non-negotiable — they're the core of what makes this an "Intelligence OS" rather than a report generator, per the review's intent.

---

## 20. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | LLM hallucinates specific facts presented as certain | High | Signals-not-scores design (§6) + mandatory `sources`/Evidence Score + hard-flagged manual verification on Supplier/Compliance (unchanged principle from v0.1 R1, now formalized via schema). |
| R2 | No live marketplace data in MVP (connectors are stubs) — Competitive Landscape/Pricing quality is knowledge-bounded | Medium | Explicit `NullConnector` fallback with honest, visibly lower Evidence Score rather than disguised confidence; connector interface (§8) ready for a real integration later without a rewrite. |
| R3 | 12 agents materially increase 7-day scope vs. v0.1's 6 | High | Shared interface + shared cache/prompt/rubric infrastructure means the *marginal* cost per extra agent is small (§1.4); roadmap (§19) allocates 3 focused days (2–4) specifically to agent build-out, with Day 6 as the compression buffer. |
| R4 | Deterministic rubrics (§6) are subjective in their *design* even though execution is deterministic | Medium | Rubrics are code-reviewed and version-controlled like any other logic; `shared/scoring.md` is the single source of truth so weight/rubric changes are visible, auditable diffs, not silent drift. |
| R5 | Cache incorrectly serves stale data as fresh, or incorrectly pollutes `pricing_history`/`trend_history` on a cache hit | Medium | TTLs tuned per data volatility (§7); explicit rule that history tables are written only on genuine fresh runs, covered by a Day-6 double-check and Day-7 tests. |
| R6 | Anonymous model (no accounts) means a cleared browser = lost history, and a leaked `report_id` is viewable by anyone | Low-Medium | Accepted tradeoff of the review's explicit "remove auth" instruction; documented in §18 as by-design, not a defect; rate limiting (not access control) is the actual abuse guard. |
| R7 | AI API cost overrun without caching/rate limiting working correctly from early on | Medium | Both built in Day 1–2 (`core/rate_limit.py`, `cache_service.py`), not deferred to Day 6 as a bolt-on. |
| R8 | GPT-5.5 API outage takes down the whole report instead of degrading gracefully | Medium | NFR-5: a total outage produces one clear `AI_SERVICE_UNAVAILABLE` failure rather than 11 confusing per-agent errors — explicit orchestrator-level circuit check before fanning out. |
| R9 | Legal/ToS risk if a real connector (§8) is implemented later without review | High if triggered, not applicable to MVP | Interface built now, implementation explicitly deferred and flagged as requiring a ToS/legal pass before any real connector ships (carried forward from v0.1 R3). |

---

## 21. Future Expansion Plan

- **New agents** (13th+): a Meesho-specific agent, an Ad-Cost Estimator agent, a Listing Image/Quality agent, a Shopify agent — each is one class + one prompt row + one rubric function (§4, NFR-10), no orchestrator change.
- **Real connectors**: swap `NullConnector` for a licensed Amazon/Flipkart partner-API connector or a compliant data provider; `connector_configs.is_enabled` flips on; Competitive Landscape/Pricing agents automatically get higher Evidence Scores once `SourceRef.type == "connector"` starts appearing — no schema change needed, this was designed in from day one (§8).
- **Accounts, post-MVP**: `sessions.id` is the seam — a future `profiles`/`organizations` table can let a user "claim" their anonymous history by associating past `session_id`s, rather than restructuring `reports`/`recent_searches`/`recent_searches` (§18).
- **Queue upgrade**: `asyncio.gather` + `BackgroundTasks` swaps for Celery/SQS/Supabase Edge Functions behind the same `orchestrator.py` interface if concurrency outgrows one background task per request (unchanged from v0.1).
- **Full-report caching**: `analysis_cache.agent_type = null` is reserved (§3) for a future whole-report cache tier, once per-agent caching's real hit-rate data justifies it.
- **Fine-tuning / RAG over supplier & compliance sources**: `prompts` table + `/prompts` git history already decouple prompt iteration from code deploys, making a future RAG layer (e.g., over IndiaMART/TradeIndia listings, or GST/BIS regulation text) a service-layer addition, not an architecture change.
- **Billing/plans**: rate limiting is already keyed per-session (§9), which is a natural seam for a future plan-tier limit once accounts exist.
- **Multi-marketplace/multi-country**: `competitors.marketplace` and `connector_configs.marketplace` are already open string fields, not an enum baked into the schema — adding Shopify or a non-Indian market is additive data, not a migration.

---

## 22. Open Questions for Approval

1. **Repo location** (carried from v0.1, still open): standalone project at `c:\dev\ecomos-ai`, sibling to the unrelated `trademind-ai` repo. Confirm before scaffolding begins.
2. **Anonymous data retention window** (NFR-13): proposing 90 days for unsaved anonymous sessions/reports before purge eligibility — confirm the number, or confirm no automatic purge is wanted for the MVP.
3. **GPT-5.5 web/browsing tool access**: several agents (Competitive Landscape, Pricing, Trend & Seasonality) are strongest with live web grounding. Confirm whether your OpenAI plan has this, since its absence means those agents default to `llm_reasoning`-only sourcing with correspondingly lower Evidence Scores across the board.
4. **India-specific compliance depth**: the Compliance & Regulatory agent (§11) flags GST category and BIS/import-certification *risk signals* only — it is explicitly not legal advice. Confirm that framing (a flagging/checklist tool, always manual-verification-required) is the intended scope, not a compliance-determination tool.

## Changelog (v0.1 → v0.2)

- Repositioned product from "AI research tool" to "Ecom Intelligence Operating System" (§0).
- Expanded 6 modules → 12 agents; added Pricing Intelligence, Trend & Seasonality, Keyword & Discoverability, Logistics & Fulfillment Risk (consolidating v0.1's separate Shipping/Packaging/Return/RTO line items), Compliance & Regulatory, Brand & Positioning (§11).
- Added `suppliers`, `supplier_leads`, `competitors`, `pricing_history`, `trend_history`, `prompts`, `agent_logs`, `analysis_cache`, `connector_configs` tables; removed `profiles`/user-scoped RLS (§3).
- Added Evidence Score alongside Confidence Score, with a fully deterministic computation (§6).
- Formalized "LLMs provide reasoning only": agents now emit `signals`, never a raw `sub_score`; all scoring is rubric/arithmetic in Python (§6).
- Added `MarketplaceConnector` interface + `NullConnector` + `connector_configs` registry — no scraping implemented (§8).
- Added DB-backed prompt versioning with full per-report reproducibility (§5).
- Standardized all 12 agents on one `ModuleResponse` schema (§4).
- Added per-agent-type cache TTL strategy, with explicit rules to keep history tables honest on cache hits (§7).
- Removed authentication entirely; introduced anonymous `session_id` model, removed Postgres RLS in favor of backend-only DB access (§18).
- Added Functional Requirements (§14), Non-Functional Requirements (§15), User Stories + Acceptance Criteria (§16), ASCII wireframes (§10), full API contracts with example payloads (§9), and a dedicated Error Handling table (§17).
- Expanded "Future Scalability" into "Future Expansion Plan" with concrete seams tied to specific schema/interface decisions already made (§21).

---

*End of SRS v0.2. No implementation will begin until this is explicitly approved.*
