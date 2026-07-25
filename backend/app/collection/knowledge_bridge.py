"""Adapts a DCE `ProductProfile` into a `KnowledgePackSignature`.

Lives in `app.collection`, not `app.knowledge`, on purpose: the Knowledge
Engine is a provider-independent leaf module (PRS §18) that must not depend
on the DCE's schema. This is the one-directional adapter — collection
depends on knowledge, never the other way around — mirroring
`app.collection.bridge` (Product Profile -> Research Engine).
"""

from app.collection.schemas import ProductProfile
from app.knowledge.engine import classify_detected_marketplace, get_knowledge_pack
from app.knowledge.schemas import KnowledgePack, KnowledgePackSignature


def signature_from_profile(profile: ProductProfile) -> KnowledgePackSignature:
    def value_of(key: str):
        field = profile.fields.get(key)
        return field.value if field else None

    category = value_of("category")
    material = value_of("material")
    weight_class = value_of("weight_class")
    fragility = value_of("fragility")
    marketplace, supplier_platform = classify_detected_marketplace(profile.detected_marketplace)

    return KnowledgePackSignature(
        category=category if category else None,
        materials=(material,) if material else (),
        marketplace=marketplace,
        supplier_platform=supplier_platform,
        weight_class=weight_class if weight_class and weight_class != "Unknown" else None,
        fragility=fragility if fragility and fragility != "Unknown" else None,
    )


def knowledge_pack_for_profile(profile: ProductProfile) -> KnowledgePack:
    return get_knowledge_pack(signature_from_profile(profile))
