# EcomOS AI — Product Research Specification (PRS v1.0)

**Status:** DRAFT — intelligence design only. No code, no schemas, no APIs, no UI in this document.
**Audience:** Anyone building, tuning, or auditing the research/scoring logic — this is the layer between "an LLM said something" and "the system recommended Launch."
**Relationship to other documents:** The SRS (v0.2) fixes the *architecture* that carries this logic (12 agents, `ModuleResponse` schema, Confidence Score / Evidence Score fields, the signals-not-scores mechanism, the 100-point weight table, prompt versioning). The FBP (v1.0) fixes how a human *experiences* this logic (screens, journeys, the Manual Verification Checklist, lifecycle states). This document does not re-derive either — it defines **how the intelligence layer thinks**: what evidence it trusts, how it turns evidence into numbers, how it knows what it doesn't know, and how it explains itself. Where this document introduces a concept the SRS or FBP left undefined (e.g. an "Insufficient Data" terminal state, a Decision Confidence gate), that is flagged explicitly as a proposed extension, not a silent contradiction.

---

## 1. Research Philosophy

**Why product research must be evidence-driven.** A seller acting on this system's output is committing real capital — FBP's own framing puts the stakes at ₹20,000–₹5,00,000 per decision. An LLM asked "will this product sell?" will produce a fluent, confident-sounding answer whether or not it has any real basis for one — fluency and correctness are unrelated properties of a language model's output. The only defense against a confidently wrong answer is forcing every claim that matters to trace back to something outside the model's own weights: a government filing, a live marketplace listing, a manufacturer quote. Evidence is not a nice-to-have citation appended to an opinion; it is the thing the opinion is *built from*. Section 4 and Section 5 exist to make that non-negotiable.

**Why AI should assist rather than replace human judgement.** Some parts of a product decision are genuinely judgment calls that carry personal and financial accountability the system cannot absorb: whether to trust a specific supplier's word, whether a category's regulatory ambiguity is worth the risk, whether *this* seller's specific capital and risk tolerance fit *this* specific opportunity. The system's job is to compress the research surface area — the dozen open browser tabs FBP describes — into a structured, scored, evidence-tagged brief, so the human's judgment is applied to a well-organized decision instead of a blank page. The system recommends; it never executes (FBP Principle 3). Every mandatory Human Verification step in Section 15 exists specifically to keep a human decision inside the loop before capital moves.

**Why deterministic scoring is mandatory.** If the same evidence could produce a different overall score on a different day because a model provider shipped a new version, or because the LLM happened to phrase its reasoning slightly differently, the score is not a score — it is noise with a number attached. Determinism is what allows two runs against identical signals to always yield an identical `overall_score` (SRS §6, §15 NFR-14), which in turn is what allows a rubric change to be a reviewable, versioned diff instead of an invisible drift. Determinism does not claim the scoring *logic* is objectively correct — see the Final Self-Review's treatment of subjective scoring models — it only claims that whatever the logic is, it is applied consistently and can therefore be audited, criticized, and improved on purpose rather than by accident.

**Why recommendations must be auditable.** A recommendation nobody can explain six months later cannot be learned from, defended to a business partner, or trusted the next time. Every score in this system must be traceable to: the exact evidence gathered, the exact signals an agent derived from that evidence, the exact rubric version that mapped those signals to a number, and the exact weights and thresholds the Decision Engine applied. This is what "explainable by default" (FBP Principle 5) means at the logic layer, not just the UI layer — the explanation has to actually exist before it can be displayed.

---

## 2. Research Pipeline

### 2.1 Stage sequence

```
Product Input
   ↓
Normalization
   ↓
Category Detection
   ↓
Evidence Collection
   ↓
AI Reasoning
   ↓
Evidence Validation
   ↓
Deterministic Scoring
   ↓
Risk Analysis
   ↓
Recommendation
   ↓
Human Verification
   ↓
Final Decision
```

Every stage below is defined by: what it consumes, what it produces, and the condition(s) under which it fails or degrades rather than silently proceeding.

### 2.2 Stage definitions

**1. Product Input**
- *Input:* raw product name text, optional category hint, optional dimensions/weight/target price (per FBP §4.3 New Research screen).
- *Output:* a raw intake record, unvalidated.
- *Failure conditions:* empty input (rejected before entering the pipeline at all); input that is not a plausible product description at all (e.g. gibberish, a sentence, a person's name) — flagged for lightweight rejection rather than silently attempting to research nonsense; input matching an already-recent identical normalized request within a short window — routed to the existing in-flight/recent run rather than duplicating work.

**2. Normalization**
- *Input:* raw intake record.
- *Output:* a normalized product identity — lowercased, trimmed, common synonym/plural collapsed (e.g. "drawer organizers" and "Drawer Organiser" resolve to the same normalized identity) — plus a list of candidate matches against existing Product DNA records (§3) in history.
- *Failure conditions:* the name is ambiguous across unrelated product families (e.g. "Organizer" alone could mean a drawer organizer, a cable organizer, or a planner) — normalization cannot silently pick one; it must either carry the ambiguity forward as multiple candidate categories into Stage 3, or request a category hint before proceeding.

**3. Category Detection**
- *Input:* normalized product identity.
- *Output:* category, sub-category, and a **categorization confidence** (distinct from any downstream Confidence Score) — because every subsequent stage selects evidence sources, rubric variants, and compliance checks based on category, an error here propagates everywhere.
- *Failure conditions:* no category match clears a minimum confidence bar → the product proceeds as "Uncategorized," which is a visible, penalized state (every downstream Evidence Weight for category-dependent sources is capped lower, per §4, because the system cannot be sure it selected the right sources to check in the first place) rather than a silent best-guess.
- *Known limitation (see Final Self-Review):* this stage currently assumes one category per product; genuinely multi-category products (a yoga-mat *bag* is both fitness accessory and bag) are forced into a single bucket.

**4. Evidence Collection**
- *Input:* normalized identity + category.
- *Output:* a raw evidence bundle per research dimension (Demand, Competition, Pricing, Supplier, Compliance, Logistics, Brand, Financial inputs) — each item tagged with source type, per the Evidence Hierarchy (§5).
- *Failure conditions:* zero evidence found for a given dimension is not an error to recover from silently — it is a real, recorded outcome that flows into the provenance system (§17) as `Unknown` and into Research Completeness (§14/§16). The pipeline never invents evidence to fill this gap.

**5. AI Reasoning**
- *Input:* evidence bundle per dimension.
- *Output:* structured qualitative **signals** per dimension (e.g. `search_interest_trend: increasing`) — never a raw numeric score, per the SRS §6 mechanism this document assumes throughout.
- *Failure conditions:* the model's reasoning asserts something the evidence bundle does not support (e.g. claims a specific competitor count with no source behind it) — this is not treated as a valid signal; it is caught at the next stage.

**6. Evidence Validation**
- *Input:* raw signals + the evidence bundle they claim to be derived from.
- *Output:* a validated signal set, with any claim that cannot be traced back to a specific evidence item stripped out and replaced with `Unknown` (§17), plus a computed Evidence Score for the dimension (SRS §6 formula, informed by the finer-grained hierarchy in §5).
- *Failure conditions:* if validation strips out enough of a dimension's signals that too little remains to score meaningfully (§16 minimum evidence bar), that dimension is marked **Unscored — Insufficient Evidence** rather than forced through the rubric with a fabricated middling number.

**7. Deterministic Scoring**
- *Input:* validated signals.
- *Output:* a 0–100 sub-score per scored dimension, via the fixed rubric logic defined per model in §6–§11 (implemented as the SRS's `scoring/rubrics.py`, specified here at the logic level, not the code level).
- *Failure conditions:* none by design — this stage is pure lookup/arithmetic over already-validated inputs and cannot itself fail; any failure upstream (Unscored dimension) is carried forward as a gap, not retried here.

**8. Risk Analysis**
- *Input:* all dimension signals and sub-scores.
- *Output:* a Unified Risk Score and Risk Level (§10), computed independently of — and consulted alongside — the composite opportunity score, because a high-opportunity, high-risk product is a fundamentally different recommendation than a high-opportunity, low-risk one, and averaging the two together would destroy that distinction.
- *Failure conditions:* a risk signal that trips a hard-floor condition (§10, §12) is recorded as such even if the rest of the pipeline completed cleanly.

**9. Recommendation**
- *Input:* weighted dimension sub-scores, Unified Risk Score, Decision Confidence (§14).
- *Output:* a recommendation band (§12) plus the mandatory explanation contract (§13).
- *Failure conditions:* Research Completeness below the hard floor defined in §16 → the pipeline does not produce Launch/Test/Reject at all; it produces **Insufficient Data** (§16), a fifth terminal state distinct from Reject.

**10. Human Verification**
- *Input:* the recommendation + the domain-specific verification triggers (§15).
- *Output:* a checklist of required and advisory verification items attached to the report, gating (softly) the Approved lifecycle transition per FBP §12/§17.
- *Failure conditions:* not applicable — this stage cannot fail, only remain incomplete, which is itself the intended signal.

**11. Final Decision**
- The user's own action. The system's role ends at producing an evidence-backed, explainable, appropriately-hedged recommendation — it does not, and must never, auto-execute a Launch/Reject decision (FBP Principle 3).

---

## 3. Product DNA

Every researched product receives a Product DNA profile — a structured identity that persists across re-research runs (tying into the SRS's `products` table and FBP's per-product History thread) and that every downstream model (§6–§11) reads from and writes to.

| Field | Definition | Why it matters | How it's derived |
|---|---|---|---|
| **Category / Sub-category** | Taxonomy placement from Stage 3 (§2). | Selects which evidence sources, compliance checks, and (eventually) rubric variants apply. | Category Detection stage; evidence-backed where a government/marketplace taxonomy exists, otherwise AI-inferred with reduced confidence. |
| **Problem solved** | The concrete customer pain point the product addresses. | Anchors Demand and Brand reasoning to something falsifiable ("does this actually solve X") rather than a generic feature list. | AI reasoning over category evidence + Review Mining's complaint data when available. |
| **Target customer** | Who buys this, in concrete terms (not a persona essay). | Drives interpretation of purchase-intent signals in the Demand Model (§6). | AI reasoning, cross-checked against Review Mining's reviewer language. |
| **Price band** | Expected retail price range in-market. | Primary input to the Financial Intelligence Model (§9) and Competition Model (§7). | Pricing Intelligence evidence; `Estimated` tag until confirmed. |
| **Weight class** | Light / medium / heavy shipping bucket. | Drives Logistics risk (§10) shipping-cost-tier signal. | User-supplied dimensions if given, else category default (`Assumed` tag). |
| **Material** | Primary construction material(s). | Drives fragility, return-cause, and compliance reasoning. | AI reasoning from category/manufacturer evidence. |
| **Fragility** | Physical fragility class. | Direct input to Logistics Risk Model (§10). | Derived from Material + category default patterns. |
| **Brand potential** | Whether this category supports a defensible, differentiated brand. | Feeds Brand Potential Model (§11) and the long-term-viability half of the Decision Engine. | Mostly AI reasoning — flagged in the Final Self-Review as the weakest-evidenced field in the whole profile. |
| **Repeat purchase potential** | Consumable/replaceable vs. one-time durable purchase. | Feeds Brand Potential Model (§11) — repeat purchase is the single biggest driver of long-term unit economics beyond the first sale. | AI reasoning from category norms (consumables vs. durables). |
| **Bundle potential** | Whether this product naturally pairs with adjacent SKUs. | Feeds cross-sell/upsell scoring in §11. | AI reasoning, cross-checked against Review Mining's "missing features" signal (a requested companion item is a bundle signal). |
| **Seasonality** | Peak/trough demand pattern across the year. | Feeds the Trend & Seasonality dimension (owned jointly with the Demand Model, see §6 note). | Trend & Seasonality evidence; `Estimated` absent a real time series. |
| **Expected lifecycle** | Rough category maturity trajectory (emerging / growth / mature / declining). | Frames whether current Demand Score should be read as a floor or a ceiling. | AI reasoning + Demand Model's growth/decay signals (§6). |
| **Typical return causes** | Known category-level reasons customers return this type of product. | Direct input to Logistics Risk's return-proneness signal (§10). | Review Mining's complaint mining when available; otherwise category default (`Assumed`). |
| **Typical RTO drivers** | Known category-level reasons for Return-to-Origin (COD refusal, size/fit mismatch, damage in transit). | Direct input to Logistics Risk's RTO signal (§10) — the single highest-weighted risk in the Decision Engine (§12). | Category default patterns; rarely directly evidenced pre-launch, almost always `Assumed`. |
| **Competition type** | Fragmented (many small sellers) vs. consolidated (few dominant brands). | Frames how to read the Competition Model's saturation and entry-difficulty signals (§7). | Competitive Landscape evidence. |
| **Customer intent** | Impulse buy vs. considered purchase. | Frames how much weight to put on price sensitivity vs. quality/trust signals. | AI reasoning from Review Mining and category norms. |
| **Market maturity** | How established the category's demand pattern is. | Distinct from Expected lifecycle — this describes evidence *availability*, not just trend direction (a mature market has more reliable historical evidence to reason from). | Derived from evidence density observed during Evidence Collection (§2 Stage 4), not a separate lookup. |
| **Expansion opportunities** | Adjacent categories this product's supplier/brand relationship could unlock. | Long-term-value input to Brand Potential (§11), informs Future SKU Opportunities. | AI reasoning, low evidence backing by nature — explicitly labeled `Assumed`/AI-reasoning-tier. |
| **Future SKU opportunities** | Specific variant/companion products worth researching next. | A forward-looking output, not a scoring input — surfaces to the user as a suggestion, never silently expands scope. | AI reasoning over Bundle potential + Expansion opportunities. |

**Sourcing gap, named explicitly:** several of these fields (Expected lifecycle, Typical return causes, Typical RTO drivers, Expansion opportunities, Future SKU opportunities) have no dedicated Evidence Collection sub-stage of their own in §4 today — they are populated by AI reasoning drawing on evidence gathered for *other* dimensions. This is flagged as Weakness #14 in the Final Self-Review rather than glossed over here.

---

## 4. Evidence Specification

Every metric this system scores must satisfy the same eight-attribute contract before it is allowed to influence a score. This is the fixed template — current metrics are specified against it below as worked examples; any future metric (including anything added under §18) must be specified the same way before it can be wired into a rubric.

**The eight attributes:** Evidence sources · Reliability score · Evidence weight · Update frequency · Manual verification requirement · Fallback behaviour · Conflict resolution · Missing evidence handling.

### 4.1 Worked example — Demand: Search-Interest Trend

- **Evidence sources (ranked):** search-behavior data (e.g. Google Trends-style signal) → marketplace review-velocity trend → industry report → AI reasoning.
- **Reliability score:** 0.5 (search-behavior) as the ceiling in MVP — no single source here reaches "government"-tier reliability.
- **Evidence weight in Demand Model:** 30% (§6).
- **Update frequency:** fast-moving; cache TTL 24–72h (matches SRS §7 Demand/Trend TTLs).
- **Manual verification requirement:** none — directional signal, not a fact claim (matches FBP §7 Demand Intelligence).
- **Fallback behaviour:** reasoning-only, with Evidence Score capped low and visibly so — never disguised as equally strong (SRS §8 connector-fallback principle applied at the domain level).
- **Conflict resolution:** if search-behavior and review-velocity trend disagree in direction, surfaced as an explicit Evidence Conflict (§10) rather than averaged.
- **Missing evidence handling:** zero sources found → `search_interest_trend` signal tagged `Unknown` (§17), Demand sub-score computed from remaining sub-components only, dimension flagged for reduced Research Completeness (§14).

### 4.2 Worked example — Pricing: Competitor Price Band

- **Evidence sources (ranked):** marketplace live listing data (connector) → manufacturer list price → supplier quote → AI reasoning.
- **Reliability score:** 0.85 (marketplace connector) down to 0.3 (reasoning-only).
- **Evidence weight in Financial Intelligence Model:** primary input to default cost/price seeding (§9).
- **Update frequency:** fast-moving; 24h TTL.
- **Manual verification requirement:** always advisory-tier (§15) — pricing is treated as an estimate until confirmed against a live listing.
- **Fallback behaviour:** `NullConnector` unavailable (MVP default, SRS §8) → reasoning-only, Evidence Score honestly lowered.
- **Conflict resolution:** disagreement with Competitive Landscape's implied price range is treated as corroboration when it *agrees* (SRS §6 corroboration boost) and as a flagged conflict when it doesn't.
- **Missing evidence handling:** no price data at all → Financial Model cannot seed defaults; user must supply a selling price manually before Profit & Unit Economics can compute anything beyond a placeholder.

### 4.3 Worked example — Review Mining: Complaint / Sentiment Signal

- **Evidence sources (ranked):** verified marketplace reviews (connector) → aggregated review-summary industry report → forum/community discussion → AI reasoning.
- **Reliability score:** 0.55 (customer reviews, even at connector tier — reviews are real but self-selected and gameable) down to 0.25 (forum).
- **Evidence weight:** feeds Review Mining's own sub-score directly, and feeds Brand Potential's differentiation-opportunity signal (§11) indirectly.
- **Update frequency:** medium; 72h TTL.
- **Manual verification requirement:** none.
- **Fallback behaviour:** reasoning-only if no review connector/search evidence found.
- **Conflict resolution:** not typically applicable (single-direction evidence), but a stark mismatch between "top praises" and "top complaints" pointing at the same feature is itself a flagged ambiguity, not silently resolved.
- **Missing evidence handling:** brand-new category with no existing competing listings to mine → `Unknown`, and Brand Potential's differentiation-opportunity signal loses one of its two main inputs (the other being Expansion opportunities in Product DNA).

### 4.4 Worked example — Supplier: MOQ & Price Spread

- **Evidence sources (ranked):** manufacturer direct quote → verified supplier platform listing (IndiaMART/TradeIndia) → unverified supplier listing → AI reasoning.
- **Reliability score:** 0.9 (manufacturer) down to 0.6 (supplier platform, unverified) down to 0.3 (reasoning).
- **Evidence weight:** primary input to Supplier Intelligence Model (§8).
- **Update frequency:** slow-moving; 14-day TTL (matches SRS §7).
- **Manual verification requirement:** **always required, unconditionally** — no confidence or evidence level ever suppresses this flag (matches SRS §11, FBP §7 item 7).
- **Fallback behaviour:** no fallback lowers the manual-verification requirement; only the Evidence Score and confidence vary.
- **Conflict resolution:** wide MOQ/price spread across multiple supplier leads is not "resolved" — it is itself a signal (`price_spread_across_suppliers`) fed directly into the rubric.
- **Missing evidence handling:** zero supplier leads found → Supplier sub-score is `Unscored — Insufficient Evidence` (§2.2 Stage 6), and this alone is severe enough to be one of the Manual Review triggers in §16.

### 4.5 Worked example — Compliance: GST Category & Certification Flag

- **Evidence sources (ranked):** government registry/portal → industry compliance report → manufacturer certification claim → AI reasoning.
- **Reliability score:** 1.0 (government) down to 0.3 (reasoning).
- **Evidence weight:** direct input to the Compliance sub-score and to hard-reject rules (§12).
- **Update frequency:** slow-moving; 14-day TTL, but see Final Self-Review Weakness #24 on staleness of `Assumed`-tag defaults.
- **Manual verification requirement:** **always required, unconditionally** — explicitly framed as a flagging tool, never a compliance determination (matches SRS §11, FBP §7 item 9).
- **Fallback behaviour:** no government-tier source available in MVP by default → reasoning-only, `Assumed` tag, always paired with the mandatory verification flag so a low-confidence flag is never mistaken for "cleared."
- **Conflict resolution:** a certification claim from a manufacturer that a government source would contradict always yields to the government source, per Evidence Hierarchy rank (§5).
- **Missing evidence handling:** no evidence at all for a category's compliance requirements → `Unknown`, and the Compliance sub-score cannot be computed as "low risk" by default — absence of evidence of risk is never treated as evidence of absence of risk (§17).

### 4.6 Worked example — Risk: Trademark / Brand-Name Conflict

- **Evidence sources (ranked):** trademark registry search (future connector) → AI reasoning pattern-match against known brand names → none.
- **Reliability score:** 1.0 (registry, not available in MVP) down to 0.3 (reasoning pattern-match, the MVP default).
- **Evidence weight:** feeds the Unified Risk Score (§10) and is one of the few signals with hard-floor authority in the Decision Engine (§12).
- **Update frequency:** effectively static per product name; re-checked only on re-research.
- **Manual verification requirement:** **always required, unconditionally** (matches FBP §12 checklist item "Trademark / brand-name clearance checked").
- **Fallback behaviour:** MVP has no registry connector, so this signal is reasoning-only by default — which is precisely why a *confirmed* collision can never be asserted from MVP evidence alone (see §12 hard-reject nuance and Final Self-Review Weakness #5).
- **Conflict resolution:** not applicable (single-direction flag).
- **Missing evidence handling:** no obvious collision detected ≠ cleared — always surfaces as "requires manual trademark search," never as a green light.

---

## 5. Evidence Hierarchy

Evidence is never treated as equal. The ranking below governs conflict resolution (evidence closer to the top always wins over evidence below it) and is one of the two inputs to a metric's Evidence Score, alongside source count and cross-agent corroboration (SRS §6 formula).

| Rank | Source type | Reliability score | Why |
|---|---|---|---|
| 1 | **Government** (GST portal, BIS/import registries, customs notifications) | 1.0 | Authoritative and legally binding; cannot be gamed by a seller or a competitor. |
| 2 | **Manufacturer** (spec sheets, direct factory quotes, certifications) | 0.9 | Primary-source and specific, though self-interested — a manufacturer can overstate quality but rarely fabricates hard specs it would be caught on. |
| 3 | **Marketplace live listing data** (real prices, ratings, review counts, via connector) | 0.85 | Reflects actual current market behavior, not a claim about it — but only for currently-listed sellers (survivorship bias: failed listings are invisible). |
| 4 | **Industry report** (Statista-style, trade-association data) | 0.75 | Aggregated and methodologically vetted, but often broad-category and can lag the current moment. |
| 5 | **Supplier** (IndiaMART/TradeIndia-style listings, non-manufacturer) | 0.6 | Real leads, but self-reported and sales-motivated — MOQ and price quotes are opening offers, not settled facts. |
| 6 | **Customer reviews** (existing reviews on competing listings) | 0.55 | Genuine user voice, but subject to fake-review inflation and selection bias (only people motivated enough to write one are represented). |
| 7 | **Google Trends / search behavior** | 0.5 | Directional and essentially free to obtain, but relative (indexed, not absolute) and confirms search interest, not purchase intent. |
| 8 | **AI reasoning** (model's own trained knowledge, zero external source) | 0.3 | Useful for synthesis and pattern-matching across everything above, but independently unverifiable and the primary hallucination surface. |
| 9 | **Blogs** | 0.25 | Frequently SEO-motivated, authorship rarely verifiable, factual accuracy inconsistent. |
| 10 | **Forums** (Reddit, Quora, seller communities) | 0.25 | Genuine practitioner voice, but small, self-selected samples and heavy anecdote bias. |
| 11 | **Social media** | 0.2 | Highest noise-to-signal ratio of any source considered; bot/engagement inflation is common and hard to detect. |

**Mapping to the SRS's engineering-layer source types:** the SRS's `SourceRef.type` enum (`connector`, `manual`, `web_search`, `llm_reasoning`, `deterministic`) is a coarser bucket that this table resolves into at the research layer: `connector` ≈ Government/Marketplace-live; `manual` ≈ Manufacturer/verified-Supplier; `web_search` ≈ Industry report, Customer reviews, Trends, Blogs, Forums, Social (all bucketed together for the engineering weight formula, but differentiated here for research-level scoring nuance and conflict resolution); `llm_reasoning` ≈ AI reasoning alone. This document's finer ranking is what a `web_search` result is actually *for* before it collapses into the coarser engineering bucket.

**Never treat all evidence equally** — this is the operative rule every model in §6–§11 inherits: two sources agreeing is not automatically stronger than one source disagreeing, if the one source outranks the two.

---

## 6. Demand Model

**Scope note:** the Demand Model below describes the full domain logic of "is there real demand for this." Operationally, per the SRS's 12-agent split, this logic is implemented across **two** agents — Demand Intelligence (structural/baseline demand, weight 15) and Trend & Seasonality (time-pattern and momentum, weight 7) — whose sub-scores are combined only at the Decision Engine level (§12), not merged into one number here. This keeps a fast-moving seasonal spike from diluting (or inflating) the read on structural, year-round demand.

### 6.1 Indicators

| Indicator | Definition | Evidence tier used (§5) |
|---|---|---|
| Search-interest trend | Direction and slope of category search volume | Search behavior, Marketplace, Industry report |
| Category growth rate | Category-level demand trajectory over recent periods | Industry report, AI reasoning |
| Review velocity (competitors) | Rate of new reviews accumulating on existing competing listings — a proxy for sales velocity | Marketplace, Customer reviews |
| Purchase intent signals | Language in reviews/search queries indicating active buying intent vs. idle browsing (e.g. "where to buy," "best price") | Customer reviews, Search behavior |
| Demand decay | Evidence the category is shrinking (declining review velocity, declining search interest over trailing periods) | Search behavior, Marketplace |
| Demand growth | Evidence the category is emerging (rising review velocity, new-entrant density increasing) | Search behavior, Marketplace |
| Seasonality pattern | Peak/trough shape across the year (owned by Trend & Seasonality) | Search behavior, Industry report |
| Demand confidence | Model's self-reported certainty in the above (SRS Confidence Score mechanism) | N/A — computed, not sourced |
| Demand evidence | Deterministic Evidence Score for this dimension (SRS §6 formula) | N/A — computed, not sourced |

### 6.2 Demand sub-score composition

| Component | Weight within Demand dimension | Rationale |
|---|---|---|
| Search-interest trend | 30% | The single most directly observable proxy for real, current buyer interest. |
| Category growth/decay trajectory | 20% | Distinguishes a temporarily-quiet-but-growing category from a permanently-shrinking one — direction matters more than the current snapshot. |
| Review velocity across competitors | 20% | The closest available proxy to actual sales velocity without live sales data. |
| Purchase intent signal strength | 15% | Filters out categories with high curiosity but low buying intent (a common false-positive pattern for "trending" products). |
| Seasonality-adjusted context | 15% | A category scored during its trough should not be penalized identically to one that is structurally weak year-round — this component is a contextual adjustment, not a raw seasonality score (which lives in the separate Trend & Seasonality agent). |

**A structural tension, named rather than hidden:** the categories where correctly spotting demand *growth* matters most — genuinely new, emerging categories — are exactly the categories with the least available evidence (no historical review velocity, thin search history). The model does not pretend to solve this; it lets the Evidence Score fall honestly for these cases (§4.1), which means an emerging-category recommendation should always carry a visibly lower Decision Confidence (§14) than a mature-category one of the same nominal score. This is a feature of honest scoring, not a bug to engineer away.

---

## 7. Competition Model

**Scope note:** implemented jointly by the Competitive Landscape (weight 10) and Keyword & Discoverability (weight 5) agents; this section describes the combined domain logic those two sub-scores draw on.

| Indicator | Definition | Feeds |
|---|---|---|
| Brand dominance | Degree to which a small number of brands control category visibility/sales | `brand_dominance_level` signal |
| Review landscape | Distribution of review counts/ratings across existing listings — concentrated (few listings own all the reviews) vs. fragmented | `seller_density` signal |
| Price concentration | How tightly competitor prices cluster vs. spread widely | Cross-feeds Pricing Intelligence |
| Listing quality | Observable quality bar of existing competing listings (images, descriptions, review response) — a low bar signals differentiation headroom | `differentiation_headroom` signal |
| Market saturation | Raw count/density of active competing sellers | `seller_density` signal |
| Entry difficulty | Composite read on how hard it would be to gain initial visibility (keyword competitiveness + brand dominance + review-count floor to compete against) | Keyword & Discoverability's `search_term_competitiveness` |
| Differentiation opportunity | Where existing listings fall short (ties to Review Mining's missing-features signal, §4.3) | Feeds Brand Potential Model (§11) |

**Competition score composition:** Brand dominance (25%) + Market saturation (25%) + Entry difficulty/Keyword competitiveness (25%) + Differentiation opportunity (25%) — deliberately equal-weighted, unlike the Demand Model, because none of these four dimensions reliably dominates the others across categories; a category can be highly saturated but still have real differentiation headroom (crowded but low quality), or lightly saturated but nearly impossible to enter (crowded shelf-space/logistics gatekeeping). Equal weighting avoids privileging one failure mode over another until category-specific calibration data exists to justify otherwise (§18).

**Confidence and Evidence:** standard pattern (§14) — Confidence is the model's self-report; Evidence is materially higher once a real marketplace connector (SRS §8) supplies actual seller/review counts instead of reasoning-only estimates, and this document's scoring logic does not change when that happens — only the Evidence Score ceiling rises.

---

## 8. Supplier Intelligence Model

| Indicator | Definition | Notes |
|---|---|---|
| Manufacturer vs. wholesaler | Whether the lead is a primary producer or an intermediary | Manufacturer leads carry higher reliability (§5) and typically better pricing/MOQ terms. |
| MOQ (Minimum Order Quantity) | Smallest order size the supplier will accept | Direct input to initial capital risk. |
| Lead time | Time from order to delivery | Feeds Logistics/cash-flow risk (§10). |
| Pricing stability | Whether quoted pricing holds across order sizes/time, or fluctuates | Inherently hard to evidence from a single research pass — flagged as Weakness #22 in the Final Self-Review. |
| Communication quality | Responsiveness and clarity in supplier interactions | Same limitation as above — largely unmeasurable pre-contact. |
| Sample availability | Whether the supplier offers samples before bulk commitment | A hard prerequisite for the mandatory Sample verification step (§15). |
| Quality consistency | Track record of consistent output quality across batches | Almost entirely unevidenced pre-contact in MVP; populated post-verification via the future feedback loop (§18). |
| Risk indicators | Red flags: unusually low pricing vs. category norm, no verifiable business registration, refusal to provide samples | Directly informs `verification_status` progression (SRS §3 `suppliers` table). |

**Supplier score composition:** Lead count found (25%) + MOQ/price-spread reasonableness vs. category norm (25%) + Sample availability (25%) + Absence of risk indicators (25%). Because Supplier Sourcing's output is **always** manual-verification-required regardless of this score (§4.4, SRS §11), the Supplier sub-score functions as a *readiness* signal — "how promising does this look before you pick up the phone" — never as a substitute for the phone call itself.

**Manual verification checklist (evaluation criteria, distinct from the FBP workflow checklist in §15):**
- Business registration/GST number independently checkable, not just claimed.
- At least one sample obtainable before any bulk commitment.
- Pricing quote is consistent across at least two independent contacts with the same supplier (if feasible) or cross-checked against the category price-spread signal.
- No unresolved risk indicator (§ above) present without an explicit note.

---

## 9. Financial Intelligence Model

**Scope note:** the SRS's Profit & Unit Economics agent (weight 11) is deterministic arithmetic over user-entered costs — this section defines the *intelligence* layered on top of that arithmetic: how defaults are estimated when the user hasn't supplied real costs yet, and how the model reasons about uncertainty rather than producing a single point estimate.

### 9.1 Cost components

Product cost · Marketplace fees · Shipping · Packaging · Returns · RTO · Ads · Storage · GST. Each is either user-supplied (authoritative, `Verified`-tier once entered) or defaulted from category norms (`Assumed`-tier, always visibly labeled as such per §17 — never presented as if it were a real cost).

### 9.2 Default estimation logic

When the user has not yet entered real costs, defaults are seeded in this priority order: (1) Pricing Intelligence's price band → selling price default; (2) category-level cost-ratio norms (e.g. "packaging typically runs 2–4% of selling price for this fragility class") → packaging/shipping defaults; (3) Logistics Risk's return-proneness/RTO signals → return-cost/RTO-cost defaults; (4) fixed platform-published rates (marketplace fee %, current GST %) where those are genuinely known constants rather than estimates. Every defaulted field is tagged `Estimated` or `Assumed` per §17 and must be visually distinguishable from a user-entered value (an FBP/UI concern, but the tagging that enables it originates here).

### 9.3 Outputs

Net profit · Margin % · ROI % · Break-even unit count — computed identically whether inputs are real or defaulted, but the report's **Financial Confidence** (a component of Decision Confidence, §14) is materially lower when defaults dominate the inputs.

### 9.4 Sensitivity analysis

Rather than a single point estimate, the Financial Model produces three scenarios:

| Scenario | Construction |
|---|---|
| **Best case** | Selling price at the top of the observed price band, return/RTO costs at the category's lower observed bound, ad cost at an efficient-acquisition assumption. |
| **Expected case** | The default/entered values as-is — the report's headline numbers. |
| **Worst case** | Selling price at the bottom of the observed band (or a defensive discount), return/RTO costs at the category's upper observed bound, ad cost at an inefficient-acquisition assumption. |

**Known limitation (see Final Self-Review):** the three scenarios currently vary each cost input independently. In reality, a high-RTO category typically also correlates with higher acquisition cost per successful sale (you pay to acquire a customer whose order then bounces) — the model does not yet capture this correlation, and Worst Case may understate true downside risk until real outcome data exists to estimate it (Weakness #7, Future Improvement #24).

**Decision Engine input:** the Decision Engine (§12) reads the **Worst Case** net profit, not just the Expected Case, when evaluating financial hard-reject conditions — a product that is only profitable in its best-case scenario is treated materially differently from one that is profitable even in its worst case.

---

## 10. Risk Intelligence Model

### 10.1 Risk catalog

| Risk | Owning source | Evidence basis |
|---|---|---|
| Return risk | Logistics & Fulfillment Risk agent | Typical return causes (Product DNA), Review Mining complaints |
| RTO risk | Logistics & Fulfillment Risk agent | Typical RTO drivers (Product DNA), category norms |
| Competition risk | Competition Model (§7) | Saturation, entry difficulty |
| Pricing risk | Pricing Intelligence + Financial Model | Price volatility/spread, undercut exposure |
| Supplier risk | Supplier Intelligence Model (§8) | Risk indicators, verification status |
| Policy risk | Marketplace policy category restrictions | AI reasoning, cross-checked at manual verification (§15) |
| Trademark risk | §4.6 worked example | AI reasoning pattern-match (MVP), registry connector (future) |
| Patent risk | Same pattern as Trademark | AI reasoning pattern-match, always manual-verification-flagged |
| Inventory risk | Financial Model + Demand Model | Break-even sensitivity, demand volatility |
| Cash-flow risk | Supplier lead time + MOQ + Financial Model | Lead time, capital tied up pre-sale |
| Counterfeit risk | Compliance & Brand reasoning | Category susceptibility patterns, AI reasoning |
| Operational risk | Cross-cutting (fragility + supplier + logistics) | Composite of the above |

Compliance & Regulatory risk (GST/BIS/import flags, §4.5) is tracked separately as its own always-manual-verified dimension rather than folded into this catalog, because it carries hard-reject authority (§12) distinct from the weighted risks below.

### 10.2 Unified Risk Score

The catalog above is combined into a single **Unified Risk Score** (0–100, higher = riskier) as a weighted sum: Return + RTO (30% combined — the single largest bucket, reflecting Logistics' dominant weight in the overall Decision Engine, §12) · Supplier + Cash-flow (20%) · Competition + Pricing (20%) · Trademark + Patent + Counterfeit (15%) · Policy + Operational + Inventory (15%).

**Hard floor rules (override the weighted average):** a weighted sum can mathematically average away a single catastrophic risk. To prevent that, specific risk types carry independent floor authority regardless of their weighted contribution:
- A **confirmed** (not merely suspected) Trademark or Patent conflict floors the Risk Score at "Critical" outright.
- A Compliance flag indicating a banned/restricted import category floors the Risk Score at "Critical" outright and triggers the hard-reject path in §12.
- RTO risk alone rated "Severe" (independent of the composite) floors the Risk Score at "High" even if every other risk is low.

**Known limitation:** floor rules are currently enumerated for only three of the twelve catalog entries. The remaining risk types rely on the weighted average alone, meaning a single severe-but-not-floored risk (e.g. catastrophic Cash-flow risk from an unusually long supplier lead time) could still be diluted by low scores elsewhere. This is named explicitly as Weakness #9 and Future Improvement #20 rather than left implicit.

---

## 11. Brand Potential Model

| Signal | Definition | Product DNA link |
|---|---|---|
| Repeat purchase | Likelihood of the same customer buying again | Product DNA "Repeat purchase potential" |
| Cross-sell | Likelihood this customer would buy an adjacent product from the same brand | Product DNA "Bundle potential" |
| Upsell | Room for a premium variant of the same product | Derived from Price band + Competition listing-quality gap |
| SKU expansion | Room to grow a full product line from this starting SKU | Product DNA "Future SKU opportunities" |
| Brand story | Whether the product supports a genuine narrative beyond commodity functionality | AI reasoning — the most subjective signal in this model |
| Category depth | How many genuinely differentiated sub-niches exist within the category | Competition Model's differentiation-opportunity signal (§7) |
| Customer loyalty potential | Whether category purchase behavior favors habitual brand loyalty vs. price-shopping every time | AI reasoning + Customer intent (Product DNA) |
| Long-term defensibility | Whether an early mover in this category can sustain an advantage, or whether it commoditizes quickly | Composite of the above |

**Brand Potential sub-score composition:** Repeat purchase potential (25%) + Cross-sell/Upsell/SKU expansion, combined (25%) + Category depth / differentiation headroom (25%) + Long-term defensibility (25%).

**Named explicitly, not buried:** this is the most evidence-poor model in the whole specification. Almost every signal above is AI-reasoning-tier (§5, reliability 0.3) with no realistic MVP path to a higher-reliability source — there is no government registry for "does this product support a good brand story." The Evidence Score for this dimension should be expected to run structurally lower than every other dimension's, and the Decision Engine (§12) must not let a high Brand sub-score compensate for a low Brand Evidence Score in a way that looks equivalent to, say, a high Compliance sub-score backed by real government data. See the Final Self-Review's dedicated treatment of subjective scoring models.

---

## 12. Decision Engine

### 12.1 Principle

Per the SRS's explicit mechanism (§6 there): **no agent is ever asked to output the number that drives the Launch/Reject decision.** This section is the domain-level specification of *how* the eleven scored dimensions' sub-scores become one recommendation — the arithmetic itself is plain, reviewable logic (SRS `scoring/decision.py`), never model output.

### 12.2 Weight table and rationale

Reusing the SRS §6 weight table as the fixed source of truth (unchanged here — this document adds *why*, not new numbers):

| Dimension | Weight | Rationale |
|---|---|---|
| Demand Intelligence | 15 | Highest weight — no amount of good economics or low risk matters if nobody wants the product. |
| Logistics & Fulfillment Risk | 12 | Second-highest — RTO and return costs are the most common silent margin killer in Indian ecommerce, and the least visible one until it's too late (§10). |
| Profit & Unit Economics | 11 | High weight, but deterministic and directly falsifiable — the one dimension a seller can independently verify with their own numbers. |
| Competitive Landscape | 10 | A saturated, dominated category can neutralize otherwise-strong demand. |
| Pricing Intelligence | 8 | Meaningful, but partially redundant with Competitive Landscape's price-concentration signal — not double-weighted. |
| Review Mining | 8 | Direct signal of unmet need in-category (differentiation headroom). |
| Supplier Sourcing | 8 | Sourcing readiness gates whether the opportunity is actually executable, but is always manual-verification-required regardless of score (§8), so its *numeric* weight is capped relative to its practical importance. |
| Compliance & Regulatory | 8 | Meaningful weight, but its real teeth are in the hard-reject rules below, not the weighted average — a Compliance sub-score alone should never look "safe" without the manual-verification flag. |
| Brand & Positioning | 8 | Long-term value signal, deliberately not over-weighted given how evidence-poor this dimension is (§11). |
| Trend & Seasonality | 7 | Time-pattern context for Demand, not a standalone opportunity signal on its own. |
| Keyword & Discoverability | 5 | Lowest weight — addressable post-launch via marketing spend, the least decision-critical dimension at the research stage. |
| **Total** | **100** | |

Decision Synthesis itself (the 12th agent) is not separately weighted — it aggregates the above and produces the narrative (§13), never the number.

### 12.3 Evidence-weighted scoring adjustment

A dimension's raw sub-score is not accepted into the weighted total at full strength if its Evidence Score is very low — a confident-looking 85 built on reasoning-only evidence should not carry identical weight to an 85 built on connector-grade evidence. Each dimension's contribution to the composite is discounted by a small penalty when its Evidence Score falls below 0.3 (the reasoning-only ceiling, §5), proportional to the shortfall — never zeroing the dimension out entirely (a low-evidence signal is still worth something), but preventing a weak-evidence dimension from silently carrying the same authority as a well-evidenced one. This closes a gap the SRS left open: Evidence Score existed as a *displayed* metric there, but its effect on the actual decision arithmetic is specified here for the first time.

### 12.4 Bands

Unchanged from the SRS: **90+ Launch · 80–89 Strong Candidate · 70–79 Test First · <70 Reject.**

### 12.5 Hard-reject rules (override the composite score entirely)

- Compliance flag confirms a banned/restricted import category → **Reject**, regardless of composite score.
- Trademark or Patent conflict is *confirmed* (not merely a reasoning-tier suspicion — see §4.6, no MVP registry connector exists to actually confirm one) → **Reject**.
- Financial Model's **Worst Case** scenario (§9.4) shows negative net profit even under an optimistic ad-spend assumption → composite score is capped at **Test First**, never Launch or Strong Candidate, regardless of Expected Case profitability.
- Unified Risk Score (§10.2) floored at "Critical" by any of its floor rules → composite capped at **Reject**.

### 12.6 Manual-review trigger rules (do not override the score, but force a "Needs Review" recommendation state)

- Research Completeness (§14) below 70% → forced **Needs Review**, regardless of composite score. This pins the exact threshold the FBP left as an undefined "ambiguous middle band" (FBP §17.2, self-critique Weakness #9).
- Supplier Sourcing returns `Unscored — Insufficient Evidence` (§4.4) → forced **Needs Review** — sourcing readiness is too load-bearing to let a missing signal pass silently through the weighted average.
- Two or more dimensions report an unresolved Evidence Conflict (§4, §10) with each other → forced **Needs Review**.

### 12.7 Decision Confidence gating

Even when the composite score and hard-reject/manual-review rules produce a clean band, the final recommendation label is additionally gated by **Decision Confidence** (§14): if the composite qualifies for Launch (≥90) but Decision Confidence falls below its own threshold (§14), the displayed recommendation is capped down one band and explicitly flagged as confidence-limited (e.g. *"Strong Candidate — confidence-limited from Launch; evidence coverage is below the bar this system requires for its highest-conviction recommendation"*). This operationalizes the rule that a shaky 90 must never look identical to a rock-solid 90.

---

## 13. Explainability

Every recommendation this system produces must ship with a fixed explanation contract — the **Decision Record** — before it is considered complete. This formalizes the content Decision Synthesis's narrative (SRS §11, FBP §7 item 12) is required to cover; it is a specification of *what must be answered*, not the prose itself.

| Required answer | Source |
|---|---|
| **Why this recommendation?** | The dominant 2–3 weighted contributors to the composite score (§12.2), named specifically, not just "the score was high." |
| **Which evidence?** | The highest-reliability-tier source (§5) actually used for each dominant contributor — not an exhaustive source dump, the *load-bearing* ones. |
| **Which risks?** | The Unified Risk Score's top contributors (§10), and explicitly whether any hard-floor or hard-reject rule was close to triggering even if it didn't. |
| **Which assumptions?** | Every `Assumed`-tier field (§17) that materially influenced the recommendation — not a blanket disclaimer, the specific assumed values. |
| **Which unknowns?** | Every `Unknown`-tier field that a well-evidenced version of this report would have wanted to fill — this is the same content as the "evidence gap" concept in the Final Self-Review's missing opportunities. |
| **What should be manually verified?** | The full checklist from §15, filtered to only the Critical-tier items for this specific report (not the generic full list). |

A recommendation that cannot answer all six is not permitted to reach the "completed" state described in the SRS's `reports.status` — it remains `partial`, with the specific missing answer identified as the reason.

---

## 14. Confidence System

Four distinct numbers, computed four distinct ways, answering four distinct questions — never conflated, never displayed as if interchangeable.

| Score | Question it answers | Computed from | Level | Effect on decision |
|---|---|---|---|---|
| **Confidence Score** | "How sure does the model say it is?" | LLM self-report, discounted on fallback (SRS §6) | Per-agent | Displayed only; does not directly gate the recommendation. |
| **Evidence Score** | "How much can we actually verify this claim?" | Deterministic source-mix formula (SRS §6, informed by §5's finer hierarchy) | Per-agent | Feeds the evidence-weighted scoring adjustment (§12.3). |
| **Decision Confidence** | "How much should the user trust the *overall* recommendation, not just one section?" | Weighted average of all eleven dimensions' Evidence Scores, minus a penalty for each unresolved cross-agent Evidence Conflict (§10), minus a penalty for each failed/unscored agent | Report-level | Gates band-capping (§12.7); the single number the report's headline recommendation is qualified by. |
| **Research Completeness** | "What fraction of the intended evidence surface did we actually gather?" | Count of populated required Product DNA (§3) + metric fields (§4) ÷ total expected for the detected category — independent of evidence *quality*, purely evidence *existence* | Report-level | Forces "Needs Review" below 70% (§12.6); forces "Insufficient Data" below the hard floor (§16). |

**Why four, not two:** Confidence Score alone can be gamed by an overconfident model with nothing behind it (guarded against by Evidence Score). Evidence Score alone, per-agent, can hide the fact that one report has excellent evidence in ten dimensions and none in the eleventh most-critical one (guarded against by Decision Confidence, which is sensitive to the *distribution*, not just the average). And even a report with strong average evidence per dimension can still be built on a thin overall evidence-gathering pass if entire Product DNA fields were never even attempted (guarded against by Research Completeness, which measures coverage, not quality, as a distinct failure mode from low-quality evidence).

---

## 15. Human Verification

| Domain | Trigger | Verifier | Evidence required to mark verified | Tier | Consequence if skipped |
|---|---|---|---|---|---|
| Supplier contacted | Always, when Supplier Sourcing returns any lead | User | Direct contact confirmation | **Critical** | Soft-gates Approved (FBP §12). |
| Sample ordered / received | Always, before Testing/Approved | User | Physical sample received & inspected | **Critical** | Soft-gates Approved. |
| Packaging tested | When Logistics fragility signal is Medium or High | User | Packaging test completed | Advisory | Tracked only, never gates a transition. |
| Pricing confirmed | Always (pricing is `Estimated` by default, §9) | User | Confirmed against a live listing | Advisory | Tracked only. |
| Trademark / brand-name clearance | Always, for any new brand entry | User | Independent trademark search completed | **Critical, conditionally elevated** | Soft-gates Approved always; if a Compliance or reasoning-tier collision flag is present, treated as equivalent-severity to the two base Critical items above. |
| Marketplace policy reviewed | When a Compliance flag exists for the category | User | Category restriction policy reviewed | **Critical if a flag is present, else Advisory** | Soft-gates Approved only when the triggering flag is present. |
| GST / compliance verified | Always | User | Confirmed with a qualified professional, not just the system's flag | **Critical** | Soft-gates Approved. |
| Quality consistency checked | After sample received | User | Cross-batch quality check, if more than one sample obtained | Advisory | Tracked only. |

**Formalizing Critical vs. Advisory:** FBP §12 names Supplier-contacted and Sample-ordered as critical without fully generalizing the concept. This document extends that baseline (those two remain always-critical) with **conditional criticality**: Trademark and GST/Marketplace-policy verification escalate to Critical whenever their corresponding risk flag is actually present in the report (§10, §4.5, §4.6) — an unflagged, low-risk category does not need the same friction as a flagged one. Critical items soft-gate the Approved lifecycle transition via a confirmation dialog, never a hard block (FBP Principle 3, §12) — this document does not change that mechanism, only which items participate in it and under what conditions.

---

## 16. Research Quality Standards

**Minimum evidence bar to score at all.** A dimension is only passed through the deterministic rubric (§2.2 Stage 7) if it has at least one source at Supplier tier or above (§5, reliability ≥0.6) *or* an Evidence Score ≥0.3 from multiple weaker sources combined. Below that bar, the dimension is marked `Unscored — Insufficient Evidence` (§4.4) rather than scored on thin grounds.

**When research should stop.** Once Research Completeness (§14) reaches 85% and no Critical-tier Evidence Conflict (§10) remains unresolved, the pipeline finalizes — additional evidence collection past this point has sharply diminishing value relative to the time/cost of gathering it.

**When research should continue.** Completeness between 70% and 85% triggers exactly one automatic re-query/retry pass on the specific under-evidenced dimensions (reusing the SRS's existing per-agent retry mechanism, SRS §12 Data Flow step 3b) before finalizing — not an open-ended retry loop.

**When research should request more evidence explicitly.** If a dimension's Confidence Score is materially higher than its Evidence Score (a "confident but unproven" pattern — the exact failure mode Evidence Score exists to catch, SRS §6), that dimension is flagged in the Decision Record (§13) and, where a retry is still available, gets priority for the one additional evidence pass above.

**When research should refuse to recommend.** Research Completeness below **40%**, or three or more of the eleven scored dimensions returning `Unscored — Insufficient Evidence`, produces a fifth terminal state: **Insufficient Data** — deliberately distinct from Reject. Reject means "we know enough, and it's a bad opportunity." Insufficient Data means "we don't know enough to say either way," and the report should visibly say so rather than forcing a number out of too little evidence.

**Cross-document note:** Insufficient Data is introduced here for the first time — it has no corresponding value in the SRS's `reports.status` enum or the FBP's lifecycle states (§17) yet. This is flagged explicitly rather than silently assumed; reconciling it into both documents is listed as Future Improvement #25 in the Final Self-Review.

---

## 17. Research Ethics

**Never fabricate suppliers. Never fabricate sales. Never fabricate market data.** This is enforced structurally, not just as a stated value: every atomic fact the system asserts carries one of exactly four provenance tags, and the tag travels with the fact everywhere it's used or displayed.

| Tag | Meaning | Rule |
|---|---|---|
| **Verified** | Confirmed by a Government/Manufacturer-tier source (§5) or by explicit human manual verification (§15). | May be used at full weight anywhere. |
| **Estimated** | Derived from real evidence via the deterministic model/rubric (e.g. a price band computed from actual marketplace listings). | Must be visibly labeled as an estimate; never presented as equivalent to Verified. |
| **Assumed** | No direct evidence exists; filled from a category-level default or heuristic (e.g. a default GST% for the category, a default packaging-cost ratio). | Must always be visibly labeled; counts partially against Research Completeness (§14). |
| **Unknown** | No evidence and no reasonable default exists. | Must be shown as Unknown. **Never silently defaulted to a mid-range or average value to "fill the gap."** This is the single most important rule in this document — it is the structural defense against the exact failure mode named in §1: a confident-sounding answer with nothing behind it. |

This four-tag system is the ethical-layer implementation of the Evidence Hierarchy (§5) and feeds Research Completeness (§14) directly: `Unknown` fields count as not-covered; `Assumed` fields count as partially-covered; only `Verified`/`Estimated` fields count as fully-covered.

**Known limitation:** the tagging is currently applied by the AI reasoning step itself (§2.2 Stage 5/6), with no independent auditor step verifying the tagger isn't mislabeling `Assumed` as `Estimated` to make a report look better-evidenced than it is. See Final Self-Review Weakness #11 and Future Improvement #21.

---

## 18. Future Intelligence

Extension points only — none of the below is implemented or scheduled; each is a reserved seam this specification is designed not to block.

- **Historical learning.** Rubric weights and thresholds (§12) are versioned, and are intended to be periodically recalibrated against real outcome data — but only via a human-reviewed, versioned rubric bump (mirroring the SRS's prompt-versioning discipline, SRS §5), never automatic silent retuning by the system itself.
- **User feedback.** A future "was this recommendation right?" capture, feeding the calibration cycle above.
- **Sales feedback.** Post-launch actual sales/return/RTO data reconciled against the Demand and Logistics predictions that led to the original recommendation — the mechanism by which this system's rubrics eventually earn correctness, not just reproducibility (§1).
- **Marketplace connectors.** Once real connectors (SRS §8) go live, the *evidence quality ceiling* rises across the Demand, Competition, and Pricing Models — the scoring logic in §6–§7 does not change, only the reliability tier of the evidence feeding it.
- **Pricing history / trend history.** The SRS's append-only history tables (`pricing_history`, `trend_history`) enable a future move from point-in-time trend *estimation* to actual measured trend *slope* once enough longitudinal data accumulates.
- **AI self-improvement.** Strictly bounded: prompt wording may improve reasoning quality within an agent, but the deterministic rubric and weight values (§6–§12) are never auto-tuned by an AI without a human-reviewed, versioned change — the same discipline SRS Risk R4 already commits to for the rubric code, extended here to any future automated tuning proposal.

---

## Final Self-Review

*Conducted as Chief Research Officer, against this exact specification — not generic caveats.*

### Top 25 Weaknesses

1. Rubric signal→score lookup logic (§6–§11) is itself subjective, human-authored judgment encoded as if it were objective — determinism guarantees *reproducibility*, not *correctness*.
2. Rubrics and weights (§12.2) are category-agnostic: the same weighting applies to a ₹200 phone case and a ₹15,000 furniture item, despite very different demand/risk dynamics.
3. Research Completeness thresholds (70%/85%/40%, §14/§16) are asserted numbers with no validation data behind them yet.
4. Decision Confidence's band-capping trigger rate (§12.7) has never been run against a real score distribution.
5. Hard-reject rules (§12.5) can fire on a "confirmed" Trademark/Patent flag that, in MVP, can only ever come from AI-reasoning-tier pattern-matching (§4.6) — no real registry exists to actually confirm one, and no appeal path is defined for a false positive.
6. The Brand Potential Model (§11) is, in practice, close to 100% AI reasoning wearing an evidence-scored costume — almost none of its signals have a realistic path to a higher-reliability source.
7. The Financial Model's sensitivity analysis (§9.4) treats cost variables as independent, when a high-RTO category plausibly also correlates with higher acquisition cost — Worst Case may understate true downside.
8. The Evidence Hierarchy (§5) ranks source *types* globally, but type rank and situational *relevance* can diverge (a stale government filing vs. a highly relevant recent review) with no resolution mechanism for that tension.
9. The Unified Risk Score (§10.2) is a weighted sum that can mathematically average away a severe risk unless it happens to be one of the three risk types with hard-floor authority.
10. Category Detection (§2.2 Stage 3) has a fallback for *ambiguous* categorization but no recovery path for *confidently wrong* categorization, which silently mis-selects evidence sources and rubrics for the whole run.
11. The Verified/Estimated/Assumed/Unknown provenance system (§17) is self-tagged by the same reasoning step that produced the claim, with no independent auditor verifying the tagging itself.
12. No time-decay or re-verification trigger exists for a source that later turns out to be wrong (e.g. a government rate later found outdated).
13. The Demand Model (§6) is structurally weakest exactly for genuinely emerging categories — precisely where correctly spotting opportunity matters most — and only partially self-corrects via a lower Evidence Score.
14. Several Product DNA fields (§3: Expected lifecycle, Typical return causes, Typical RTO drivers, Expansion opportunities, Future SKU opportunities) have no dedicated Evidence Collection sub-stage of their own in §4 — they are AI-inferred labels riding on evidence gathered for other dimensions.
15. Evidence-vs-evidence conflicts between two same-rank sources (e.g. two connectors reporting different prices) have no defined tiebreak beyond "flag it" (§4, §10).
16. Critical vs. Advisory tiering for Human Verification (§15) is itself an unvalidated judgment call, not derived from any observed data on which items sellers actually skip.
17. The evidence-weighted scoring adjustment (§12.3) penalizes a dimension with genuinely unobtainable evidence identically to one where evidence collection simply failed — it cannot distinguish "nothing exists to find" from "we didn't look hard enough."
18. No defense exists against a user asserting a fact (e.g. "this supplier is verified") outside the system's own evidence chain — the provenance system has no adversarial-input guard.
19. The "Insufficient Data" terminal state (§16) is introduced only in this document and has no corresponding value in the SRS `reports.status` enum or the FBP lifecycle states — a real cross-document gap.
20. "Confidence Score" and "Decision Confidence" (§14) are close enough in name to risk confusion despite being deliberately distinct concepts, and this document proposes no naming/visual safeguard (left entirely to the FBP).
21. The weight rationale in §12.2 (e.g. "Logistics gets 12 because RTO is the biggest margin killer") is asserted from general domain knowledge, not from this system's own outcome data — circular until real calibration exists.
22. Supplier Intelligence's "pricing stability" and "communication quality" signals (§8) are inherently longitudinal metrics being force-fit into a single point-in-time research pass.
23. Category Detection (§2.2 Stage 3, §3) assumes one category per product, with no defined handling for genuinely multi-category products (e.g. a "Yoga Mat Bag").
24. `Assumed`-tier category-level defaults (e.g. default GST%, §9.2) are themselves static and go stale as tax law or category norms change, with no defined re-validation cadence.
25. The entire specification assumes India-first, single-market research; no defined behavior exists for simultaneous multi-country research intent, where evidence hierarchies and compliance rubrics would need to diverge per country.

### Top 25 Missing Opportunities

1. No mechanism to track, over time, whether high-Decision-Confidence recommendations actually turn out correct more often than low-confidence ones — the actual test of whether this system works.
2. No category-specific rubric variants, despite the taxonomy (§2/§3) already existing to key them off of.
3. No cross-product evidence reuse — shared suppliers/categories between two researched products currently mean fully redundant evidence collection.
4. No distinct signal for "this category is genuinely novel/unclassifiable" beyond a generic lower-evidence-weight downgrade.
5. No evidence-freshness scoring dimension — a two-year-old industry report currently scores identically to one from last month within the same source-type tier.
6. No structured reject-reason taxonomy captured when a hard-reject rule fires, which would otherwise be immediately useful for future rubric tuning.
7. No internal adversarial self-critique pass (asking the model to argue against its own conclusion) before finalizing signals.
8. No distinct handling for a product name likely referring to a trending/viral item, whose demand dynamics differ from steady-state category demand — currently folded generically into the Demand Model.
9. No plan for the system's own accumulated verification outcomes (supplier verified-good/bad, sample-matched-description) to become a first-party evidence source over time.
10. No first-class "evidence gap report" — a simple list of exactly which evidence types were sought but not found, useful to both the user and future connector prioritization.
11. No "second opinion" mode — a cheap re-run of Decision Synthesis reasoning under different framing to detect reasoning instability as a proxy for robustness.
12. No use of "graveyard category" patterns (a category repeatedly researched and repeatedly Rejected) to temper Demand Model optimism for structurally saturated categories.
13. No self-consistency check comparing a re-researched product's new dimension scores against its own prior run to flag unexplained swings, beyond a generic staleness notice.
14. No process for a domain expert to review/annotate a sample of runs for rubric-quality auditing, distinct from ordinary end-user manual verification.
15. No lightweight taxonomy distinguishing known-reliable vs. known-risky supplier platforms beyond generically naming IndiaMART/TradeIndia.
16. No proactive mechanism to update `Assumed`-tier compliance defaults when regulations change — only reactive staleness discovery.
17. No standalone deliverable built from Review Mining's "missing features" output beyond feeding Brand Potential internally — could be its own differentiation brief.
18. No marketplace-relevance weighting — evidence collection currently treats Amazon-specific and Meesho-specific relevance as equal regardless of the seller's actual target marketplace.
19. No detection of internal contradiction *within* a single agent's own signal set — only cross-agent conflicts are currently specified.
20. No portfolio-level view aggregating Decision Confidence and expected value across a user's full research history.
21. No use of a user's own Research Completeness history (e.g. consistently low for compliance-heavy categories) as an onboarding nudge to supply better hints upfront.
22. No "what would change this decision" feature — surfacing the single highest-leverage missing evidence item for a borderline-confidence report.
23. No shadow-mode process for testing a proposed new rubric version silently against live traffic before promoting it.
24. No aggregation of anonymized Assumed/Unknown-tag frequency across runs to prioritize which evidence gaps are most common and most worth closing via future connectors.
25. No category-level base-rate library (e.g. typical RTO% by category, derived from aggregated past runs) that would let `Assumed` defaults become genuinely evidence-derived once enough volume exists, rather than one-off heuristics.

### Top 25 Future Improvements

1. Build category-specific rubric variants once per-category volume justifies the added maintenance surface.
2. Introduce a versioned, human-reviewed quarterly rubric-calibration cycle comparing predicted bands against actual decision-journal outcomes.
3. Add an evidence-freshness decay factor to the Evidence Score formula.
4. Define an explicit tiebreak procedure for same-rank evidence conflicts, rather than "flag it" alone.
5. Define a structured reject-reason taxonomy for every hard-reject and Reject-band recommendation.
6. Build the proprietary first-party evidence layer from accumulated verification outcomes, formally raising its hierarchy rank once sufficient volume exists.
7. Ship an "evidence gap report" as a first-class report section.
8. Add an internal self-consistency/adversarial-critique pass as a Decision Confidence input.
9. Define multi-category (primary + secondary) product handling instead of forcing single-category assignment.
10. Build a per-category base-rate library from aggregated historical runs, replacing one-off `Assumed` defaults.
11. Define a formal appeal/override path for hard-reject rules that fire on an unverified, reasoning-only signal.
12. Retune Research Completeness and Decision Confidence thresholds against real production score distributions.
13. Add marketplace-relevance weighting to evidence collection and scoring emphasis.
14. Define a formal regulatory-change monitoring process to proactively invalidate stale `Assumed` compliance defaults.
15. Add cross-product evidence reuse for shared suppliers/categories.
16. Define a "second opinion" adversarial-critique pass for Decision Synthesis's narrative, distinct from the deterministic score.
17. Build a portfolio-level Decision Confidence / expected-value view once History volume justifies it.
18. Formalize a rubric shadow-mode deployment process ahead of any new rubric-version promotion.
19. Add graveyard-category detection as an input that tempers Demand Model optimism for structurally saturated categories.
20. Expand the Unified Risk Score with explicit floor rules for every risk type, not just the current subset, once each type has a trustworthy-enough evidence source.
21. Define an independent auditor step that spot-checks the AI reasoning step's own provenance self-tagging (§17), rather than trusting it unverified.
22. Define country-specific evidence hierarchies and compliance rubric variants ahead of any multi-market expansion.
23. Build the "what would change this decision" feature, surfacing the single highest-leverage missing evidence item for borderline reports.
24. Define correlation-aware sensitivity analysis in the Financial Model, once real outcome data exists to estimate cost-variable correlations.
25. Formalize the "Insufficient Data" terminal state into the SRS's `reports.status` enum and the FBP's lifecycle states, closing the cross-document gap named in Weakness #19.

### Which scoring models are most subjective, and the path to making them evidence-based

| Model | Why it's subjective today | Path forward |
|---|---|---|
| **Brand Potential (§11)** | Almost entirely AI-reasoning-tier; no realistic MVP-era source outranks reasoning for "does this support a good brand story." | Accumulate real outcome data via the future decision journal (§18) — did repeat purchase/cross-sell actually materialize — and replace subjective whitespace judgment with measured category-level success-rate base rates over time. |
| **Demand growth/decay for emerging categories (§6)** | Structurally evidence-sparse by definition — the categories most worth getting right have the least history to reason from. | Real search-volume/sales-rank time series once marketplace connectors ship (SRS §8, §21), replacing reasoning-based trend inference with a measured slope. |
| **Decision Engine weight rationale (§12.2)** | Currently asserted from general Indian-ecommerce domain knowledge, not this system's own data. | The rubric-calibration cycle (§18, Future Improvement #2) — the intended mechanism by which weights graduate from "reasonable assertion" to "empirically justified." |
| **Rubric signal→score lookup tables generally (§6–§11)** | Human-authored judgment encoded as fixed rules, dressed in the language of determinism. | This is not a flaw to eliminate before launch — determinism buys reproducibility and auditability *now*, which is what makes the calibration cycle possible *later*. The lookup tables are meant to be a versioned, improvable starting point, not a claim of present-day correctness. Treat v1.0 of every rubric in this document as a bootstrap phase whose entire purpose is to be measured against reality and revised on purpose — not evidence of failure if it needs revising. |

---

*End of PRS v1.0. This document defines how the intelligence layer thinks; it does not implement it. No implementation begins until this, alongside the SRS and FBP, is explicitly approved.*
