"""Report persistence.

Two implementations of the same `ReportRepository` protocol:

- `SupabaseReportRepository` — the real, production-shape backend (SRS §3 schema),
  used automatically when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are configured.
- `JsonFileReportRepository` — a local-file fallback so the app boots and is fully
  usable with zero external dependencies when those env vars are absent. This is a
  Phase 1 development convenience, not a production data store — it is not part of
  the approved SRS schema and must not be relied on beyond local dev/testing.

`get_repository()` is the only thing callers should import — it picks the
implementation from `Settings.supabase_configured`, so swapping to a real
Supabase project is an env var change, never a code change.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings
from app.models.schemas import ModuleSection, ReportResponse, ReportSummary
from app.scoring.decision import DIMENSION_LABELS, DIMENSION_WEIGHTS

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_FILE = DATA_DIR / "db.json"


class ReportRepository(Protocol):
    def create_report(self, report: ReportResponse, session_id: str) -> None: ...
    def get_report(self, report_id: str) -> ReportResponse | None: ...
    def list_reports(self, session_id: str | None = None, saved_only: bool = False) -> list[ReportSummary]: ...
    def delete_report(self, report_id: str) -> bool: ...
    def toggle_favorite(self, report_id: str) -> ReportResponse | None: ...


class JsonFileReportRepository:
    """Local dev/testing fallback — NOT the approved production data store.
    See database/schema.sql for the real schema this must eventually match.
    """

    _lock = threading.Lock()

    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not DB_FILE.exists():
            DB_FILE.write_text(json.dumps({"reports": {}}, indent=2))

    def _read(self) -> dict:
        with self._lock:
            return json.loads(DB_FILE.read_text())

    def _write(self, data: dict) -> None:
        with self._lock:
            DB_FILE.write_text(json.dumps(data, indent=2, default=str))

    def create_report(self, report: ReportResponse, session_id: str) -> None:
        data = self._read()
        payload = json.loads(report.model_dump_json())
        payload["_session_id"] = session_id
        data["reports"][report.id] = payload
        self._write(data)

    def get_report(self, report_id: str) -> ReportResponse | None:
        data = self._read()
        raw = data["reports"].get(report_id)
        if raw is None:
            return None
        return ReportResponse.model_validate(raw)

    def list_reports(self, session_id: str | None = None, saved_only: bool = False) -> list[ReportSummary]:
        data = self._read()
        results = []
        for raw in data["reports"].values():
            if session_id and raw.get("_session_id") != session_id:
                continue
            if saved_only and not raw.get("is_saved"):
                continue
            results.append(
                ReportSummary(
                    id=raw["id"],
                    product_name=raw["product_name"],
                    category=raw.get("category"),
                    status=raw["status"],
                    overall_score=raw.get("overall_score"),
                    recommendation=raw.get("recommendation"),
                    is_saved=raw.get("is_saved", False),
                    created_at=raw["created_at"],
                )
            )
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    def delete_report(self, report_id: str) -> bool:
        data = self._read()
        if report_id in data["reports"]:
            del data["reports"][report_id]
            self._write(data)
            return True
        return False

    def toggle_favorite(self, report_id: str) -> ReportResponse | None:
        data = self._read()
        raw = data["reports"].get(report_id)
        if raw is None:
            return None
        raw["is_saved"] = not raw.get("is_saved", False)
        self._write(data)
        return ReportResponse.model_validate(raw)


class SupabaseReportRepository:
    """Real backend — talks to Supabase via the service-role key (SRS §18: no
    client-side auth, no RLS, all access backend-mediated). Maps to the
    `reports` + `module_results` + `profit_calculations` tables in
    database/schema.sql.
    """

    def __init__(self) -> None:
        from supabase import Client, create_client  # local import: optional dependency path

        settings = get_settings()
        self._client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def create_report(self, report: ReportResponse, session_id: str) -> None:
        product = (
            self._client.table("products")
            .upsert(
                {"product_name": report.product_name, "normalized_name": report.product_name.lower().strip(), "category": report.category},
                on_conflict="normalized_name",
            )
            .execute()
        )
        product_id = product.data[0]["id"] if product.data else None

        self._client.table("reports").insert(
            {
                "id": report.id,
                "session_id": session_id,
                "product_id": product_id,
                "product_name": report.product_name,
                "category": report.category,
                "status": report.status,
                "research_mode": report.research_mode,
                "overall_score": report.overall_score,
                "risk_level": report.risk_level,
                "recommendation": report.recommendation,
                "research_completeness_pct": report.research_completeness_pct,
                "recommendation_explanation": report.recommendation_explanation,
                "manual_verification_checklist": report.manual_verification_checklist,
                "knowledge_pack": json.loads(report.knowledge_pack.model_dump_json()) if report.knowledge_pack else None,
                "is_saved": report.is_saved,
                "created_at": report.created_at.isoformat(),
                "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            }
        ).execute()

        for section in report.sections:
            self._client.table("module_results").insert(
                {
                    "report_id": report.id,
                    "agent_type": section.agent_type,
                    "status": section.status.value,
                    "data": section.data,
                    "signals": section.signals,
                    "reasoning": section.reasoning,
                    "confidence_score": section.confidence_score,
                    "evidence_score": section.evidence_score,
                    "sub_score": section.sub_score,
                    "sources": [s.model_dump(mode="json") for s in section.sources],
                    "requires_manual_verification": section.requires_manual_verification,
                    "unavailable_reason": section.unavailable_reason,
                }
            ).execute()

    def _row_to_report(self, row: dict, module_rows: list[dict]) -> ReportResponse:
        sections = [
            ModuleSection(
                agent_type=m["agent_type"],
                label=DIMENSION_LABELS.get(m["agent_type"], m["agent_type"]),
                status=m["status"],
                data=m.get("data") or {},
                signals=m.get("signals") or {},
                reasoning=m.get("reasoning"),
                confidence_score=m.get("confidence_score"),
                evidence_score=m.get("evidence_score"),
                sub_score=m.get("sub_score"),
                sources=m.get("sources") or [],
                requires_manual_verification=m.get("requires_manual_verification", False),
                weight_in_decision_engine=DIMENSION_WEIGHTS.get(m["agent_type"], 0),
                unavailable_reason=m.get("unavailable_reason"),
            )
            for m in module_rows
        ]
        return ReportResponse(
            id=row["id"],
            product_name=row.get("product_name") or "",
            category=row.get("category"),
            status=row["status"],
            research_mode=row.get("research_mode", "manual"),
            overall_score=row.get("overall_score"),
            risk_level=row.get("risk_level"),
            recommendation=row.get("recommendation"),
            is_saved=row.get("is_saved", False),
            sections=sections,
            manual_verification_checklist=row.get("manual_verification_checklist") or [],
            research_completeness_pct=row.get("research_completeness_pct") or 0.0,
            recommendation_explanation=row.get("recommendation_explanation") or "",
            knowledge_pack=row.get("knowledge_pack"),
            created_at=datetime.fromisoformat(row["created_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
        )

    def get_report(self, report_id: str) -> ReportResponse | None:
        report_row = self._client.table("reports").select("*").eq("id", report_id).maybe_single().execute()
        if not report_row or not report_row.data:
            return None
        modules = self._client.table("module_results").select("*").eq("report_id", report_id).execute()
        return self._row_to_report(report_row.data, modules.data)

    def list_reports(self, session_id: str | None = None, saved_only: bool = False) -> list[ReportSummary]:
        query = self._client.table("reports").select("*")
        if session_id:
            query = query.eq("session_id", session_id)
        if saved_only:
            query = query.eq("is_saved", True)
        rows = query.order("created_at", desc=True).execute()
        return [
            ReportSummary(
                id=r["id"],
                product_name=r.get("product_name") or "",
                category=r.get("category"),
                status=r["status"],
                overall_score=r.get("overall_score"),
                recommendation=r.get("recommendation"),
                is_saved=r.get("is_saved", False),
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows.data
        ]

    def delete_report(self, report_id: str) -> bool:
        result = self._client.table("reports").delete().eq("id", report_id).execute()
        return bool(result.data)

    def toggle_favorite(self, report_id: str) -> ReportResponse | None:
        report = self.get_report(report_id)
        if report is None:
            return None
        new_value = not report.is_saved
        self._client.table("reports").update({"is_saved": new_value}).eq("id", report_id).execute()
        report.is_saved = new_value
        return report


_repository_instance: ReportRepository | None = None


def get_repository() -> ReportRepository:
    global _repository_instance
    if _repository_instance is not None:
        return _repository_instance

    settings = get_settings()
    if settings.supabase_configured:
        _repository_instance = SupabaseReportRepository()
    else:
        _repository_instance = JsonFileReportRepository()
    return _repository_instance
