"""The ONE translation layer between the Data Collection Engine and the
Phase 1 Research Engine. Per the Phase 2 brief: "The profile becomes the
single source of truth for the Research Engine. Everything downstream reads
from this object."

This does not rewrite the Research Engine (app/research/orchestrator.py) —
that pipeline is already built and tested (Phase 1). Instead it maps a
`ProductProfile`'s field values onto the exact shape
`run_manual_research()` already expects, so the DCE becomes the front door
without touching working code. If a required field is missing or invalid,
this refuses outright rather than defaulting it to zero — the same
"never fabricate" rule the rest of this engine enforces.
"""

from app.collection.field_registry import REQUIRED_FIELD_KEYS
from app.collection.schemas import FieldStatus, ProductProfile
from app.core.errors import AppError

# Maps DCE field keys -> ManualResearchRequest field keys where they differ
# (most keys are identical by design). category -> category_hint since the
# Research Engine's own category detector (Stage 3 of its pipeline) treats a
# hint as authoritative user input, and the DCE has often already resolved it.
_KEY_MAP = {"category": "category_hint"}

_PASSTHROUGH_KEYS = [
    "product_name", "selling_price", "buying_price", "shipping_cost",
    "packaging_cost", "marketplace_fee_pct", "ad_cost", "gst_pct",
    "closing_fee", "weight_grams", "material", "supplier_name",
    "supplier_notes", "competition_notes", "review_notes", "category",
]


def profile_to_research_input(profile: ProductProfile) -> dict:
    if not profile.ready_for_research:
        missing = ", ".join(profile.missing_required) or "one or more required fields"
        raise AppError(
            "PROFILE_INCOMPLETE",
            f"This Product Profile isn't ready for research yet — still missing: {missing}. "
            "Complete the Data Collection form before sending it to the Research Engine.",
            422,
        )

    invalid = [k for k in REQUIRED_FIELD_KEYS if profile.fields[k].status == FieldStatus.INVALID]
    if invalid:
        raise AppError(
            "PROFILE_INVALID",
            f"This Product Profile has invalid required fields: {', '.join(invalid)}. Fix them before sending to research.",
            422,
        )

    # Omit fields with no value entirely, rather than passing an explicit
    # None — the Research Engine's agents use `mi.get(key, default)`, which
    # only falls back to `default` when the key is ABSENT. Passing
    # `{"marketplace_fee_pct": None}` would silently break that fallback and
    # crash downstream arithmetic instead of defaulting to 0.
    payload: dict = {}
    for key in _PASSTHROUGH_KEYS:
        field_value = profile.fields.get(key)
        if field_value is None or field_value.value is None:
            continue
        target_key = _KEY_MAP.get(key, key)
        payload[target_key] = field_value.value

    # Not a FieldValue — a top-level ProductProfile attribute (parsed from
    # source_url, never fetched, PRS §17). Passed through so the Research
    # Engine's Knowledge Engine lookup (app/research/orchestrator.py) can use
    # it; omitted entirely when absent, same "never pass an explicit None"
    # rule as everything else in this function.
    if profile.detected_marketplace:
        payload["detected_marketplace"] = profile.detected_marketplace

    return payload
