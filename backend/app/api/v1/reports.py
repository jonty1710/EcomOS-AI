from fastapi import APIRouter, Depends, Query

from app.core.errors import AppError
from app.core.session import get_session_id
from app.models.schemas import CompareResponse, ReportResponse, ReportSummary
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    saved: bool = Query(default=False),
    session_id: str = Depends(get_session_id),
) -> list[ReportSummary]:
    return report_service.list_reports(session_id=session_id, saved_only=saved)


@router.get("/compare", response_model=CompareResponse)
async def compare_reports(ids: str = Query(..., description="Comma-separated report ids, 2-5")) -> CompareResponse:
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not (2 <= len(id_list) <= 5):
        raise AppError("VALIDATION_ERROR", "Provide between 2 and 5 report ids to compare.", 422)
    result = report_service.compare_reports(id_list)
    if result is None:
        raise AppError("NOT_FOUND", "One or more reports could not be found.", 404)
    return result


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str) -> ReportResponse:
    report = report_service.get_report(report_id)
    if report is None:
        raise AppError("NOT_FOUND", "This report could not be found.", 404)
    return report


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: str) -> None:
    deleted = report_service.delete_report(report_id)
    if not deleted:
        raise AppError("NOT_FOUND", "This report could not be found.", 404)


@router.post("/{report_id}/favorite", response_model=ReportResponse)
async def toggle_favorite(report_id: str) -> ReportResponse:
    report = report_service.toggle_favorite(report_id)
    if report is None:
        raise AppError("NOT_FOUND", "This report could not be found.", 404)
    return report
