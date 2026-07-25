"""Profit & Unit Economics — fully deterministic, no LLM (SRS §11 agent #11).

Formulas (documented here since this file is the single source of truth for them):

  marketplace_fee = selling_price * marketplace_fee_pct / 100
  gst_amount      = selling_price * gst_pct / 100
  total_cost      = buying_price + shipping_cost + packaging_cost + marketplace_fee
                     + gst_amount + ad_cost + return_cost + rto_cost
  net_profit      = selling_price - total_cost
  margin_pct      = net_profit / selling_price * 100
  roi_pct         = net_profit / buying_price * 100

Break-even needs a fixed-cost basis, which a single per-unit cost entry doesn't supply.
If the caller doesn't provide one, we assume a 50-unit first batch (buying_price * 50) —
this assumption is always returned explicitly (`breakeven_basis`) and tagged `Assumed`
per PRS §17, never presented as a measured fact.
"""

import math
from dataclasses import dataclass, field

DEFAULT_BATCH_SIZE_UNITS = 50


@dataclass
class ProfitInputs:
    selling_price: float
    buying_price: float
    shipping_cost: float = 0
    packaging_cost: float = 0
    marketplace_fee_pct: float = 0
    ad_cost: float = 0
    gst_pct: float = 18
    return_cost: float = 0
    rto_cost: float = 0
    closing_fee: float = 0  # added for the Data Collection Engine (Phase 2) — a flat
    # per-unit marketplace closing fee (e.g. Meesho-style), distinct from the
    # percentage-based marketplace_fee_pct. Defaults to 0 so every Phase 1 caller
    # is unaffected.
    initial_investment: float | None = None


@dataclass
class ProfitResult:
    net_profit: float
    margin_pct: float
    roi_pct: float | None
    breakeven_units: int | None
    breakeven_basis: str
    marketplace_fee: float
    gst_amount: float
    total_cost: float


@dataclass
class ProfitScenarios:
    best_case: ProfitResult
    expected_case: ProfitResult
    worst_case: ProfitResult


def _compute(inputs: ProfitInputs) -> ProfitResult:
    marketplace_fee = inputs.selling_price * inputs.marketplace_fee_pct / 100
    gst_amount = inputs.selling_price * inputs.gst_pct / 100
    total_cost = (
        inputs.buying_price
        + inputs.shipping_cost
        + inputs.packaging_cost
        + marketplace_fee
        + inputs.closing_fee
        + gst_amount
        + inputs.ad_cost
        + inputs.return_cost
        + inputs.rto_cost
    )
    net_profit = inputs.selling_price - total_cost
    margin_pct = (net_profit / inputs.selling_price * 100) if inputs.selling_price > 0 else 0.0
    roi_pct = (net_profit / inputs.buying_price * 100) if inputs.buying_price > 0 else None

    if inputs.initial_investment is not None:
        investment = inputs.initial_investment
        basis = "user_provided"
    else:
        investment = inputs.buying_price * DEFAULT_BATCH_SIZE_UNITS
        basis = f"assumed_{DEFAULT_BATCH_SIZE_UNITS}_unit_batch"

    breakeven_units = math.ceil(investment / net_profit) if net_profit > 0 else None

    return ProfitResult(
        net_profit=round(net_profit, 2),
        margin_pct=round(margin_pct, 2),
        roi_pct=round(roi_pct, 2) if roi_pct is not None else None,
        breakeven_units=breakeven_units,
        breakeven_basis=basis,
        marketplace_fee=round(marketplace_fee, 2),
        gst_amount=round(gst_amount, 2),
        total_cost=round(total_cost, 2),
    )


def compute_profit(inputs: ProfitInputs) -> ProfitResult:
    return _compute(inputs)


def compute_scenarios(inputs: ProfitInputs) -> ProfitScenarios:
    """Best/Expected/Worst case sensitivity (PRS §9.4).

    Best case: +10% selling price, -30% return/RTO cost, -20% ad cost.
    Worst case: -10% selling price, +30% return/RTO cost, +20% ad cost.
    Variables are varied independently — PRS §9.4 names this as a known
    simplification (real-world return-rate/ad-cost correlation isn't modeled yet).
    """
    expected = _compute(inputs)

    best_inputs = ProfitInputs(
        **{**inputs.__dict__, "selling_price": inputs.selling_price * 1.10,
           "return_cost": inputs.return_cost * 0.7, "rto_cost": inputs.rto_cost * 0.7,
           "ad_cost": inputs.ad_cost * 0.8}
    )
    worst_inputs = ProfitInputs(
        **{**inputs.__dict__, "selling_price": inputs.selling_price * 0.90,
           "return_cost": inputs.return_cost * 1.3, "rto_cost": inputs.rto_cost * 1.3,
           "ad_cost": inputs.ad_cost * 1.2}
    )

    return ProfitScenarios(
        best_case=_compute(best_inputs),
        expected_case=expected,
        worst_case=_compute(worst_inputs),
    )


def financial_sub_score(scenarios: ProfitScenarios) -> float:
    """Deterministic rubric mapping margin/ROI -> 0-100 sub-score (PRS §12.2 Profit weight = 11).

    Uses the Expected Case as the primary basis, discounted if the Worst Case
    is unprofitable — mirrors the Decision Engine's own hard-reject logic (PRS §12.5)
    at the single-dimension level.
    """
    margin = scenarios.expected_case.margin_pct
    if margin >= 30:
        base = 92.0
    elif margin >= 20:
        base = 78.0
    elif margin >= 10:
        base = 60.0
    elif margin >= 0:
        base = 35.0
    else:
        base = 10.0

    if scenarios.worst_case.net_profit < 0 and base > 60:
        base = 60.0  # cap: never "strong" on a score whose worst case is a loss

    return round(min(100.0, max(0.0, base)), 1)
