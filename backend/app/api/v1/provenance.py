from fastapi import APIRouter, Body

from app.core.errors import AppError
from app.provenance.schemas import DataLineageReport, ProvenanceEventRecord
from app.services import provenance_service

router = APIRouter(prefix="/provenance", tags=["provenance"])


@router.get("/profiles/{profile_id}/lineage", response_model=DataLineageReport)
async def get_lineage(profile_id: str) -> DataLineageReport:
    """The Data Lineage Viewer's backend — every field's source, reliability,
    confidence, verification status, expiry, and audit trail in one report.
    """
    report = provenance_service.get_lineage_report(profile_id)
    if report is None:
        raise AppError("NOT_FOUND", "This product profile could not be found.", 404)
    return report


@router.post("/profiles/{profile_id}/fields/{field_key}/reject", response_model=ProvenanceEventRecord, status_code=201)
async def reject_field(profile_id: str, field_key: str, note: str | None = Body(default=None, embed=True)) -> ProvenanceEventRecord:
    event = provenance_service.reject_field(profile_id, field_key, note)
    if event is None:
        raise AppError("NOT_FOUND", "This product profile or field could not be found.", 404)
    return event


@router.post("/profiles/{profile_id}/fields/{field_key}/clear-rejection", response_model=ProvenanceEventRecord, status_code=201)
async def clear_rejection(profile_id: str, field_key: str) -> ProvenanceEventRecord:
    event = provenance_service.clear_rejection(profile_id, field_key)
    if event is None:
        raise AppError("NOT_FOUND", "This product profile or field could not be found.", 404)
    return event


@router.post("/profiles/{profile_id}/fields/{field_key}/request-refresh", response_model=ProvenanceEventRecord, status_code=201)
async def request_refresh(profile_id: str, field_key: str) -> ProvenanceEventRecord:
    event = provenance_service.request_refresh(profile_id, field_key)
    if event is None:
        raise AppError("NOT_FOUND", "This product profile or field could not be found.", 404)
    return event
