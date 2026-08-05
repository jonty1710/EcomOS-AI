import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { readWizardContext } from "@/lib/local-tracking";
import { getProfitExpectedCase } from "@/lib/report-helpers";
import type { ReportResponse } from "@/lib/types";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "success" | "destructive" }) {
  return (
    <div className="rounded-lg border border-border bg-secondary/30 p-4 text-center">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone === "success" ? "text-success" : tone === "destructive" ? "text-destructive" : ""}`}>
        {value}
      </p>
    </div>
  );
}

export function ProfitSnapshotCard({ report }: { report: ReportResponse }) {
  const expected = getProfitExpectedCase(report);
  if (!expected) return null;

  const ctx = readWizardContext(report.id);
  const breakEvenCaption = expected.breakeven_units
    ? ctx
      ? `≈ ₹${Math.round(ctx.buying_price * expected.breakeven_units).toLocaleString("en-IN")} to get there`
      : expected.breakeven_basis.startsWith("assumed_")
        ? "Assuming a 50-unit first batch"
        : "Based on your entered investment"
    : "Not reachable at current margin";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Profit Snapshot</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="Expected Profit"
          value={`₹${expected.net_profit.toLocaleString("en-IN")}`}
          tone={expected.net_profit >= 0 ? "success" : "destructive"}
        />
        <Stat
          label="Expected Margin"
          value={`${expected.margin_pct}%`}
          tone={expected.margin_pct >= 0 ? "success" : "destructive"}
        />
        <Stat label="Expected ROI" value={expected.roi_pct !== null ? `${expected.roi_pct}%` : "—"} />
        <div className="rounded-lg border border-border bg-secondary/30 p-4 text-center">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Break-Even</p>
          <p className="mt-1 text-2xl font-semibold">
            {expected.breakeven_units ? `${expected.breakeven_units} units` : "—"}
          </p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{breakEvenCaption}</p>
        </div>
      </CardContent>
    </Card>
  );
}
