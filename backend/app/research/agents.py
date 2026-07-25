"""Concrete Phase 1 agents.

Two are real (deterministic, no AI): Profit & Unit Economics, and a
*preliminary* Logistics & Fulfillment Risk. The remaining nine of the eleven
scored dimensions (SRS §11 / PRS §12.2) are `PlannedForAIPhaseAgent` stubs —
they never fabricate a signal or score; they return a section explicitly
marked `planned_for_ai_phase` so the Report Screen can render an honest
"Not yet connected" state (per the Phase 1 brief, and PRS §17 Research Ethics).

Phase 3 adds the Knowledge Engine (app/knowledge/): both real agents now
enrich their `reasoning` text with curated category/material/logistics
reference context when available — always clearly framed as general/typical
information, never as a claim about this specific product. The planned
agents surface a `knowledge_preview` in `data` (never in `reasoning`, since
no reasoning has actually happened) showing what grounding context will be
available to them once AI is wired in.
"""

from app.knowledge.schemas import KnowledgePack
from app.models.schemas import ModuleSection, ModuleStatus, SourceRef
from app.research.base_agent import ResearchAgent, ResearchContext
from app.research.logistics import build_logistics_profile
from app.scoring.decision import DIMENSION_LABELS, DIMENSION_WEIGHTS
from app.scoring.profit import ProfitInputs, compute_scenarios, financial_sub_score
from app.scoring.risk import compute_preliminary_risk


def _knowledge_preview_for_agent(agent_type: str, pack: KnowledgePack | None) -> str | None:
    """One-line preview of what the Knowledge Engine already has for a
    still-planned dimension — visible today, usable by AI reasoning later.
    Returns None when this pack has nothing relevant for this agent_type
    (never invents a preview for a dimension the seed data doesn't cover).
    """
    if pack is None:
        return None
    cat = pack.category_knowledge
    if agent_type == "demand" and cat:
        return f"Category reference: typical demand pattern for {cat.category} is '{cat.typical_demand_pattern}'."
    if agent_type == "competitive_landscape" and cat:
        return f"Category reference: typical competition level for {cat.category} is '{cat.typical_competition_level}'."
    if agent_type == "pricing_intelligence" and cat:
        lo, hi = cat.typical_margin_band_pct
        return f"Category reference: typical margin band for {cat.category} is {lo}-{hi}%."
    if agent_type == "trend_seasonality" and cat:
        return f"Category reference: {cat.seasonality_notes}"
    if agent_type == "brand_positioning" and cat:
        return f"Category reference: {cat.brand_potential_notes}"
    if agent_type == "supplier_sourcing" and pack.supplier_knowledge:
        return f"Sourcing reference already available for platform '{pack.supplier_knowledge.platform}': {pack.supplier_knowledge.typical_moq_notes}"
    if agent_type == "compliance_regulatory" and pack.compliance_knowledge:
        labels = ", ".join(c.label for c in pack.compliance_knowledge)
        return f"{len(pack.compliance_knowledge)} compliance flag(s) already identified for this category/material: {labels}."
    return None


class ProfitAgent(ResearchAgent):
    agent_type = "profit_unit_economics"
    weight = DIMENSION_WEIGHTS["profit_unit_economics"]

    async def run(self, context: ResearchContext) -> ModuleSection:
        mi = context.manual_inputs
        inputs = ProfitInputs(
            selling_price=mi["selling_price"],
            buying_price=mi["buying_price"],
            shipping_cost=mi.get("shipping_cost") or 0,
            packaging_cost=mi.get("packaging_cost") or 0,
            marketplace_fee_pct=mi.get("marketplace_fee_pct") or 0,
            ad_cost=mi.get("ad_cost") or 0,
            gst_pct=mi.get("gst_pct") if mi.get("gst_pct") is not None else 18,
            return_cost=mi.get("return_cost") or 0,
            rto_cost=mi.get("rto_cost") or 0,
            closing_fee=mi.get("closing_fee") or 0,
        )
        scenarios = compute_scenarios(inputs)
        sub_score = financial_sub_score(scenarios)

        reasoning = (
            "Computed directly from your entered costs — 100% deterministic arithmetic, "
            "no AI reasoning involved (PRS §9)."
        )
        cat = context.knowledge_pack.category_knowledge if context.knowledge_pack else None
        if cat:
            lo, hi = cat.typical_margin_band_pct
            reasoning += (
                f" For reference, {cat.category} products typically run a {lo}-{hi}% margin "
                f"(curated category data, not a claim about this specific product) — your computed "
                f"margin here is {scenarios.expected_case.margin_pct}%."
            )

        return ModuleSection(
            agent_type=self.agent_type,
            label=DIMENSION_LABELS[self.agent_type],
            status=ModuleStatus.COMPLETED,
            data={
                "expected_case": scenarios.expected_case.__dict__,
                "best_case": scenarios.best_case.__dict__,
                "worst_case": scenarios.worst_case.__dict__,
            },
            signals={},  # pure arithmetic — no LLM signals, per SRS §11 agent #11
            reasoning=reasoning,
            confidence_score=1.0,  # fixed maximum: deterministic math, not a claim needing corroboration
            evidence_score=1.0,
            sub_score=sub_score,
            sources=[SourceRef(type="manual", name="User-entered costs")],
            requires_manual_verification=False,
            weight_in_decision_engine=self.weight,
        )


class LogisticsPreliminaryAgent(ResearchAgent):
    agent_type = "logistics_risk"
    weight = DIMENSION_WEIGHTS["logistics_risk"]

    async def run(self, context: ResearchContext) -> ModuleSection:
        mi = context.manual_inputs
        profile = build_logistics_profile(mi.get("weight_grams"), mi.get("material"))
        risk = compute_preliminary_risk(
            fragility=profile.fragility,
            weight_class=profile.weight_class,
            selling_price=mi["selling_price"],
            return_cost=mi.get("return_cost") or 0,
            rto_cost=mi.get("rto_cost") or 0,
        )
        # Preliminary risk score inverted to a 0-100 "goodness" sub-score, consistent
        # with every other dimension's convention (higher sub_score = better).
        sub_score = round(100 - risk.risk_score, 1)

        reasoning = (
            f"Preliminary read only — {risk.basis} "
            "This is not the full Logistics & Fulfillment Risk score PRS §10 describes; "
            "RTO/return proneness evidence from real market data requires the AI phase."
        )
        pack = context.knowledge_pack
        if pack and pack.logistics_knowledge:
            causes = ", ".join(pack.logistics_knowledge.typical_rto_causes)
            reasoning += f" Typical RTO causes for {profile.weight_class.lower()}-weight items: {causes}."
        if pack and pack.packaging_knowledge:
            lo, hi = pack.packaging_knowledge.cost_band_pct_of_selling_price
            reasoning += f" Typical packaging cost for this weight/fragility combination runs {lo}-{hi}% of selling price."

        return ModuleSection(
            agent_type=self.agent_type,
            label=DIMENSION_LABELS[self.agent_type],
            status=ModuleStatus.UNSCORED_INSUFFICIENT_EVIDENCE if profile.weight_source == "unknown" else ModuleStatus.COMPLETED,
            data={
                "weight_class": profile.weight_class,
                "fragility": profile.fragility,
                "suggested_packaging": profile.suggested_packaging,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "components": {
                    "fragility": risk.fragility_component,
                    "weight": risk.weight_component,
                    "rto_ratio": risk.rto_ratio_component,
                    "return_ratio": risk.return_ratio_component,
                },
            },
            signals={},
            reasoning=reasoning,
            confidence_score=0.6 if profile.weight_source == "provided" else 0.3,
            evidence_score=0.4 if profile.material_source == "provided_matched" else 0.2,
            sub_score=sub_score,
            sources=[SourceRef(type="manual", name="User-entered weight/material")]
            if profile.weight_source == "provided"
            else [],
            requires_manual_verification=False,
            weight_in_decision_engine=self.weight,
            unavailable_reason=None,
        )


class PlannedForAIPhaseAgent(ResearchAgent):
    """One instance per AI-dependent dimension. Never invents a signal or score."""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.weight = DIMENSION_WEIGHTS[agent_type]

    async def run(self, context: ResearchContext) -> ModuleSection:
        preview = _knowledge_preview_for_agent(self.agent_type, context.knowledge_pack)
        return ModuleSection(
            agent_type=self.agent_type,
            label=DIMENSION_LABELS[self.agent_type],
            status=ModuleStatus.PLANNED_FOR_AI_PHASE,
            data={"knowledge_preview": preview} if preview else {},
            signals={},
            reasoning=None,
            confidence_score=None,
            evidence_score=None,
            sub_score=None,
            sources=[],
            requires_manual_verification=False,
            weight_in_decision_engine=self.weight,
            unavailable_reason=(
                "This dimension requires AI-driven evidence gathering and reasoning "
                "(SRS §11, PRS §6-§11), which is not part of Phase 1 (Foundation). "
                "Planned for the AI Integration phase."
            ),
        )


def build_agent_registry() -> list[ResearchAgent]:
    """The full 11-agent roster (SRS §11), in weight-table order. This is the
    ONLY place that decides which agents are real vs. planned — the orchestrator
    just iterates whatever this returns.
    """
    deterministic: dict[str, ResearchAgent] = {
        "profit_unit_economics": ProfitAgent(),
        "logistics_risk": LogisticsPreliminaryAgent(),
    }
    registry: list[ResearchAgent] = []
    for agent_type in DIMENSION_WEIGHTS:
        registry.append(deterministic.get(agent_type) or PlannedForAIPhaseAgent(agent_type))
    return registry
