"""Verifies the Knowledge Engine is actually consumed by the Research Engine
and reachable from the Data Collection Engine — not just wired but inert.
"""

import pytest

from app.collection.collector import collect
from app.collection.knowledge_bridge import knowledge_pack_for_profile
from app.research.orchestrator import run_manual_research


@pytest.mark.asyncio
async def test_orchestrator_attaches_knowledge_pack_to_report():
    report = await run_manual_research({
        "product_name": "Ceramic Mug",
        "selling_price": 349, "buying_price": 120, "shipping_cost": 30, "packaging_cost": 20,
        "weight_grams": 300, "material": "ceramic", "supplier_name": "PotteryCo",
    })
    assert report.knowledge_pack is not None
    assert report.knowledge_pack.category_knowledge.category == "Kitchen & Dining"


@pytest.mark.asyncio
async def test_profit_agent_reasoning_references_category_margin_band():
    report = await run_manual_research({
        "product_name": "Ceramic Mug",
        "selling_price": 349, "buying_price": 120, "shipping_cost": 30, "packaging_cost": 20,
        "weight_grams": 300, "material": "ceramic", "supplier_name": "PotteryCo",
    })
    profit_section = next(s for s in report.sections if s.agent_type == "profit_unit_economics")
    assert "margin" in profit_section.reasoning.lower()
    assert "Kitchen & Dining" in profit_section.reasoning


@pytest.mark.asyncio
async def test_planned_agent_surfaces_knowledge_preview_when_available():
    report = await run_manual_research({
        "product_name": "Ceramic Mug",
        "selling_price": 349, "buying_price": 120, "shipping_cost": 30, "packaging_cost": 20,
        "weight_grams": 300, "material": "ceramic", "supplier_name": "PotteryCo",
    })
    demand_section = next(s for s in report.sections if s.agent_type == "demand")
    assert demand_section.status.value == "planned_for_ai_phase"
    assert demand_section.reasoning is None  # still no fabricated reasoning
    assert "knowledge_preview" in demand_section.data  # but a real preview is available


@pytest.mark.asyncio
async def test_orchestrator_handles_missing_category_and_material_without_crashing():
    report = await run_manual_research({
        "product_name": "xyzzy plugh foobar",  # matches no category keyword
        "selling_price": 100, "buying_price": 50, "shipping_cost": 5, "packaging_cost": 5,
        "supplier_name": "X",
    })
    assert report.knowledge_pack is not None
    assert report.knowledge_pack.category_knowledge is None


def test_dce_profile_bridges_into_a_knowledge_pack():
    profile = collect("s1", {
        "product_name": "Yoga Mat", "selling_price": 799, "buying_price": 250,
        "shipping_cost": 50, "packaging_cost": 15, "supplier_name": "FitCo",
        "weight_grams": 900, "material": "rubber",
    })
    pack = knowledge_pack_for_profile(profile)
    assert pack.category_knowledge.category == "Fitness & Sports"
    assert pack.material_knowledge[0].material == "rubber"


def test_dce_bridge_passes_detected_marketplace_through_to_research_input():
    from app.collection.bridge import profile_to_research_input

    profile = collect("s1", {
        "product_name": "Ceramic Mug", "selling_price": 349, "buying_price": 120,
        "shipping_cost": 30, "packaging_cost": 20, "supplier_name": "PotteryCo",
        "weight_grams": 300, "material": "ceramic",
        "source_url": "https://www.amazon.in/dp/B000123",
    })
    payload = profile_to_research_input(profile)
    assert payload["detected_marketplace"] == "amazon"
