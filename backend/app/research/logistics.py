"""Weight Class, Material Fragility, and Packaging Type — deterministic lookups.

These feed the Preliminary Logistics Risk read (app/scoring/risk.py) and the
Product DNA fields defined in PRS §3 (Weight class, Material, Fragility).
No AI — fixed thresholds and lookup tables only.
"""

from dataclasses import dataclass

WEIGHT_CLASS_THRESHOLDS_GRAMS = {
    "Light": (0, 150),
    "Medium": (150, 1000),
    "Heavy": (1000, float("inf")),
}

# Fragility lookup keyed on common material keywords found in free-text material input.
MATERIAL_FRAGILITY: dict[str, str] = {
    "glass": "High",
    "ceramic": "High",
    "porcelain": "High",
    "electronic": "High",
    "electronics": "High",
    "plastic": "Low",
    "silicone": "Low",
    "rubber": "Low",
    "fabric": "Low",
    "cotton": "Low",
    "leather": "Low",
    "metal": "Medium",
    "steel": "Medium",
    "aluminium": "Medium",
    "aluminum": "Medium",
    "wood": "Medium",
    "bamboo": "Medium",
    "paper": "Medium",
    "cardboard": "Medium",
}

# (weight_class, fragility) -> suggested packaging type
PACKAGING_LOOKUP: dict[tuple[str, str], str] = {
    ("Light", "High"): "Bubble wrap + rigid small box",
    ("Light", "Medium"): "Padded mailer",
    ("Light", "Low"): "Poly mailer",
    ("Medium", "High"): "Bubble wrap + double-walled box",
    ("Medium", "Medium"): "Corrugated box with void fill",
    ("Medium", "Low"): "Corrugated box",
    ("Heavy", "High"): "Custom foam insert + reinforced crate",
    ("Heavy", "Medium"): "Reinforced corrugated box + edge protectors",
    ("Heavy", "Low"): "Reinforced corrugated box",
}


@dataclass
class LogisticsProfile:
    weight_class: str
    fragility: str
    suggested_packaging: str
    weight_source: str  # "provided" | "unknown"
    material_source: str  # "provided_matched" | "provided_unmatched" | "unknown"


def classify_weight(weight_grams: float | None) -> tuple[str, str]:
    if weight_grams is None:
        return "Unknown", "unknown"
    for label, (low, high) in WEIGHT_CLASS_THRESHOLDS_GRAMS.items():
        if low <= weight_grams < high:
            return label, "provided"
    return "Unknown", "unknown"


def classify_material(material: str | None) -> tuple[str, str]:
    if not material or not material.strip():
        return "Unknown", "unknown"
    material_lower = material.lower()
    for keyword, fragility in MATERIAL_FRAGILITY.items():
        if keyword in material_lower:
            return fragility, "provided_matched"
    return "Medium", "provided_unmatched"  # unrecognized material: assume moderate fragility, never "Low" by default


def build_logistics_profile(weight_grams: float | None, material: str | None) -> LogisticsProfile:
    weight_class, weight_source = classify_weight(weight_grams)
    fragility, material_source = classify_material(material)

    packaging_key = (
        weight_class if weight_class != "Unknown" else "Medium",
        fragility if fragility != "Unknown" else "Medium",
    )
    suggested_packaging = PACKAGING_LOOKUP.get(packaging_key, "Corrugated box with void fill")

    return LogisticsProfile(
        weight_class=weight_class,
        fragility=fragility,
        suggested_packaging=suggested_packaging,
        weight_source=weight_source,
        material_source=material_source,
    )
