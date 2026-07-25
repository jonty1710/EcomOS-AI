"use client";

import { useEffect, useState } from "react";
import { GitCompare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ReportRow } from "@/components/report/report-row";
import { api, ApiRequestError } from "@/lib/api-client";
import type { CompareResponse, ReportSummary } from "@/lib/types";

// Compares deterministic fields only (Phase 1 brief §10): overall status,
// recommendation, and the Profit & Unit Economics / Logistics sub-scores —
// the only two of eleven dimensions with real data before the AI phase.
export default function ComparePage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listReports().then(setReports).catch(() => setReports([]));
  }, []);

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 5 ? [...prev, id] : prev));
  }

  async function runCompare() {
    setError(null);
    try {
      const result = await api.compareReports(selected);
      setComparison(result);
    } catch (e) {
      setError(e instanceof ApiRequestError ? e.message : "Could not compare these reports.");
    }
  }

  if (comparison) {
    const scoredSections = ["profit_unit_economics", "logistics_risk"];
    return (
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Compare</h1>
          <Button variant="outline" size="sm" onClick={() => setComparison(null)}>
            Back to selection
          </Button>
        </div>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full min-w-[600px] text-sm">
            <thead className="bg-secondary/50">
              <tr>
                <th className="p-3 text-left font-medium text-muted-foreground">Dimension</th>
                {comparison.reports.map((r) => (
                  <th key={r.id} className="p-3 text-left font-medium">
                    {r.product_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-border">
                <td className="p-3 text-muted-foreground">Overall Score</td>
                {comparison.reports.map((r) => (
                  <td key={r.id} className="p-3 font-medium">
                    {r.overall_score ?? "—"}
                  </td>
                ))}
              </tr>
              <tr className="border-t border-border">
                <td className="p-3 text-muted-foreground">Recommendation</td>
                {comparison.reports.map((r) => (
                  <td key={r.id} className="p-3 font-medium">
                    {r.recommendation}
                  </td>
                ))}
              </tr>
              <tr className="border-t border-border">
                <td className="p-3 text-muted-foreground">Research Completeness</td>
                {comparison.reports.map((r) => (
                  <td key={r.id} className="p-3 font-medium">
                    {r.research_completeness_pct}%
                  </td>
                ))}
              </tr>
              {scoredSections.map((agentType) => (
                <tr key={agentType} className="border-t border-border">
                  <td className="p-3 text-muted-foreground">
                    {comparison.reports[0]?.sections.find((s) => s.agent_type === agentType)?.label ?? agentType}
                  </td>
                  {comparison.reports.map((r) => {
                    const section = r.sections.find((s) => s.agent_type === agentType);
                    return (
                      <td key={r.id} className="p-3 font-medium">
                        {section?.sub_score ?? "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">
          Only Profit &amp; Unit Economics and preliminary Logistics Risk have real data in Phase 1 — the remaining
          dimensions show as Planned for AI Phase on each report&apos;s own page.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Compare</h1>
        <p className="text-sm text-muted-foreground">Select 2-5 researched products to compare, deterministic fields only.</p>
      </div>

      {reports === null ? (
        Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)
      ) : reports.length < 2 ? (
        <EmptyState
          icon={GitCompare}
          title="Not enough research to compare"
          description="Research at least two products, then come back here to compare them side by side."
          actionLabel="Start Research"
          actionHref="/research/new"
        />
      ) : (
        <>
          <div className="space-y-2">
            {reports.map((r) => (
              <ReportRow key={r.id} report={r} selectable selected={selected.includes(r.id)} onToggleSelect={toggle} />
            ))}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Card>
            <CardContent className="flex items-center justify-between py-3">
              <p className="text-sm text-muted-foreground">{selected.length} selected (2-5 required)</p>
              <Button disabled={selected.length < 2} onClick={runCompare}>
                <GitCompare className="h-4 w-4" />
                Compare Selected
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
