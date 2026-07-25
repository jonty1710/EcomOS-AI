-- EcomOS AI — Database Schema
-- Source of truth: docs/SRS.md §3 (approved). No sample/seed data in this file.
--
-- Phase 1 (Foundation) note: every table below is created up front so the AI phase
-- (agents, prompts, connectors) is a config/code addition later, never a schema migration.
-- Phase 1 code only actively reads/writes: sessions, products, reports, module_results
-- (deterministic modules only), profit_calculations, recent_searches.
-- prompts / agent_logs / analysis_cache / connector_configs exist but are unused until
-- the AI phase — see backend/app/ai/providers/base_provider.py.
--
-- All access is via the backend's Supabase service role key (no client-side Supabase Auth,
-- no RLS — see SRS §18). All tables use uuid primary keys and created_at timestamps.

create extension if not exists pgcrypto;

-- Anonymous session tracking
create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  product_name text not null,
  normalized_name text not null unique,               -- unique, not just indexed (Phase 4 fix — required
                                                        -- for the backend's upsert(...on_conflict="normalized_name")
                                                        -- to work at all; PostgREST needs a real unique
                                                        -- constraint to match against, an index alone isn't enough)
  category text,
  created_at timestamptz not null default now()
);

-- Research history: one row per analysis run. Never overwritten.
create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete set null,
  product_id uuid references public.products(id) on delete cascade,
  product_name text,                                -- denormalized from products, avoids a join for list/get (Phase 4 fix)
  category text,                                     -- denormalized from products (Phase 4 fix)
  status text not null default 'pending',          -- pending|running|partial|completed|failed|insufficient_data
  research_mode text not null default 'manual',     -- manual|ai (Phase 1 is manual-only)
  overall_score numeric(5,2),
  risk_level text,
  recommendation text,
  research_completeness_pct numeric(5,2),            -- PRS §16 (Phase 4 fix — was missing from Phase 1 schema)
  recommendation_explanation text,                    -- PRS §13 Decision Record (Phase 4 fix)
  manual_verification_checklist jsonb not null default '[]',
  knowledge_pack jsonb,                                -- Phase 3 KnowledgePack snapshot (Phase 4 fix)
  is_saved boolean not null default false,
  served_from_cache boolean not null default false,
  prompt_bundle jsonb,
  error_message text,
  pdf_url text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists idx_reports_session_created on public.reports (session_id, created_at desc);
create index if not exists idx_reports_product_created on public.reports (product_id, created_at desc);

-- Prompt versioning — unused until the AI phase, created now so nothing about the
-- report/module_results shape changes when providers are wired in.
create table if not exists public.prompts (
  id uuid primary key default gen_random_uuid(),
  agent_type text not null,
  version integer not null,
  template text not null,
  change_notes text,
  is_active boolean not null default false,
  created_at timestamptz not null default now(),
  unique (agent_type, version)
);
create unique index if not exists one_active_prompt_per_agent
  on public.prompts (agent_type) where (is_active);

-- Standardized module output — used today only by deterministic modules
-- (profit, logistics_preliminary, category_detection); AI-driven agent_types
-- (demand, competition, pricing, ...) will write here unchanged once Phase 2 ships.
create table if not exists public.module_results (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  agent_type text not null,
  status text not null default 'pending',           -- pending|running|completed|failed|planned_for_ai_phase
  data jsonb not null default '{}',
  signals jsonb not null default '{}',
  reasoning text,
  confidence_score numeric(4,3),
  evidence_score numeric(4,3),
  sub_score numeric(5,2),
  sources jsonb not null default '[]',
  requires_manual_verification boolean not null default false,
  unavailable_reason text,                            -- Phase 4 fix — was missing, needed to reassemble a ModuleSection
  prompt_id uuid references public.prompts(id),
  latency_ms integer,
  token_usage jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  unique (report_id, agent_type)
);

-- Supplier catalog
create table if not exists public.suppliers (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  source text not null,                              -- indiamart|tradeindia|manual|other
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

create table if not exists public.supplier_leads (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  supplier_id uuid references public.suppliers(id) on delete cascade,
  confidence_score numeric(4,3),
  evidence_score numeric(4,3),
  created_at timestamptz not null default now(),
  unique (report_id, supplier_id)
);

-- Competitor catalog — unused until the AI phase (Competitive Landscape agent)
create table if not exists public.competitors (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  name text not null,
  marketplace text not null,
  rating numeric(3,2),
  review_count integer,
  source text not null,                              -- llm_reasoning|web_search|connector|manual
  created_at timestamptz not null default now()
);

-- Pricing history — append-only; Phase 1 may append manual price points only
create table if not exists public.pricing_history (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  competitor_id uuid references public.competitors(id) on delete set null,
  report_id uuid references public.reports(id) on delete set null,
  marketplace text not null,
  price numeric(10,2) not null,
  observed_at timestamptz not null default now(),
  source text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_pricing_history_product_observed on public.pricing_history (product_id, observed_at desc);

-- Trend history — append-only; unused until the AI phase (Trend & Seasonality agent)
create table if not exists public.trend_history (
  id uuid primary key default gen_random_uuid(),
  product_id uuid references public.products(id) on delete cascade,
  report_id uuid references public.reports(id) on delete set null,
  signal_date date not null,
  demand_sub_score numeric(5,2),
  trend_label text,
  source text not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_trend_history_product_date on public.trend_history (product_id, signal_date desc);

-- Profit calculator — deterministic, fully active in Phase 1
create table if not exists public.profit_calculations (
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

create table if not exists public.recent_searches (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete cascade,
  product_name text not null,
  report_id uuid references public.reports(id) on delete cascade,
  searched_at timestamptz not null default now()
);

-- Cache layer — unused until the AI phase (agent-level caching)
create table if not exists public.analysis_cache (
  id uuid primary key default gen_random_uuid(),
  cache_key text not null unique,
  agent_type text,
  payload jsonb not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_analysis_cache_expires on public.analysis_cache (expires_at);

-- Raw execution/audit log — unused until the AI phase
create table if not exists public.agent_logs (
  id uuid primary key default gen_random_uuid(),
  report_id uuid references public.reports(id) on delete cascade,
  agent_type text not null,
  prompt_id uuid references public.prompts(id),
  status text not null,                              -- success|error|timeout|cache_hit
  latency_ms integer,
  error_message text,
  created_at timestamptz not null default now()
);
create index if not exists idx_agent_logs_report on public.agent_logs (report_id);

-- Future marketplace connector registry — config only, disabled by default
create table if not exists public.connector_configs (
  id uuid primary key default gen_random_uuid(),
  marketplace text not null unique,                  -- amazon|flipkart|meesho|shopify
  connector_type text not null default 'none',        -- none|api|partner_feed
  is_enabled boolean not null default false,
  config jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- Rate limiting (anonymous, session + IP scoped)
create table if not exists public.rate_limit_logs (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete cascade,
  ip_address text,
  endpoint text not null,
  window_start timestamptz not null,
  request_count integer not null default 1
);

-- Product Profiles (Phase 2 — Data Collection Engine, backend/app/collection/).
-- The single source of truth handed to the Research Engine (see
-- backend/app/collection/bridge.py). Append-only versioning: editing a profile
-- inserts a NEW row with version = old.version + 1 and previous_version_id
-- pointing at the row it superseded — never an in-place update, same
-- auditability principle as `reports` (every report run is preserved).
create table if not exists public.product_profiles (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.sessions(id) on delete set null,
  product_name text not null,
  source_url text,
  detected_marketplace text,                          -- parsed from source_url domain only, never fetched
  version integer not null default 1,
  previous_version_id uuid references public.product_profiles(id) on delete set null,
  fields jsonb not null default '{}',                  -- {field_key: FieldValue}, see collection/schemas.py
  cost_structure jsonb not null default '{}',
  data_quality jsonb not null default '{}',            -- {completeness_pct, validation_pct, confidence_pct, verification_pending_pct}
  missing_required jsonb not null default '[]',
  missing_optional jsonb not null default '[]',
  ready_for_research boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_product_profiles_session_updated on public.product_profiles (session_id, updated_at desc);
create index if not exists idx_product_profiles_previous_version on public.product_profiles (previous_version_id);

-- Field Audit Events (Phase 4 — Data Source Manager, backend/app/provenance/).
-- Append-only, deliberately small: only the three actions the Data Collection
-- Engine has no concept of natively (rejecting a value, clearing a rejection,
-- requesting a refresh) are written here. Everything else in a field's audit
-- trail (value set, value changed, verified, verification cleared) is DERIVED
-- by diffing product_profiles' own version chain on read — see
-- backend/app/provenance/audit_trail.py. Never updated in place; "current
-- state" for a field (e.g. is it currently rejected) is always the latest
-- relevant row, not a mutated column.
create table if not exists public.field_audit_events (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.product_profiles(id) on delete cascade,
  field_key text not null,
  event_type text not null,                            -- rejected | rejection_cleared | refresh_requested
  note text,
  actor text not null default 'user',
  created_at timestamptz not null default now()
);
create index if not exists idx_field_audit_events_profile on public.field_audit_events (profile_id, created_at);

-- Phase 4 migration block — additive, idempotent, safe to re-run against a
-- database that was created before these columns existed (the `create table`
-- statements above already include them for a fresh install; this block is
-- what actually updates an already-provisioned project).
alter table public.reports add column if not exists product_name text;
alter table public.reports add column if not exists category text;
alter table public.reports add column if not exists research_completeness_pct numeric(5,2);
alter table public.reports add column if not exists recommendation_explanation text;
alter table public.reports add column if not exists manual_verification_checklist jsonb not null default '[]';
alter table public.reports add column if not exists knowledge_pack jsonb;
alter table public.module_results add column if not exists unavailable_reason text;

-- products.normalized_name needs a real UNIQUE constraint, not just an index,
-- for upsert(...on_conflict="normalized_name") to work (discovered live —
-- PostgREST error 42P10 "no unique or exclusion constraint matching the
-- ON CONFLICT specification"). Safe to run even if a handful of test rows
-- already exist, as long as none of them share a normalized_name.
drop index if exists public.idx_products_normalized_name;
alter table public.products drop constraint if exists products_normalized_name_key;
alter table public.products add constraint products_normalized_name_key unique (normalized_name);
