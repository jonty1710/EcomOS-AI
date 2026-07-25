"""Source Registry — every known data provider in the system today, plus
the two reserved-for-later providers (Knowledge Engine's future connectors,
and the future AI Provider) that don't produce field values yet but are
registered so nothing has to change structurally when they do.

`baseline_reliability` values are not invented for this phase — they reuse
PRS §5's Evidence Hierarchy reliability scores wherever a direct analogue
exists, so a "Marketplace" source here means the same trust level it means
throughout the rest of this system's design docs:

  Government        1.0   (not a provider in this system yet — no gov't connector)
  Manufacturer       0.9
  Marketplace        0.85
  Industry report    0.75  <- Knowledge Engine's curated reference content
  Supplier           0.6
  User (self-report) 0.85  <- Phase 2 collector.py's existing "user_input" confidence
  AI reasoning       0.3   (not reachable yet — no provider wired in)
  Calculation        1.0   <- deterministic math has no uncertainty of its own

This is a static registry (like app/collection/field_registry.py and
app/knowledge/*.json) — one canonical list every other provenance module
reads from, never redeclared.
"""

from app.provenance.schemas import RefreshStrategy, SourceDefinition, SourceType

_REGISTRY_LIST: list[SourceDefinition] = [
    SourceDefinition(
        key="marketplace", label="Marketplace",
        default_source_type=SourceType.AUTO_COLLECTED,
        baseline_reliability=0.85,
        description="A live marketplace listing (Amazon/Flipkart/Meesho) — reachable once a ProductDataConnector (app/connectors/product_connector.py) is implemented. Not reachable in this phase.",
        typically_requires_verification=False,
        default_refresh_strategy=RefreshStrategy.PERIODIC,
        evidence_tier_reference="PRS §5 tier: Marketplace (0.85)",
    ),
    SourceDefinition(
        key="manufacturer", label="Manufacturer",
        default_source_type=SourceType.IMPORTED,
        baseline_reliability=0.9,
        description="A manufacturer spec sheet or direct certification — reachable once a manufacturer API connector exists. Not reachable in this phase.",
        typically_requires_verification=False,
        default_refresh_strategy=RefreshStrategy.ON_DEMAND,
        evidence_tier_reference="PRS §5 tier: Manufacturer (0.9)",
    ),
    SourceDefinition(
        key="supplier", label="Supplier",
        default_source_type=SourceType.USER_ENTERED,
        baseline_reliability=0.6,
        description="Information relayed from a supplier conversation and typed in by the user (Buying Price, MOQ, Lead Time, GST Available) — the person is a conduit, the supplier is the actual origin.",
        typically_requires_verification=True,
        default_refresh_strategy=RefreshStrategy.MANUAL_ONLY,
        evidence_tier_reference="PRS §5 tier: Supplier (0.6)",
    ),
    SourceDefinition(
        key="user", label="User",
        default_source_type=SourceType.USER_ENTERED,
        baseline_reliability=0.85,
        description="Directly entered by the person doing the research, with no further relay (product name, notes, physical measurements they took themselves).",
        typically_requires_verification=False,
        default_refresh_strategy=RefreshStrategy.MANUAL_ONLY,
        evidence_tier_reference="Matches Phase 2 collector.py's existing user-input confidence baseline (0.85)",
    ),
    SourceDefinition(
        key="calculation_engine", label="Calculation Engine",
        default_source_type=SourceType.CALCULATED,
        baseline_reliability=1.0,
        description="This system's own deterministic Python — arithmetic (Net Cost, Margin, ROI) and rule-based classification (Category detection, Fragility, Packaging Suggestion). No uncertainty beyond its inputs'.",
        typically_requires_verification=False,
        default_refresh_strategy=RefreshStrategy.ON_EDIT,
        evidence_tier_reference="PRS §5 tier: Calculation (1.0) — deterministic math is not a claim needing corroboration",
    ),
    SourceDefinition(
        key="knowledge_engine", label="Knowledge Engine",
        default_source_type=SourceType.IMPORTED,
        baseline_reliability=0.75,
        description="Curated reference data from the Knowledge Engine (Phase 3) — category/material/logistics patterns loaded from seed JSON, not a claim about this specific product.",
        typically_requires_verification=False,
        default_refresh_strategy=RefreshStrategy.ON_DEMAND,
        evidence_tier_reference="PRS §5 tier: Industry report (0.75) — curated reference, same trust class",
    ),
    SourceDefinition(
        key="ai_provider", label="Future AI Provider",
        default_source_type=SourceType.AUTO_COLLECTED,
        baseline_reliability=0.3,
        description="Reasoning from an AI provider (app/ai/providers/base_provider.py) — reserved, zero implementations exist yet in this codebase. Not reachable in this phase.",
        typically_requires_verification=True,
        default_refresh_strategy=RefreshStrategy.ON_DEMAND,
        evidence_tier_reference="PRS §5 tier: AI reasoning (0.3) — the weakest evidence tier by design",
    ),
]

SOURCE_REGISTRY: dict[str, SourceDefinition] = {s.key: s for s in _REGISTRY_LIST}
