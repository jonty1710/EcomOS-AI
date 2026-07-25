"""Auto-Calculated Fields — 100% deterministic Python, no AI, no user input.

Reuses the SAME profit formula and logistics lookups already proven in the
Phase 1 Research Engine (app/scoring/profit.py, app/research/logistics.py)
rather than forking a second copy — one canonical formula, referenced from
both the Data Collection Engine and the Research Engine's Profit agent.
"""

from app.research.logistics import build_logistics_profile
from app.scoring.profit import ProfitInputs, compute_scenarios, financial_sub_score
from app.scoring.risk import FRAGILITY_RISK_POINTS


def calculate_discount_pct(mrp: float | None, selling_price: float | None) -> float | None:
    if mrp is None or selling_price is None or mrp <= 0:
        return None
    return round((mrp - selling_price) / mrp * 100, 2)


def calculate_pricing(values: dict) -> dict:
    """Computes Net Cost, Expected Profit, Margin, ROI, Break Even, and a Cost
    Structure breakdown. Returns {} for any field whose required inputs
    (Selling Price, Buying Price) are missing — never a fabricated placeholder.
    """
    selling_price = values.get("selling_price")
    buying_price = values.get("buying_price")
    if not isinstance(selling_price, (int, float)) or not isinstance(buying_price, (int, float)):
        return {"discount_pct": calculate_discount_pct(values.get("mrp"), selling_price)}

    inputs = ProfitInputs(
        selling_price=selling_price,
        buying_price=buying_price,
        shipping_cost=values.get("shipping_cost") or 0,
        packaging_cost=values.get("packaging_cost") or 0,
        marketplace_fee_pct=values.get("marketplace_fee_pct") or 0,
        closing_fee=values.get("closing_fee") or 0,
        ad_cost=values.get("ad_cost") or 0,
        gst_pct=values.get("gst_pct") if values.get("gst_pct") is not None else 18,
    )
    scenarios = compute_scenarios(inputs)
    expected = scenarios.expected_case

    total_cost = expected.total_cost or 1  # guard div-by-zero for the breakdown below
    cost_structure = {
        "buying_price": round(buying_price / total_cost * 100, 1),
        "shipping_cost": round((inputs.shipping_cost) / total_cost * 100, 1),
        "packaging_cost": round((inputs.packaging_cost) / total_cost * 100, 1),
        "marketplace_fee": round(expected.marketplace_fee / total_cost * 100, 1),
        "closing_fee": round(inputs.closing_fee / total_cost * 100, 1),
        "gst": round(expected.gst_amount / total_cost * 100, 1),
        "ad_cost": round(inputs.ad_cost / total_cost * 100, 1),
    }

    return {
        "discount_pct": calculate_discount_pct(values.get("mrp"), selling_price),
        "net_cost": expected.total_cost,
        "expected_profit": expected.net_profit,
        "margin_pct": expected.margin_pct,
        "roi_pct": expected.roi_pct,
        "breakeven_units": expected.breakeven_units,
        "profitability_score": financial_sub_score(scenarios),
        "cost_structure": cost_structure,
    }


def calculate_physical(values: dict) -> dict:
    """Weight Class, Fragility (+ Fragility Score), Packaging Type — reuses
    Phase 1's exact lookup tables (app/research/logistics.py, app/scoring/risk.py).
    """
    profile = build_logistics_profile(values.get("weight_grams"), values.get("material"))
    return {
        "weight_class": profile.weight_class,
        "fragility": profile.fragility,
        "packaging_type": profile.suggested_packaging,
        "fragility_score": FRAGILITY_RISK_POINTS.get(profile.fragility, 50),
    }


def calculate_all(values: dict) -> dict:
    """Runs every calculated field. `values` is the raw (validated) field-value
    dict keyed by field key. Returns a flat dict of calculated field key -> value,
    plus a nested "cost_structure" dict handled separately by the caller.
    """
    result: dict = {}
    result.update(calculate_pricing(values))
    result.update(calculate_physical(values))
    return result
