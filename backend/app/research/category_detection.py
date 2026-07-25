"""Category Detection — PRS §2.2 Stage 3.

Deterministic keyword-taxonomy match. No AI. A product name is tokenized and
matched against a fixed category keyword table; the category with the most
keyword hits wins. Ties and zero-hit cases fall back to "Uncategorized" with a
low categorization_confidence, per PRS §2.2: "no category match clears a
minimum confidence bar -> the product proceeds as Uncategorized, a visible,
penalized state."
"""

import re
from dataclasses import dataclass, field

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Kitchen & Dining": ["kitchen", "cookware", "utensil", "container", "bottle", "mug", "cutlery", "storage jar"],
    "Home Organization": ["organizer", "organiser", "storage", "drawer", "closet", "rack", "shelf", "basket"],
    "Fitness & Sports": ["yoga", "gym", "fitness", "dumbbell", "resistance band", "mat", "sports", "exercise"],
    "Electronics Accessories": ["phone holder", "charger", "cable", "earphone", "case", "stand", "mount", "power bank"],
    "Apparel & Fashion": ["shirt", "dress", "kurta", "jacket", "shoes", "sandals", "bag", "wallet", "belt"],
    "Beauty & Personal Care": ["skincare", "makeup", "shampoo", "beauty", "cream", "lotion", "brush", "grooming"],
    "Baby & Kids": ["baby", "infant", "toddler", "kids", "toy", "stroller", "diaper"],
    "Pet Supplies": ["pet", "dog", "cat", "leash", "pet bed", "pet bowl"],
    "Stationery & Office": ["notebook", "pen", "stationery", "office", "planner", "desk"],
    "Outdoor & Garden": ["outdoor", "garden", "camping", "patio", "plant pot", "grill"],
    "Home Decor": ["decor", "candle", "frame", "curtain", "cushion", "vase", "lamp"],
}


@dataclass
class CategoryDetectionResult:
    category: str
    sub_category: str | None
    categorization_confidence: float
    matched_keywords: list[str] = field(default_factory=list)


def detect_category(product_name: str, category_hint: str | None = None) -> CategoryDetectionResult:
    if category_hint and category_hint.strip():
        hint = category_hint.strip()
        # Hint is treated as authoritative user input (Verified-tier, PRS §17) if it
        # matches a known taxonomy entry; otherwise carried through as a custom category.
        for category in CATEGORY_KEYWORDS:
            if hint.lower() == category.lower():
                return CategoryDetectionResult(category=category, sub_category=None, categorization_confidence=1.0)
        return CategoryDetectionResult(category=hint, sub_category=None, categorization_confidence=0.9)

    name_lower = re.sub(r"[^a-z0-9\s]", " ", product_name.lower())
    tokens = set(name_lower.split())

    best_category: str | None = None
    best_score = 0
    best_hits: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in name_lower or any(tok == kw for tok in tokens)]
        if len(hits) > best_score:
            best_score = len(hits)
            best_category = category
            best_hits = hits

    if best_category is None or best_score == 0:
        return CategoryDetectionResult(
            category="Uncategorized",
            sub_category=None,
            categorization_confidence=0.1,
            matched_keywords=[],
        )

    # Confidence scales with keyword hit density, capped — a single generic keyword
    # match should never look as certain as a multi-keyword match.
    confidence = min(0.95, 0.5 + 0.15 * best_score)
    return CategoryDetectionResult(
        category=best_category,
        sub_category=None,
        categorization_confidence=confidence,
        matched_keywords=best_hits,
    )
