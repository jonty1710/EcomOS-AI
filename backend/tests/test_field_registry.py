from app.collection.field_registry import (
    FIELD_REGISTRY,
    REQUIRED_FIELD_KEYS,
    SECTIONS,
)
from app.collection.schemas import CollectionType


def test_registry_keys_are_unique_and_nonempty():
    keys = list(FIELD_REGISTRY.keys())
    assert len(keys) == len(set(keys))
    assert len(keys) > 0


def test_every_field_belongs_to_a_known_section():
    for definition in FIELD_REGISTRY.values():
        assert definition.section in SECTIONS


def test_required_fields_match_the_brief_worked_example():
    # Phase 2 brief's own "Required Inputs" example: Buying Price, Shipping Cost,
    # Packaging Cost, Supplier Name, Weight — plus the two obvious fundamentals.
    assert set(REQUIRED_FIELD_KEYS) == {
        "product_name", "selling_price", "buying_price", "shipping_cost",
        "packaging_cost", "weight_grams", "supplier_name",
    }


def test_calculated_fields_are_never_required():
    for definition in FIELD_REGISTRY.values():
        if definition.collection_type == CollectionType.CALCULATED:
            assert definition.required is False


def test_fragility_and_packaging_are_calculated_not_asked():
    assert FIELD_REGISTRY["fragility"].collection_type == CollectionType.CALCULATED
    assert FIELD_REGISTRY["packaging_type"].collection_type == CollectionType.CALCULATED


def test_buying_price_requires_manual_verification():
    assert FIELD_REGISTRY["buying_price"].requires_manual_verification is True
