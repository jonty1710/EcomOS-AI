"""Knowledge Engine — schemas.

The Knowledge Engine sits between the Data Collection Engine and any future
AI provider (SRS §21, PRS §18). It answers one question, deterministically:
"what does this system already know, in general, about a product like this?"
— category patterns, material properties, packaging guidance, logistics
norms, marketplace rules, supplier-sourcing intelligence, compliance flags,
and research methodology reminders.

It is NOT the Research Engine (which scores THIS specific product) and NOT
an AI provider (which will eventually reason over both this pack and the
product's own evidence). It is a grounding layer: curated, versioned,
inspectable reference data — never a live lookup, never a guess. Every
lookup either finds a real entry, falls back to an explicitly-labeled
generic entry, or returns nothing — it never fabricates a plausible-sounding
answer for a key it doesn't have (same rule the DCE enforces for product
fields, PRS §17 Research Ethics, applied one layer up).
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LibraryMatchStatus(str, Enum):
    """How a single library lookup resolved. Distinct from the DCE's
    FieldStatus (schemas there describe a *value*; this describes a
    *lookup outcome*), but the same honesty principle: never claim more
    certainty than actually exists.
    """

    MATCHED = "matched"  # an entry exists for exactly this key
    FALLBACK = "fallback"  # no exact entry; a generic/default entry was used instead
    NOT_AVAILABLE = "not_available"  # a key was given, but no entry (exact or generic) exists
    NOT_APPLICABLE = "not_applicable"  # no key was given at all — this library wasn't queried


# --- Individual library entry shapes (mirror the seed JSON files 1:1) -----------


class CategoryKnowledge(BaseModel):
    category: str
    typical_demand_pattern: str
    typical_competition_level: str
    typical_margin_band_pct: tuple[float, float]
    typical_return_rate_pct: float
    typical_rto_rate_pct: float
    typical_gst_pct: float
    common_materials: list[str] = Field(default_factory=list)
    common_compliance_flags: list[str] = Field(default_factory=list)
    seasonality_notes: str
    brand_potential_notes: str
    research_focus_notes: list[str] = Field(default_factory=list)
    source_hint: str


class MaterialKnowledge(BaseModel):
    material: str
    aliases: list[str] = Field(default_factory=list)
    fragility: str
    durability_notes: str
    sustainability_notes: str
    common_compliance_flags: list[str] = Field(default_factory=list)
    recommended_packaging_notes: str


class PackagingKnowledge(BaseModel):
    weight_class: str
    fragility: str
    suggested_packaging: str
    cost_band_pct_of_selling_price: tuple[float, float]
    damage_prevention_notes: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)


class LogisticsKnowledge(BaseModel):
    weight_class: str
    typical_shipping_cost_band_pct: tuple[float, float]
    typical_rto_causes: list[str] = Field(default_factory=list)
    typical_return_causes: list[str] = Field(default_factory=list)
    cod_notes: str
    carrier_notes: str


class MarketplaceKnowledge(BaseModel):
    marketplace: str
    typical_commission_pct_band: tuple[float, float]
    closing_fee_notes: str
    prohibited_category_notes: list[str] = Field(default_factory=list)
    listing_requirements: list[str] = Field(default_factory=list)
    return_policy_notes: str
    payment_cycle_notes: str


class SupplierIntelligenceKnowledge(BaseModel):
    platform: str
    typical_moq_notes: str
    typical_lead_time_days_band: tuple[int, int]
    verification_red_flags: list[str] = Field(default_factory=list)
    verification_best_practices: list[str] = Field(default_factory=list)
    negotiation_notes: str


class ComplianceKnowledge(BaseModel):
    flag_key: str
    label: str
    description: str
    applies_when: str
    required_action: str
    penalty_risk_notes: str
    verification_source_hint: str


class ResearchBestPractices(BaseModel):
    category: str | None  # None = the general/default entry
    checklist: list[str] = Field(default_factory=list)
    evidence_priority_notes: list[str] = Field(default_factory=list)
    common_pitfalls: list[str] = Field(default_factory=list)


# --- Signature (the deterministic cache key) and coverage ------------------------


class KnowledgePackSignature(BaseModel):
    """Every input that can affect a Knowledge Pack's contents. Two calls
    with an identical signature always produce an identical pack — this is
    what makes the pack-assembly cache correct (app/knowledge/engine.py).
    """

    category: str | None = None
    materials: tuple[str, ...] = ()
    marketplace: str | None = None
    supplier_platform: str | None = None
    weight_class: str | None = None
    fragility: str | None = None

    model_config = {"frozen": True}

    def cache_key(self) -> tuple:
        return (self.category, self.materials, self.marketplace, self.supplier_platform, self.weight_class, self.fragility)


class KnowledgePackCoverage(BaseModel):
    """Mirrors the DCE's Data Quality Score (PRS §14 "four distinct numbers,
    four distinct questions") one layer up: how much of the requested
    knowledge was actually available, vs. generic fallback, vs. missing.
    """

    category: LibraryMatchStatus
    materials: dict[str, LibraryMatchStatus] = Field(default_factory=dict)
    packaging: LibraryMatchStatus
    logistics: LibraryMatchStatus
    marketplace: LibraryMatchStatus
    supplier: LibraryMatchStatus
    compliance: LibraryMatchStatus
    research_best_practices: LibraryMatchStatus
    overall_coverage_pct: float


class KnowledgePack(BaseModel):
    """The single deterministic output of the Knowledge Engine for a given
    signature. This is what the Research Engine attaches to `ResearchContext`
    (app/research/base_agent.py) and what a future AI provider would read as
    grounding context before reasoning — see PRS §18 "Future Intelligence."
    """

    signature: KnowledgePackSignature
    category_knowledge: CategoryKnowledge | None = None
    material_knowledge: list[MaterialKnowledge] = Field(default_factory=list)
    packaging_knowledge: PackagingKnowledge | None = None
    logistics_knowledge: LogisticsKnowledge | None = None
    marketplace_knowledge: MarketplaceKnowledge | None = None
    supplier_knowledge: SupplierIntelligenceKnowledge | None = None
    compliance_knowledge: list[ComplianceKnowledge] = Field(default_factory=list)
    research_best_practices: ResearchBestPractices
    coverage: KnowledgePackCoverage
    generated_at: datetime
