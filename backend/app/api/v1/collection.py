from fastapi import APIRouter, Body, Depends

from app.collection.bridge import profile_to_research_input
from app.collection.field_registry import FIELD_REGISTRY, SECTIONS
from app.collection.schemas import FieldDefinition, ProductProfile, ProductProfileSummary
from app.core.errors import AppError
from app.core.session import get_session_id
from app.models.schemas import ReportResponse
from app.services import profile_service, report_service
from pydantic import BaseModel

router = APIRouter(prefix="/collection", tags=["data-collection"])


class FieldRegistryResponse(BaseModel):
    sections: list[str]
    fields: list[FieldDefinition]


@router.get("/field-registry", response_model=FieldRegistryResponse)
async def get_field_registry() -> FieldRegistryResponse:
    """The single canonical field list — the frontend renders its form
    dynamically from this rather than hardcoding a second copy.
    """
    return FieldRegistryResponse(sections=SECTIONS, fields=list(FIELD_REGISTRY.values()))


@router.post("/preview", response_model=ProductProfile)
async def preview_profile(
    payload: dict = Body(...),
    session_id: str = Depends(get_session_id),
) -> ProductProfile:
    """Stateless — computes classification/validation/quality without saving."""
    return profile_service.preview_profile(session_id, payload)


@router.post("/profiles", response_model=ProductProfile, status_code=201)
async def create_profile(
    payload: dict = Body(...),
    session_id: str = Depends(get_session_id),
) -> ProductProfile:
    return profile_service.create_profile(session_id, payload)


@router.get("/profiles", response_model=list[ProductProfileSummary])
async def list_profiles(session_id: str = Depends(get_session_id)) -> list[ProductProfileSummary]:
    return profile_service.list_profiles(session_id)


@router.get("/profiles/{profile_id}", response_model=ProductProfile)
async def get_profile(profile_id: str) -> ProductProfile:
    profile = profile_service.get_profile(profile_id)
    if profile is None:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)
    return profile


@router.put("/profiles/{profile_id}", response_model=ProductProfile)
async def update_profile(
    profile_id: str,
    payload: dict = Body(...),
    session_id: str = Depends(get_session_id),
) -> ProductProfile:
    updated = profile_service.update_profile(session_id, profile_id, payload)
    if updated is None:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)
    return updated


@router.get("/profiles/{profile_id}/versions", response_model=list[ProductProfileSummary])
async def get_profile_versions(profile_id: str) -> list[ProductProfileSummary]:
    return profile_service.list_versions(profile_id)


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: str) -> None:
    deleted = profile_service.delete_profile(profile_id)
    if not deleted:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)


@router.post("/profiles/{profile_id}/send-to-research", response_model=ReportResponse, status_code=201)
async def send_to_research(
    profile_id: str,
    session_id: str = Depends(get_session_id),
) -> ReportResponse:
    """The DCE's final workflow step: Product Profile -> Research Engine.
    Refuses (422, via AppError raised inside the bridge) rather than running
    research on an incomplete profile.
    """
    profile = profile_service.get_profile(profile_id)
    if profile is None:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)
    research_input = profile_to_research_input(profile)
    return await report_service.create_manual_report(research_input, session_id)
