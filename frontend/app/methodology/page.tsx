import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PlannedForAiBadge } from "@/components/planned-for-ai";

const DIMENSIONS: { label: string; weight: number; status: "deterministic" | "planned" }[] = [
  { label: "Demand Intelligence", weight: 15, status: "planned" },
  { label: "Competitive Landscape", weight: 10, status: "planned" },
  { label: "Pricing Intelligence", weight: 8, status: "planned" },
  { label: "Trend & Seasonality", weight: 7, status: "planned" },
  { label: "Review Mining", weight: 8, status: "planned" },
  { label: "Keyword & Discoverability", weight: 5, status: "planned" },
  { label: "Supplier Sourcing", weight: 8, status: "planned" },
  { label: "Logistics & Fulfillment Risk", weight: 12, status: "deterministic" },
  { label: "Compliance & Regulatory", weight: 8, status: "planned" },
  { label: "Brand & Positioning", weight: 8, status: "planned" },
  { label: "Profit & Unit Economics", weight: 11, status: "deterministic" },
];

// Read-only transparency screen (FBP §4.9) — no raw prompts, no editing.
export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Methodology</h1>
        <p className="text-sm text-muted-foreground">
          How EcomOS AI reasons — plain language, no raw prompts or internals.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Decision Engine Weight Table</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {DIMENSIONS.map((d) => (
            <div key={d.label} className="flex items-center justify-between border-b border-border py-2 last:border-0">
              <div>
                <p className="text-sm font-medium">{d.label}</p>
                <p className="text-xs text-muted-foreground">Weight: {d.weight} / 100</p>
              </div>
              {d.status === "deterministic" ? (
                <Badge variant="success">Deterministic — active</Badge>
              ) : (
                <PlannedForAiBadge />
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Current Phase</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Phase 1 (Foundation). Only Profit &amp; Unit Economics and a preliminary slice of Logistics &amp;
            Fulfillment Risk are computed — both are 100% deterministic arithmetic, no AI involved. Because fewer
            than half the weighted dimensions can be scored yet, every report&apos;s overall recommendation is
            deliberately shown as <span className="font-medium text-foreground">Insufficient Data</span> rather than
            a fabricated Launch/Test/Reject verdict. See docs/PRS.md §16 for the research-completeness rule this
            follows.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
