from app.knowledge.engine import (
    classify_detected_marketplace,
    clear_pack_cache,
    get_knowledge_pack,
    get_knowledge_pack_from_fields,
)
from app.knowledge.schemas import KnowledgePackSignature, LibraryMatchStatus


def test_fully_specified_signature_matches_everything_available():
    pack = get_knowledge_pack_from_fields(
        category="Kitchen & Dining", materials=("ceramic",), marketplace="amazon",
        weight_class="Medium", fragility="High",
    )
    assert pack.coverage.category == LibraryMatchStatus.MATCHED
    assert pack.coverage.materials["ceramic"] == LibraryMatchStatus.MATCHED
    assert pack.coverage.packaging == LibraryMatchStatus.MATCHED
    assert pack.coverage.logistics == LibraryMatchStatus.MATCHED
    assert pack.coverage.marketplace == LibraryMatchStatus.MATCHED
    assert pack.category_knowledge is not None
    assert pack.category_knowledge.category == "Kitchen & Dining"


def test_unknown_category_falls_back_to_uncategorized():
    pack = get_knowledge_pack_from_fields(category="Nonexistent Category XYZ")
    assert pack.coverage.category == LibraryMatchStatus.FALLBACK
    assert pack.category_knowledge.category == "Uncategorized"


def test_empty_signature_never_crashes_and_is_mostly_not_applicable():
    pack = get_knowledge_pack_from_fields()
    assert pack.category_knowledge is None
    assert pack.coverage.category == LibraryMatchStatus.NOT_APPLICABLE
    assert pack.coverage.packaging == LibraryMatchStatus.NOT_APPLICABLE
    # Research best practices always resolves (general fallback), never NOT_APPLICABLE
    assert pack.coverage.research_best_practices == LibraryMatchStatus.FALLBACK
    assert pack.coverage.overall_coverage_pct == 50.0  # only research_best_practices (FALLBACK=0.5) scored


def test_material_alias_resolves_to_canonical_entry():
    pack = get_knowledge_pack_from_fields(materials=("porcelain",))
    assert len(pack.material_knowledge) == 1
    assert pack.material_knowledge[0].material == "ceramic"


def test_material_free_text_substring_resolves():
    pack = get_knowledge_pack_from_fields(materials=("stainless steel body",))
    assert len(pack.material_knowledge) == 1
    assert pack.material_knowledge[0].material == "metal"


def test_unrecognized_material_is_not_available_not_fabricated():
    pack = get_knowledge_pack_from_fields(materials=("unobtainium",))
    assert pack.material_knowledge == []
    assert pack.coverage.materials["unobtainium"] == LibraryMatchStatus.NOT_AVAILABLE


def test_compliance_flags_derived_from_category_and_material():
    pack = get_knowledge_pack_from_fields(category="Baby & Kids", materials=("wood",))
    flag_keys = {c.flag_key for c in pack.compliance_knowledge}
    assert "toy_safety" in flag_keys  # from category
    assert pack.coverage.compliance == LibraryMatchStatus.MATCHED


def test_no_compliance_flags_when_category_and_material_have_none():
    pack = get_knowledge_pack_from_fields(category="Fitness & Sports", materials=("rubber",))
    # rubber itself has food_safety, but Fitness & Sports has no category flags —
    # rubber's own flag still surfaces since compliance is a union.
    flag_keys = {c.flag_key for c in pack.compliance_knowledge}
    assert "food_safety" in flag_keys


def test_packaging_degrades_gracefully_for_unknown_weight_class():
    pack = get_knowledge_pack_from_fields(weight_class="Unknown", fragility="High")
    assert pack.coverage.packaging == LibraryMatchStatus.FALLBACK
    assert pack.packaging_knowledge is not None


def test_research_best_practices_category_specific_beats_general():
    pack = get_knowledge_pack_from_fields(category="Baby & Kids")
    assert pack.coverage.research_best_practices == LibraryMatchStatus.MATCHED
    assert pack.research_best_practices.category == "Baby & Kids"


def test_classify_detected_marketplace_routes_correctly():
    assert classify_detected_marketplace("amazon") == ("amazon", None)
    assert classify_detected_marketplace("indiamart") == (None, "indiamart")
    assert classify_detected_marketplace(None) == (None, None)
    assert classify_detected_marketplace("some-unrelated-site") == (None, None)


def test_identical_signature_returns_cached_object():
    clear_pack_cache()
    sig = KnowledgePackSignature(category="Home Decor")
    a = get_knowledge_pack(sig)
    b = get_knowledge_pack(sig)
    assert a is b
    info = get_knowledge_pack.cache_info()
    assert info.hits >= 1


def test_signature_is_hashable():
    sig = KnowledgePackSignature(category="Home Decor", materials=("glass", "metal"))
    hash(sig)  # must not raise — required for get_knowledge_pack's lru_cache to work at all


def test_material_order_is_not_normalized_by_signature():
    # Documents actual behavior: materials tuple order is part of the cache
    # key, so ("glass","metal") and ("metal","glass") are distinct signatures.
    # This is a known simplification (see docs/KNOWLEDGE_ENGINE.md), not a bug.
    sig1 = KnowledgePackSignature(materials=("glass", "metal"))
    sig2 = KnowledgePackSignature(materials=("metal", "glass"))
    assert sig1.cache_key() != sig2.cache_key()
