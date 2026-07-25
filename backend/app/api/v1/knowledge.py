from fastapi import APIRouter, Query

from app.collection.knowledge_bridge import knowledge_pack_for_profile
from app.core.errors import AppError
from app.knowledge.engine import classify_detected_marketplace, get_knowledge_pack_from_fields
from app.knowledge.schemas import KnowledgePack
from app.services import profile_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/pack/preview", response_model=KnowledgePack)
async def preview_knowledge_pack(
    category: str | None = Query(default=None),
    material: str | None = Query(default=None),
    marketplace: str | None = Query(default=None, description="e.g. amazon, flipkart, meesho, indiamart, tradeindia"),
    weight_class: str | None = Query(default=None, description="Light | Medium | Heavy"),
    fragility: str | None = Query(default=None, description="Low | Medium | High"),
) -> KnowledgePack:
    """Ad-hoc inspection endpoint — no Product Profile required. Useful for
    exploring what the Knowledge Engine knows about a given combination
    before/without running Data Collection.
    """
    resolved_marketplace, supplier_platform = classify_detected_marketplace(marketplace)
    return get_knowledge_pack_from_fields(
        category=category,
        materials=(material,) if material else (),
        marketplace=resolved_marketplace,
        supplier_platform=supplier_platform,
        weight_class=weight_class,
        fragility=fragility,
    )


@router.get("/pack/for-profile/{profile_id}", response_model=KnowledgePack)
async def get_knowledge_pack_for_profile(profile_id: str) -> KnowledgePack:
    """The same Knowledge Pack the Research Engine will attach to this
    profile's report — computed here for inspection before actually sending
    the profile to research.
    """
    profile = profile_service.get_profile(profile_id)
    if profile is None:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)
    return knowledge_pack_for_profile(profile)
