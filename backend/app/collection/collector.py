"""The Data Collector Workflow (Phase 2 brief):

    Enter Product Name
       v
    Paste Marketplace URL (optional, parsed only — never fetched)
       v
    Identify all fields
       v
    Mark missing fields
       v
    Request only missing values
       v
    Validate inputs
       v
    Generate Product Profile

No AI. No scraping. Every field either has a real value with a traceable
source, or is explicitly marked missing — never guessed, never defaulted
silently (the one rule this whole module exists to enforce).
"""

import uuid
from datetime import datetime, timezone

from app.collection.calculations import calculate_all
from app.collection.field_registry import (
    CURRENTLY_AUTO_DETECTABLE_KEYS,
    FIELD_REGISTRY,
    REQUIRED_FIELD_KEYS,
)
from app.collection.marketplace_url import detect_marketplace
from app.collection.quality_score import compute_data_quality
from app.collection.schemas import (
    CollectionType,
    EffectiveClassification,
    FieldStatus,
    FieldValue,
    ProductProfile,
)
from app.collection.validation import validate_computed_margin, validate_field
from app.research.category_detection import detect_category


def effective_classification_for(key: str) -> EffectiveClassification:
    definition = FIELD_REGISTRY[key]
    if definition.collection_type == CollectionType.CALCULATED:
        return EffectiveClassification.CALCULATED
    if definition.requires_manual_verification:
        return EffectiveClassification.MANUAL_VERIFICATION_REQUIRED
    if definition.collection_type == CollectionType.AUTO_DETECT:
        return EffectiveClassification.AUTO_DETECT
    return EffectiveClassification.USER_INPUT_REQUIRED


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def collect(
    session_id: str,
    raw_input: dict,
    profile_id: str | None = None,
    version: int = 1,
    previous_version_id: str | None = None,
) -> ProductProfile:
    now = datetime.now(timezone.utc)
    product_name = (raw_input.get("product_name") or "").strip()
    source_url = raw_input.get("source_url")
    detected_marketplace = detect_marketplace(source_url)

    # Step: identify all fields — start from whatever the user/raw_input supplied
    # for every non-calculated registry field (calculated fields are NEVER taken
    # from raw_input, even if present — they are always recomputed).
    raw_values = {
        key: raw_input.get(key)
        for key, definition in FIELD_REGISTRY.items()
        if definition.collection_type != CollectionType.CALCULATED
    }

    # The one real auto-detection available today: Category, via the same
    # deterministic keyword classifier from Phase 1 (no AI, no connector needed).
    category_result = None
    if _is_empty(raw_values.get("category")):
        category_result = detect_category(product_name, None)
        if category_result.category != "Uncategorized":
            raw_values["category"] = category_result.category

    # Step: validate inputs, building a "clean" set (invalid values excluded)
    # that calculations run against — an invalid Buying Price must never leak
    # into Net Cost/Margin/ROI math.
    field_errors: dict[str, list[str]] = {}
    field_warnings: dict[str, list[str]] = {}
    clean_values: dict = {}
    for key, value in raw_values.items():
        if _is_empty(value):
            continue
        errors, warnings = validate_field(key, value, raw_values)
        field_errors[key] = errors
        field_warnings[key] = warnings
        if not errors:
            clean_values[key] = value

    # Step: generate calculated fields from clean inputs only
    calculated = calculate_all(clean_values)
    cost_structure = calculated.pop("cost_structure", {})
    margin_warnings = validate_computed_margin(calculated.get("margin_pct"))

    # Step: build the per-field state for every registry entry
    fields: dict[str, FieldValue] = {}
    for key, definition in FIELD_REGISTRY.items():
        if definition.collection_type == CollectionType.CALCULATED:
            value = calculated.get(key)
            status = FieldStatus.FILLED if value is not None else FieldStatus.MISSING
            warnings = list(margin_warnings) if key == "margin_pct" else []
            fields[key] = FieldValue(
                key=key, value=value, status=status,
                effective_classification=effective_classification_for(key),
                confidence=1.0 if value is not None else None,
                verified=False, source="calculated", errors=[], warnings=warnings,
            )
            continue

        raw_value = raw_values.get(key)
        errors = field_errors.get(key, [])
        warnings = list(field_warnings.get(key, []))

        if _is_empty(raw_value):
            status = FieldStatus.MISSING
            confidence = None
            source = "unavailable"
            verified = False
        elif errors:
            status = FieldStatus.INVALID
            confidence = None
            source = "user"
            verified = False
        else:
            status = FieldStatus.FILLED
            verified = bool(raw_input.get(f"{key}_verified", False))
            if key in CURRENTLY_AUTO_DETECTABLE_KEYS and category_result is not None:
                confidence = category_result.categorization_confidence
                source = "deterministic_detection"
            elif key in CURRENTLY_AUTO_DETECTABLE_KEYS:
                confidence = 1.0  # user overrode the detector directly — treat as authoritative
                source = "user"
            else:
                confidence = 0.85 if not definition.requires_manual_verification else (0.6 if not verified else 0.95)
                source = "user"

        fields[key] = FieldValue(
            key=key, value=raw_value, status=status,
            effective_classification=effective_classification_for(key),
            confidence=confidence, verified=verified if definition.requires_manual_verification else False,
            source=source, errors=errors, warnings=warnings,
        )

    quality = compute_data_quality(fields)
    missing_required = [k for k in REQUIRED_FIELD_KEYS if fields[k].status != FieldStatus.FILLED]
    missing_optional = [
        k for k, fv in fields.items()
        if fv.status == FieldStatus.MISSING and k not in REQUIRED_FIELD_KEYS
        and FIELD_REGISTRY[k].collection_type != CollectionType.CALCULATED
    ]
    any_required_invalid = any(fields[k].status == FieldStatus.INVALID for k in REQUIRED_FIELD_KEYS)
    ready_for_research = len(missing_required) == 0 and not any_required_invalid

    return ProductProfile(
        id=profile_id or str(uuid.uuid4()),
        session_id=session_id,
        product_name=product_name,
        source_url=source_url,
        detected_marketplace=detected_marketplace,
        version=version,
        previous_version_id=previous_version_id,
        fields=fields,
        cost_structure=cost_structure,
        data_quality=quality,
        missing_required=missing_required,
        missing_optional=missing_optional,
        ready_for_research=ready_for_research,
        created_at=now,
        updated_at=now,
    )
