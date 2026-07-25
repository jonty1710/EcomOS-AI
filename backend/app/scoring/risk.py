"""Preliminary Logistics Risk — deterministic, evidence-limited subset of the
Unified Risk Score (PRS §10). Phase 1 has no AI evidence for Compliance,
Trademark, Competition or Supplier risk, so this computes only the slice that
manual inputs actually support: fragility, weight class, and return/RTO cost
ratios. It is explicitly a *preliminary* read, never presented as the full
11-risk composite PRS §10 describes.
"""

from dataclasses import dataclass

FRAGILITY_RISK_POINTS = {"Low": 10, "Medium": 40, "High": 75, "Unknown": 50}
WEIGHT_CLASS_RISK_POINTS = {"Light": 10, "Medium": 30, "Heavy": 55, "Unknown": 35}


@dataclass
class PreliminaryRiskResult:
    risk_score: float  # 0-100, higher = riskier
    risk_level: str  # Low | Medium | High
    fragility_component: float
    weight_component: float
    rto_ratio_component: float
    return_ratio_component: float
    basis: str


def compute_preliminary_risk(
    fragility: str,
    weight_class: str,
    selling_price: float,
    return_cost: float,
    rto_cost: float,
) -> PreliminaryRiskResult:
    fragility_pts = FRAGILITY_RISK_POINTS.get(fragility, 50)
    weight_pts = WEIGHT_CLASS_RISK_POINTS.get(weight_class, 35)

    rto_ratio = (rto_cost / selling_price) if selling_price > 0 else 0
    return_ratio = (return_cost / selling_price) if selling_price > 0 else 0

    rto_pts = min(100.0, rto_ratio * 400)  # ratio 0.25 -> 100 pts (saturates)
    return_pts = min(100.0, return_ratio * 500)  # ratio 0.20 -> 100 pts (saturates)

    risk_score = (
        fragility_pts * 0.35
        + weight_pts * 0.20
        + rto_pts * 0.25
        + return_pts * 0.20
    )
    risk_score = round(min(100.0, max(0.0, risk_score)), 1)

    if risk_score < 30:
        risk_level = "Low"
    elif risk_score < 60:
        risk_level = "Medium"
    else:
        risk_level = "High"

    return PreliminaryRiskResult(
        risk_score=risk_score,
        risk_level=risk_level,
        fragility_component=round(fragility_pts * 0.35, 1),
        weight_component=round(weight_pts * 0.20, 1),
        rto_ratio_component=round(rto_pts * 0.25, 1),
        return_ratio_component=round(return_pts * 0.20, 1),
        basis="fragility + weight class + return/RTO cost ratios only — "
              "Compliance, Trademark, Competition and Supplier risk require AI "
              "evidence not yet available (PRS §10).",
    )
