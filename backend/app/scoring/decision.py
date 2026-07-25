"""Decision Engine — PRS §12. Composite scoring, weighted per the SRS §6 / PRS §12.2
100-point table (unchanged here — this module only decides how much of that table
Phase 1 can actually fill in).

Phase 1 has no AI agents, so only two of the eleven scored dimensions can be
computed at all: Profit & Unit Economics (fully, it was always deterministic)
and a *preliminary* slice of Logistics & Fulfillment Risk (fragility/weight/
return-RTO ratios only, not the full evidence-backed risk read).

Per PRS §16 Research Quality Standards, Research Completeness this low
(well under the 40% hard floor) means the report must never claim a
Launch/Test/Reject recommendation — it produces the "Insufficient Data"
terminal state instead, honestly, rather than fabricating a composite score
from 2 of 11 dimensions.
"""

from dataclasses import dataclass

# PRS §12.2 / SRS §6 — the fixed 100-point weight table. Reproduced here (not
# re-derived) because the Decision Engine's arithmetic must match the approved
# spec exactly.
DIMENSION_WEIGHTS: dict[str, int] = {
    "demand": 15,
    "competitive_landscape": 10,
    "pricing_intelligence": 8,
    "trend_seasonality": 7,
    "review_mining": 8,
    "keyword_discoverability": 5,
    "supplier_sourcing": 8,
    "logistics_risk": 12,
    "compliance_regulatory": 8,
    "brand_positioning": 8,
    "profit_unit_economics": 11,
}
assert sum(DIMENSION_WEIGHTS.values()) == 100

DIMENSION_LABELS: dict[str, str] = {
    "demand": "Demand Intelligence",
    "competitive_landscape": "Competitive Landscape",
    "pricing_intelligence": "Pricing Intelligence",
    "trend_seasonality": "Trend & Seasonality",
    "review_mining": "Review Mining",
    "keyword_discoverability": "Keyword & Discoverability",
    "supplier_sourcing": "Supplier Sourcing",
    "logistics_risk": "Logistics & Fulfillment Risk",
    "compliance_regulatory": "Compliance & Regulatory",
    "brand_positioning": "Brand & Positioning",
    "profit_unit_economics": "Profit & Unit Economics",
}

# AI-dependent dimensions require a real evidence-gathering pass this phase doesn't have.
AI_DEPENDENT_DIMENSIONS = [
    d for d in DIMENSION_WEIGHTS if d not in ("profit_unit_economics", "logistics_risk")
]

RESEARCH_COMPLETENESS_HARD_FLOOR = 40.0  # PRS §16
RESEARCH_COMPLETENESS_NEEDS_REVIEW = 70.0  # PRS §12.6
LOGISTICS_PRELIMINARY_CREDIT_FRACTION = 0.4  # partial evidence only, PRS §16 min-evidence bar


@dataclass
class CompositeResult:
    research_completeness_pct: float
    overall_score: float | None
    recommendation: str
    risk_level: str | None
    explanation: str


def compute_research_completeness() -> float:
    """Weight-credit currently satisfiable without AI agents."""
    credit = DIMENSION_WEIGHTS["profit_unit_economics"]
    credit += DIMENSION_WEIGHTS["logistics_risk"] * LOGISTICS_PRELIMINARY_CREDIT_FRACTION
    return round(credit / sum(DIMENSION_WEIGHTS.values()) * 100, 1)


def compute_composite(
    financial_sub_score: float,
    preliminary_risk_level: str,
) -> CompositeResult:
    completeness = compute_research_completeness()

    if completeness < RESEARCH_COMPLETENESS_HARD_FLOOR:
        return CompositeResult(
            research_completeness_pct=completeness,
            overall_score=None,
            recommendation="Insufficient Data",
            risk_level=preliminary_risk_level,
            explanation=(
                f"Research Completeness is {completeness}%, below the {RESEARCH_COMPLETENESS_HARD_FLOOR}% "
                "hard floor (PRS §16). Only Profit & Unit Economics and a preliminary slice of "
                "Logistics & Fulfillment Risk are computable without AI agents — the remaining "
                f"{len(AI_DEPENDENT_DIMENSIONS)} of 11 scored dimensions are Planned for AI Phase. "
                "A Launch/Strong Candidate/Test First/Reject recommendation is deliberately withheld "
                "rather than computed from partial evidence — see PRS §17 Research Ethics."
            ),
        )

    # Unreachable in Phase 1 (no path raises completeness above the floor without AI
    # agents), kept so this function is already correct once agents are wired in.
    return CompositeResult(
        research_completeness_pct=completeness,
        overall_score=financial_sub_score,
        recommendation="Needs Review" if completeness < RESEARCH_COMPLETENESS_NEEDS_REVIEW else "Test First",
        risk_level=preliminary_risk_level,
        explanation="Partial AI evidence available; full Decision Engine gating applies.",
    )
