from fastapi import APIRouter, Depends

from app.core.session import get_session_id
from app.models.schemas import ManualResearchRequest, ReportResponse
from app.services.report_service import create_manual_report

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/manual", response_model=ReportResponse, status_code=201)
async def submit_manual_research(
    payload: ManualResearchRequest,
    session_id: str = Depends(get_session_id),
) -> ReportResponse:
    """Manual Research Workflow (Phase 1 brief §11). Runs the deterministic
    engine only — every AI-dependent section returns status=planned_for_ai_phase.
    """
    return await create_manual_report(payload.model_dump(), session_id)
