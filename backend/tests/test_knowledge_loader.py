from app.knowledge import loader
from app.knowledge.schemas import (
    CategoryKnowledge,
    ComplianceKnowledge,
    LogisticsKnowledge,
    MarketplaceKnowledge,
    MaterialKnowledge,
    PackagingKnowledge,
    ResearchBestPractices,
    SupplierIntelligenceKnowledge,
)


def test_categories_load_and_include_uncategorized_fallback():
    categories = loader.load_categories()
    assert "Uncategorized" in categories
    assert all(isinstance(v, CategoryKnowledge) for v in categories.values())
    # Must match Phase 1's real taxonomy exactly (app/research/category_detection.py)
    assert "Kitchen & Dining" in categories
    assert "Electronics Accessories" in categories


def test_materials_load_with_aliases():
    materials = loader.load_materials()
    assert all(isinstance(v, MaterialKnowledge) for v in materials.values())
    assert "porcelain" in materials["ceramic"].aliases
    assert "steel" in materials["metal"].aliases


def test_packaging_covers_all_nine_weight_fragility_combinations():
    packaging = loader.load_packaging()
    assert all(isinstance(v, PackagingKnowledge) for v in packaging.values())
    weight_classes = ["Light", "Medium", "Heavy"]
    fragilities = ["Low", "Medium", "High"]
    for wc in weight_classes:
        for fr in fragilities:
            assert f"{wc}_{fr}" in packaging


def test_logistics_covers_all_weight_classes():
    logistics = loader.load_logistics()
    assert all(isinstance(v, LogisticsKnowledge) for v in logistics.values())
    assert set(logistics.keys()) == {"Light", "Medium", "Heavy"}


def test_marketplace_rules_load():
    rules = loader.load_marketplace_rules()
    assert all(isinstance(v, MarketplaceKnowledge) for v in rules.values())
    assert {"amazon", "flipkart", "meesho"}.issubset(rules.keys())


def test_supplier_intelligence_loads():
    suppliers = loader.load_supplier_intelligence()
    assert all(isinstance(v, SupplierIntelligenceKnowledge) for v in suppliers.values())
    assert {"indiamart", "tradeindia"}.issubset(suppliers.keys())


def test_compliance_loads():
    compliance = loader.load_compliance()
    assert all(isinstance(v, ComplianceKnowledge) for v in compliance.values())
    assert "food_safety" in compliance


def test_research_best_practices_has_general_fallback():
    practices = loader.load_research_best_practices()
    assert all(isinstance(v, ResearchBestPractices) for v in practices.values())
    assert "general" in practices
    assert practices["general"].category is None


def test_loaders_are_cached_singletons():
    a = loader.load_categories()
    b = loader.load_categories()
    assert a is b  # same object — lru_cache returned the cached instance, not a fresh parse


def test_clear_all_caches_forces_reload():
    a = loader.load_categories()
    loader.clear_all_caches()
    b = loader.load_categories()
    assert a is not b
    assert a == b  # different instances, same content
