import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/tooltip";
import type { ReportResponse } from "@/lib/types";

type RiskColor = "green" | "yellow" | "red" | "gray";

const DOT_CLASS: Record<RiskColor, string> = {
  green: "bg-success",
  yellow: "bg-warning",
  red: "bg-destructive",
  gray: "bg-muted-foreground/40",
};

const CAPTION: Record<RiskColor, string> = {
  green: "Low risk",
  yellow: "Moderate risk",
  red: "High risk",
  gray: "Not available yet",
};

// Weighted-component maxima, reproduced from backend/app/scoring/risk.py's
// fixed formula (fragility*0.35, rto*0.25, return*0.20 of a 0-100 scale) so
// the already-computed numbers can be shown as traffic lights instead of raw
// points. The underlying numbers and their meaning are 100% backend-computed;
// this only changes how they're displayed.
const RTO_MAX = 25;
const RETURN_MAX = 20;

function bucket(value: number, max: number): RiskColor {
  const frac = value / max;
  if (frac < 0.33) return "green";
  if (frac < 0.66) return "yellow";
  return "red";
}

function fragilityColor(fragility: string | undefined): RiskColor {
  if (fragility === "Low") return "green";
  if (fragility === "Medium") return "yellow";
  if (fragility === "High") return "red";
  return "gray";
}

function Facet({ label, color, tooltip }: { label: string; color: RiskColor; tooltip: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5">
      <span className="flex items-center gap-1.5 text-sm">
        {label}
        <InfoTooltip text={tooltip} />
      </span>
      <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <span className={`h-2.5 w-2.5 rounded-full ${DOT_CLASS[color]}`} />
        {CAPTION[color]}
      </span>
    </div>
  );
}

export function RiskSummaryCard({ report }: { report: ReportResponse }) {
  const logistics = report.sections.find((s) => s.agent_type === "logistics_risk");

  const logisticsReady = logistics?.status === "completed";
  const components = (logistics?.data.components as Record<string, number> | undefined) ?? {};
  const fragility = logistics?.data.fragility as string | undefined;

  const returnsColor: RiskColor = logisticsReady ? bucket(components.return_ratio ?? 0, RETURN_MAX) : "gray";
  const rtoColor: RiskColor = logisticsReady ? bucket(components.rto_ratio ?? 0, RTO_MAX) : "gray";
  const packagingColor: RiskColor = logisticsReady ? fragilityColor(fragility) : "gray";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Risk Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <Facet
          label="Competition"
          color="gray"
          tooltip="How crowded this product's market is. Needs AI-powered research, not available yet."
        />
        <Facet
          label="Returns"
          color={returnsColor}
          tooltip="How likely customers are to return this product, based on your entered costs."
        />
        <Facet
          label="RTO (Return to Origin)"
          color={rtoColor}
          tooltip="How likely a delivery is to fail and come back to you unsold."
        />
        <Facet
          label="Supplier"
          color="gray"
          tooltip="How reliable this product's typical suppliers are. Needs AI-powered research, not available yet."
        />
        <Facet
          label="Breakable Risk"
          color={packagingColor}
          tooltip="How likely this product is to get damaged in shipping."
        />
        {!logisticsReady && (
          <p className="pt-1 text-xs text-muted-foreground">
            Add Weight in Data Collection for a real Returns/RTO/Breakable Risk read.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
