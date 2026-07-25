"""Research Engine — the orchestration layer (NOT AI, PRS §2 pipeline stages 2-9
condensed for Phase 1's manual-only mode).

    Product Name
       v
    Normalization + Category Detection
       v
    Knowledge Engine lookup (Phase 3 — deterministic grounding context)
       v
    Run deterministic modules (agent registry, asyncio.gather)
       v
    Deterministic Scoring + Risk Analysis (app/scoring/*)
       v
    Unified report (ReportResponse)

No LLM calls anywhere in this file or anything it imports. The Knowledge
Engine lookup happens BEFORE the agent registry runs, per the Phase 3 brief:
"The Research Engine should consume this Knowledge Pack before any future AI
reasoning" — every agent, present and future, receives the same
`ResearchContext.knowledge_pack`.
"""

import asyncio
import re
import uuid
from datetime import datetime, timezone

from app.knowledge.engine import classify_detected_marketplace, get_knowledge_pack_from_fields
from app.models.schemas import ModuleSection, ModuleStatus, ReportResponse
from app.research.agents import build_agent_registry
from app.research.base_agent import ResearchContext
from app.research.category_detection import detect_category
from app.research.logistics import build_logistics_profile
from app.scoring.decision import compute_composite


def normalize_product_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


MANUAL_VERIFICATION_BASE_CHECKLIST = [
    "Supplier contacted and terms confirmed directly.",
    "GST category confirmed with a qualified professional.",
    "Pricing confirmed against live marketplace listings.",
    "Trademark / brand-name clearance searched independently.",
]


async def run_manual_research(request_data: dict) -> ReportResponse:
    """Entry point used by the API layer. Accepts the validated
    `ManualResearchRequest` fields as a dict (already model_dump()'d) and returns
    a complete, unpersisted `ReportResponse`. Persistence is the caller's job
    (app/services/report_service.py) — this function has no DB dependency,
    which keeps it trivially unit-testable (see backend/tests).
    """
    product_name = request_data["product_name"]
    category_result = detect_category(product_name, request_data.get("category_hint"))

    # Knowledge Engine lookup — same deterministic weight/material classifiers
    # LogisticsPreliminaryAgent uses (app/research/logistics.py), computed once
    # here so the signature is available before any agent runs. Cheap, pure,
    # side-effect-free — recomputing it inside the agent too is intentional
    # duplication, not a bug (see app/research/agents.py), to avoid coupling
    # agent internals to orchestrator-only state.
    logistics_profile = build_logistics_profile(request_data.get("weight_grams"), request_data.get("material"))
    marketplace, supplier_platform = classify_detected_marketplace(request_data.get("detected_marketplace"))
    knowledge_pack = get_knowledge_pack_from_fields(
        category=category_result.category if category_result.category != "Uncategorized" else None,
        materials=(request_data["material"],) if request_data.get("material") else (),
        marketplace=marketplace,
        supplier_platform=supplier_platform,
        weight_class=logistics_profile.weight_class if logistics_profile.weight_source == "provided" else None,
        fragility=logistics_profile.fragility if logistics_profile.material_source != "unknown" else None,
    )

    context = ResearchContext(
        product_name=product_name,
        category=category_result.category,
        manual_inputs=request_data,
        knowledge_pack=knowledge_pack,
    )

    agents = build_agent_registry()
    sections: list[ModuleSection] = await asyncio.gather(*(agent.run(context) for agent in agents))

    profit_section = next(s for s in sections if s.agent_type == "profit_unit_economics")
    logistics_section = next(s for s in sections if s.agent_type == "logistics_risk")

    composite = compute_composite(
        financial_sub_score=profit_section.sub_score or 0.0,
        preliminary_risk_level=logistics_section.data.get("risk_level"),
    )

    checklist = list(MANUAL_VERIFICATION_BASE_CHECKLIST)
    if logistics_section.data.get("fragility") == "High":
        checklist.append("Packaging tested — high-fragility item flagged by the preliminary logistics read.")

    now = datetime.now(timezone.utc)
    return ReportResponse(
        id=str(uuid.uuid4()),
        product_name=product_name,
        category=category_result.category,
        status="insufficient_data" if composite.overall_score is None else "completed",
        research_mode="manual",
        overall_score=composite.overall_score,
        risk_level=composite.risk_level,
        recommendation=composite.recommendation,
        is_saved=False,
        sections=sections,
        manual_verification_checklist=checklist,
        research_completeness_pct=composite.research_completeness_pct,
        recommendation_explanation=composite.explanation,
        knowledge_pack=knowledge_pack,
        created_at=now,
        completed_at=now,
    )
