"""Shared Pydantic schemas.

`ModuleSection` is the Phase 1 stand-in for the SRS's `ModuleResponse` envelope
(docs/SRS.md §4). It is deliberately the same shape every agent — deterministic
today, AI-driven later — will return, so the AI phase is a new `status`/`data`
producer plugged into an existing contract, not a new contract.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.knowledge.schemas import KnowledgePack


class ModuleStatus(str, Enum):
    COMPLETED = "completed"
    UNSCORED_INSUFFICIENT_EVIDENCE = "unscored_insufficient_evidence"
    PLANNED_FOR_AI_PHASE = "planned_for_ai_phase"
    FAILED = "failed"


class SourceRef(BaseModel):
    type: Literal["manual", "deterministic", "connector", "web_search", "llm_reasoning"]
    name: str
    url: str | None = None
    retrieved_at: datetime | None = None


class ModuleSection(BaseModel):
    """One row of a report — one per research dimension (SRS §11 / PRS §6-11)."""

    agent_type: str
    label: str
    status: ModuleStatus
    data: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    reasoning: str | None = None
    confidence_score: float | None = None
    evidence_score: float | None = None
    sub_score: float | None = None
    sources: list[SourceRef] = Field(default_factory=list)
    requires_manual_verification: bool = False
    weight_in_decision_engine: float = 0.0
    unavailable_reason: str | None = None


# ---------------------------------------------------------------------------
# Manual Research Workflow input (SRS §9 POST /reports shape, extended per the
# Phase 1 prompt's required manual fields)
# ---------------------------------------------------------------------------


class ManualResearchRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    category_hint: str | None = None

    # Financial inputs (SRS §9 profit-calculator contract)
    selling_price: float = Field(gt=0)
    buying_price: float = Field(ge=0)
    shipping_cost: float = Field(ge=0, default=0)
    packaging_cost: float = Field(ge=0, default=0)
    marketplace_fee_pct: float = Field(ge=0, le=100, default=0)
    ad_cost: float = Field(ge=0, default=0)
    gst_pct: float = Field(ge=0, le=100, default=18)
    return_cost: float = Field(ge=0, default=0)
    rto_cost: float = Field(ge=0, default=0)
    closing_fee: float = Field(ge=0, default=0)

    # Logistics / Product DNA inputs (PRS §3)
    weight_grams: float | None = Field(default=None, ge=0)
    material: str | None = None
    supplier_name: str | None = None
    supplier_notes: str | None = None

    # Free-text manual notes — never scored by AI in Phase 1, stored verbatim
    competition_notes: str | None = None
    review_notes: str | None = None

    @field_validator("product_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("product_name cannot be blank")
        return v


class ReportResponse(BaseModel):
    id: str
    product_name: str
    category: str | None
    status: str
    research_mode: str
    overall_score: float | None
    risk_level: str | None
    recommendation: str | None
    is_saved: bool
    sections: list[ModuleSection]
    manual_verification_checklist: list[str]
    research_completeness_pct: float
    recommendation_explanation: str
    knowledge_pack: KnowledgePack | None = None
    created_at: datetime
    completed_at: datetime | None


class ReportSummary(BaseModel):
    id: str
    product_name: str
    category: str | None
    status: str
    overall_score: float | None
    recommendation: str | None
    is_saved: bool
    created_at: datetime


class CompareResponse(BaseModel):
    reports: list[ReportResponse]
    dimensions: list[str]
