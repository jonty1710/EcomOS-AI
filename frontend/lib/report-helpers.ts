import type { ReportResponse } from "./types";

export interface ProfitExpectedCase {
  net_profit: number;
  margin_pct: number;
  roi_pct: number | null;
  breakeven_units: number | null;
  breakeven_basis: string;
}

/** The Profit & Unit Economics agent is always real/deterministic (never
 * planned_for_ai_phase) — see backend/app/research/agents.py. Returns null
 * only if the section is genuinely missing (shouldn't happen for a manual
 * research report, but never assumed). */
export function getProfitExpectedCase(report: ReportResponse): ProfitExpectedCase | null {
  const section = report.sections.find((s) => s.agent_type === "profit_unit_economics");
  if (!section || section.status !== "completed") return null;
  return (section.data.expected_case as unknown as ProfitExpectedCase) ?? null;
}
