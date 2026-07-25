"""Data Collection Engine — core schemas.

Every field in a Product Profile carries its own classification metadata
(collection_type, requires_manual_verification, confidence, provenance) —
never just a bare value. This is the structural enforcement of the Phase 2
rule: the system must never fabricate a missing value, and every value that
IS present must be traceable to where it came from.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataType(str, Enum):
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"


class CollectionType(str, Enum):
    """HOW a field's value is meant to come into existence. This is the
    underlying mechanism — see `EffectiveClassification` for the user-facing
    3-bucket label the Phase 2 brief asks for, which is derived from this
    plus `requires_manual_verification` (see field_registry.py module docstring
    for why these are modeled as two orthogonal things, not one enum).
    """

    AUTO_DETECT = "auto_detect"
    USER_INPUT = "user_input"
    CALCULATED = "calculated"


class EffectiveClassification(str, Enum):
    """The user-facing bucket (Phase 2 brief's 3 categories, plus Calculated
    as a 4th shown separately since calculated fields are never "requested").
    Computed per-field at collection time, not stored statically — the same
    field can show as Auto Detect once a connector exists, even though today
    it always resolves to User Input Required (see collector.py).
    """

    AUTO_DETECT = "auto_detect"
    USER_INPUT_REQUIRED = "user_input_required"
    MANUAL_VERIFICATION_REQUIRED = "manual_verification_required"
    CALCULATED = "calculated"


class FieldStatus(str, Enum):
    FILLED = "filled"
    MISSING = "missing"
    INVALID = "invalid"


class FieldDefinition(BaseModel):
    """Static registry entry — one per collectible or calculated field.
    See field_registry.py for the full registry. Never instantiated per-product;
    `FieldValue` below is the per-product runtime state.
    """

    key: str
    label: str
    section: str
    data_type: DataType
    collection_type: CollectionType
    requires_manual_verification: bool = False
    required: bool = False
    source_hint: str  # e.g. "Marketplace", "Supplier", "User", "Deterministic"
    help_text: str | None = None
    unit: str | None = None
    enum_options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None


class FieldValue(BaseModel):
    """Per-product runtime state for one field."""

    key: str
    value: Any | None = None
    status: FieldStatus
    effective_classification: EffectiveClassification
    confidence: float | None = None  # 0.0-1.0; None = no basis to assess yet
    verified: bool = False
    source: str  # "user" | "calculated" | "deterministic_detection" | "unavailable"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DataQualityScore(BaseModel):
    """Four distinct numbers, four distinct questions — never collapsed into
    one "quality" figure, same principle as PRS §14's Confidence System.
    """

    completeness_pct: float  # of collectible fields, how many have a value
    validation_pct: float  # of fields with a value, how many are valid
    confidence_pct: float  # of fields with a value, how confidently sourced
    verification_pending_pct: float  # of fields requiring verification, how many still unverified


class ProductProfile(BaseModel):
    """The single source of truth handed to the Research Engine (see
    app/collection/bridge.py). Nothing downstream re-derives these values —
    they either come from here, or they don't exist yet.
    """

    id: str
    session_id: str
    product_name: str
    source_url: str | None = None
    detected_marketplace: str | None = None
    version: int = 1
    previous_version_id: str | None = None
    fields: dict[str, FieldValue]
    cost_structure: dict[str, float] = Field(default_factory=dict)
    data_quality: DataQualityScore
    missing_required: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)
    ready_for_research: bool = False
    created_at: datetime
    updated_at: datetime


class ProductProfileSummary(BaseModel):
    id: str
    product_name: str
    version: int
    completeness_pct: float
    ready_for_research: bool
    created_at: datetime
    updated_at: datetime
