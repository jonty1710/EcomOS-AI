"""Knowledge Engine — the deterministic lookup interface.

Public entry point: `get_knowledge_pack(signature)`. Same signature in,
same `KnowledgePack` out, always — no randomness, no network access, no
provider/model dependency of any kind (this module imports nothing from
app.ai or app.connectors). This is what makes it safe for a future AI
provider to treat as trusted grounding context: its content is fixed and
auditable, not generated per-call.

Never fabricates: every lookup either finds a real entry (MATCHED), falls
back to an explicitly-generic entry (FALLBACK), or comes back empty
(NOT_AVAILABLE / NOT_APPLICABLE) — see schemas.py `LibraryMatchStatus`.
Nothing in this file invents a plausible-sounding value for a key that
isn't actually in the seed data.

Caching strategy, tier 2 (assembled packs): `get_knowledge_pack` is wrapped
in `functools.lru_cache` — building a pack is pure computation over data
that's already in memory (tier 1, see loader.py), so caching the assembly
itself mainly saves repeated Pydantic construction for popular
category/material/marketplace combinations, not I/O. `maxsize=256` comfortably
covers every realistic signature combination (12 categories x 10 materials x
a handful of marketplace/weight/fragility combinations is well under that).
"""

from datetime import datetime, timezone
from functools import lru_cache

from app.knowledge.loader import (
    load_categories,
    load_compliance,
    load_logistics,
    load_marketplace_rules,
    load_materials,
    load_packaging,
    load_research_best_practices,
    load_supplier_intelligence,
)
from app.knowledge.schemas import (
    CategoryKnowledge,
    ComplianceKnowledge,
    KnowledgePack,
    KnowledgePackCoverage,
    KnowledgePackSignature,
    LibraryMatchStatus,
    LogisticsKnowledge,
    MarketplaceKnowledge,
    MaterialKnowledge,
    PackagingKnowledge,
    ResearchBestPractices,
    SupplierIntelligenceKnowledge,
)

_UNCATEGORIZED_KEY = "Uncategorized"
_GENERAL_BEST_PRACTICES_KEY = "general"


def _lookup_category(category: str | None) -> tuple[CategoryKnowledge | None, LibraryMatchStatus]:
    if category is None:
        return None, LibraryMatchStatus.NOT_APPLICABLE
    library = load_categories()
    if category in library:
        return library[category], LibraryMatchStatus.MATCHED
    if _UNCATEGORIZED_KEY in library:
        return library[_UNCATEGORIZED_KEY], LibraryMatchStatus.FALLBACK
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_material(material_text: str | None) -> tuple[MaterialKnowledge | None, LibraryMatchStatus]:
    """Same substring-normalization approach as
    app/research/logistics.py::classify_material, applied against the
    Knowledge Engine's richer entries (each of which lists its own aliases).
    """
    if material_text is None or not material_text.strip():
        return None, LibraryMatchStatus.NOT_APPLICABLE
    text_lower = material_text.lower()
    library = load_materials()
    for entry in library.values():
        candidates = [entry.material, *entry.aliases]
        if any(candidate in text_lower for candidate in candidates):
            return entry, LibraryMatchStatus.MATCHED
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_packaging(weight_class: str | None, fragility: str | None) -> tuple[PackagingKnowledge | None, LibraryMatchStatus]:
    if weight_class is None and fragility is None:
        return None, LibraryMatchStatus.NOT_APPLICABLE
    library = load_packaging()
    wc = weight_class or "Unknown"
    fr = fragility or "Unknown"
    exact_key = f"{wc}_{fr}"
    if exact_key in library:
        return library[exact_key], LibraryMatchStatus.MATCHED
    # Same degradation Phase 2 already applies (research/logistics.py PACKAGING_LOOKUP):
    # substitute "Unknown" with the middle-of-the-road "Medium" bucket rather than guessing.
    fallback_key = f"{wc if wc != 'Unknown' else 'Medium'}_{fr if fr != 'Unknown' else 'Medium'}"
    if fallback_key in library:
        return library[fallback_key], LibraryMatchStatus.FALLBACK
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_logistics(weight_class: str | None) -> tuple[LogisticsKnowledge | None, LibraryMatchStatus]:
    if weight_class is None:
        return None, LibraryMatchStatus.NOT_APPLICABLE
    library = load_logistics()
    if weight_class in library:
        return library[weight_class], LibraryMatchStatus.MATCHED
    if "Medium" in library:
        return library["Medium"], LibraryMatchStatus.FALLBACK
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_marketplace(marketplace: str | None) -> tuple[MarketplaceKnowledge | None, LibraryMatchStatus]:
    if marketplace is None:
        return None, LibraryMatchStatus.NOT_APPLICABLE
    library = load_marketplace_rules()
    if marketplace in library:
        return library[marketplace], LibraryMatchStatus.MATCHED
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_supplier(platform: str | None) -> tuple[SupplierIntelligenceKnowledge | None, LibraryMatchStatus]:
    if platform is None:
        return None, LibraryMatchStatus.NOT_APPLICABLE
    library = load_supplier_intelligence()
    if platform in library:
        return library[platform], LibraryMatchStatus.MATCHED
    return None, LibraryMatchStatus.NOT_AVAILABLE


def _lookup_compliance(flag_keys: list[str]) -> tuple[list[ComplianceKnowledge], LibraryMatchStatus]:
    if not flag_keys:
        return [], LibraryMatchStatus.NOT_APPLICABLE
    library = load_compliance()
    found = [library[k] for k in dict.fromkeys(flag_keys) if k in library]  # de-dup, preserve order
    if not found:
        return [], LibraryMatchStatus.NOT_AVAILABLE
    return found, LibraryMatchStatus.MATCHED


def _lookup_research_best_practices(category: str | None) -> tuple[ResearchBestPractices, LibraryMatchStatus]:
    library = load_research_best_practices()
    if category is not None and category in library:
        return library[category], LibraryMatchStatus.MATCHED
    general = library.get(_GENERAL_BEST_PRACTICES_KEY)
    if general is not None:
        return general, LibraryMatchStatus.FALLBACK
    # Should be unreachable — the general entry always ships in the seed data —
    # but never raise out of a knowledge lookup; degrade to an empty, honest entry.
    return ResearchBestPractices(category=None, checklist=[], evidence_priority_notes=[], common_pitfalls=[]), LibraryMatchStatus.NOT_AVAILABLE


_STATUS_CREDIT = {
    LibraryMatchStatus.MATCHED: 1.0,
    LibraryMatchStatus.FALLBACK: 0.5,
    LibraryMatchStatus.NOT_AVAILABLE: 0.0,
}


def _compute_coverage(
    category_status: LibraryMatchStatus,
    material_statuses: dict[str, LibraryMatchStatus],
    packaging_status: LibraryMatchStatus,
    logistics_status: LibraryMatchStatus,
    marketplace_status: LibraryMatchStatus,
    supplier_status: LibraryMatchStatus,
    compliance_status: LibraryMatchStatus,
    research_status: LibraryMatchStatus,
) -> KnowledgePackCoverage:
    scored = [
        s for s in (
            category_status, packaging_status, logistics_status,
            marketplace_status, supplier_status, compliance_status, research_status,
        )
        if s != LibraryMatchStatus.NOT_APPLICABLE
    ]
    scored.extend(s for s in material_statuses.values() if s != LibraryMatchStatus.NOT_APPLICABLE)

    overall_pct = round(sum(_STATUS_CREDIT[s] for s in scored) / len(scored) * 100, 1) if scored else 0.0

    return KnowledgePackCoverage(
        category=category_status,
        materials=material_statuses,
        packaging=packaging_status,
        logistics=logistics_status,
        marketplace=marketplace_status,
        supplier=supplier_status,
        compliance=compliance_status,
        research_best_practices=research_status,
        overall_coverage_pct=overall_pct,
    )


def _build_knowledge_pack(signature: KnowledgePackSignature) -> KnowledgePack:
    category_knowledge, category_status = _lookup_category(signature.category)

    material_knowledge: list[MaterialKnowledge] = []
    material_statuses: dict[str, LibraryMatchStatus] = {}
    for material_text in signature.materials:
        entry, status = _lookup_material(material_text)
        material_statuses[material_text] = status
        if entry is not None:
            material_knowledge.append(entry)

    packaging_knowledge, packaging_status = _lookup_packaging(signature.weight_class, signature.fragility)
    logistics_knowledge, logistics_status = _lookup_logistics(signature.weight_class)
    marketplace_knowledge, marketplace_status = _lookup_marketplace(signature.marketplace)
    supplier_knowledge, supplier_status = _lookup_supplier(signature.supplier_platform)

    # Compliance flags are DERIVED, not requested directly — union of whatever
    # the matched category and material entries say is relevant (never asked
    # of the caller, same "don't fabricate an input we don't have" discipline).
    derived_flags: list[str] = []
    if category_knowledge is not None:
        derived_flags.extend(category_knowledge.common_compliance_flags)
    for m in material_knowledge:
        derived_flags.extend(m.common_compliance_flags)
    compliance_knowledge, compliance_status = _lookup_compliance(derived_flags)

    research_best_practices, research_status = _lookup_research_best_practices(signature.category)

    coverage = _compute_coverage(
        category_status, material_statuses, packaging_status, logistics_status,
        marketplace_status, supplier_status, compliance_status, research_status,
    )

    return KnowledgePack(
        signature=signature,
        category_knowledge=category_knowledge,
        material_knowledge=material_knowledge,
        packaging_knowledge=packaging_knowledge,
        logistics_knowledge=logistics_knowledge,
        marketplace_knowledge=marketplace_knowledge,
        supplier_knowledge=supplier_knowledge,
        compliance_knowledge=compliance_knowledge,
        research_best_practices=research_best_practices,
        coverage=coverage,
        generated_at=datetime.now(timezone.utc),
    )


@lru_cache(maxsize=256)
def get_knowledge_pack(signature: KnowledgePackSignature) -> KnowledgePack:
    """The Knowledge Engine's public interface. Pass a `KnowledgePackSignature`
    (category, materials, marketplace, supplier_platform, weight_class,
    fragility — whatever subset is known); get back a complete `KnowledgePack`.
    Absent fields are honest `NOT_APPLICABLE` gaps, never guessed.
    """
    return _build_knowledge_pack(signature)


def classify_detected_marketplace(value: str | None) -> tuple[str | None, str | None]:
    """Routes a raw `detected_marketplace` string (from
    app/collection/marketplace_url.py — amazon/flipkart/meesho/indiamart/
    tradeindia all come from the same domain-parsing table) into the correct
    signature slot: (marketplace, supplier_platform). The two knowledge
    libraries have disjoint key spaces — a sell-side marketplace and a
    sourcing platform are different kinds of knowledge — so a caller must
    not pass "indiamart" into the marketplace slot or it will silently miss.
    """
    if value is None:
        return None, None
    if value in load_marketplace_rules():
        return value, None
    if value in load_supplier_intelligence():
        return None, value
    return None, None


def get_knowledge_pack_from_fields(
    category: str | None = None,
    materials: tuple[str, ...] = (),
    marketplace: str | None = None,
    supplier_platform: str | None = None,
    weight_class: str | None = None,
    fragility: str | None = None,
) -> KnowledgePack:
    """Convenience wrapper over `get_knowledge_pack` for callers (like the
    Research Engine orchestrator) that have raw fields rather than an
    already-built signature object.
    """
    signature = KnowledgePackSignature(
        category=category, materials=materials, marketplace=marketplace,
        supplier_platform=supplier_platform, weight_class=weight_class, fragility=fragility,
    )
    return get_knowledge_pack(signature)


def clear_pack_cache() -> None:
    """Test/dev-only: clears the tier-2 (assembled-pack) cache. See
    app/knowledge/loader.py::clear_all_caches for the tier-1 (seed data) cache.
    """
    get_knowledge_pack.cache_clear()
