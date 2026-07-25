from app.db.repository import get_repository
from app.models.schemas import CompareResponse, ReportResponse, ReportSummary
from app.research.orchestrator import run_manual_research
from app.scoring.decision import DIMENSION_LABELS


async def create_manual_report(request_data: dict, session_id: str) -> ReportResponse:
    report = await run_manual_research(request_data)
    get_repository().create_report(report, session_id)
    return report


def get_report(report_id: str) -> ReportResponse | None:
    return get_repository().get_report(report_id)


def list_reports(session_id: str | None, saved_only: bool) -> list[ReportSummary]:
    return get_repository().list_reports(session_id=session_id, saved_only=saved_only)


def delete_report(report_id: str) -> bool:
    return get_repository().delete_report(report_id)


def toggle_favorite(report_id: str) -> ReportResponse | None:
    return get_repository().toggle_favorite(report_id)


def compare_reports(report_ids: list[str]) -> CompareResponse | None:
    reports = []
    for rid in report_ids:
        report = get_report(rid)
        if report is None:
            return None
        reports.append(report)
    return CompareResponse(reports=reports, dimensions=list(DIMENSION_LABELS.values()))
