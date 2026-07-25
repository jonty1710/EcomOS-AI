"""Validation Engine — deterministic, no AI.

Two severities, never confused:
- ERRORS reject the value outright (field becomes INVALID, excluded from
  calculations that depend on it, counted against validation_pct).
- WARNINGS are advisory — the value is still accepted (field stays FILLED),
  shown to the user, but never blocks anything (Phase 2 brief's explicit
  "warn" vs "reject" rules).
"""

from app.collection.field_registry import FIELD_REGISTRY
from app.collection.schemas import DataType

COMMON_GST_RATES = {0, 0.1, 0.25, 3, 5, 12, 18, 28}
MAX_REASONABLE_WEIGHT_GRAMS = 200_000  # 200kg — beyond this, reject as an impossible single-product weight
HEAVY_WEIGHT_WARNING_THRESHOLD_GRAMS = 50_000  # 50kg — unusual but not impossible, warn only
MAX_REASONABLE_PRICE = 10_000_000  # ₹1 crore — beyond this, warn (not reject; some products genuinely cost this)


def validate_field(key: str, value, all_values: dict) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) for one field. `all_values` is the full raw
    input dict so cross-field rules (selling < buying, GST sanity, etc.) can run.
    """
    errors: list[str] = []
    warnings: list[str] = []
    definition = FIELD_REGISTRY.get(key)
    if definition is None or value is None:
        return errors, warnings

    if definition.data_type == DataType.TEXT and key == "product_name":
        if isinstance(value, str) and not value.strip():
            errors.append("Product name cannot be empty.")

    if definition.data_type == DataType.NUMBER:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{definition.label} must be a number.")
            return errors, warnings
        if definition.min_value is not None and value < definition.min_value:
            errors.append(f"{definition.label} cannot be negative.")
        if definition.max_value is not None and value > definition.max_value:
            errors.append(f"{definition.label} cannot exceed {definition.max_value}{definition.unit or ''}.")

    # --- Field-specific rules named explicitly in the Phase 2 brief -----------
    if key == "weight_grams" and isinstance(value, (int, float)):
        if value > MAX_REASONABLE_WEIGHT_GRAMS:
            errors.append("This weight is not physically plausible for a single product — please check the unit (grams, not kg).")
        elif value > HEAVY_WEIGHT_WARNING_THRESHOLD_GRAMS:
            warnings.append("Unusually heavy for a typical ecommerce product — please verify.")

    if key == "gst_pct" and isinstance(value, (int, float)) and value not in COMMON_GST_RATES:
        warnings.append(f"{value}% is not a standard Indian GST slab — please verify this rate.")

    if key in ("selling_price", "mrp", "buying_price") and isinstance(value, (int, float)):
        if value > MAX_REASONABLE_PRICE:
            warnings.append(f"{definition.label} is unusually high — please double-check.")

    if key == "selling_price" and isinstance(value, (int, float)):
        buying = all_values.get("buying_price")
        if isinstance(buying, (int, float)) and value < buying:
            warnings.append("Selling Price is lower than Buying Price — this will produce a negative gross margin before other costs.")

    if key == "discount_pct" and isinstance(value, (int, float)):
        if value < 0 or value > 100:
            errors.append("Discount % must be between 0 and 100.")

    return errors, warnings


def validate_computed_margin(margin_pct: float | None) -> list[str]:
    """Cross-cutting rule that only makes sense once Margin is actually
    computed (i.e. after calculations.py runs) — kept separate from
    validate_field since Margin isn't a raw input.
    """
    if margin_pct is not None and margin_pct < 0:
        return ["Margin is negative at the entered costs — this product loses money per unit as configured."]
    return []
