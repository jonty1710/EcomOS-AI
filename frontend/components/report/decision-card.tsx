import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { INSUFFICIENT_DATA_COPY, RECOMMENDATION_COPY } from "@/lib/friendly-labels";
import { cn } from "@/lib/utils";
import type { ReportResponse } from "@/lib/types";

const TONE_STYLES: Record<string, string> = {
  launch: "border-success/40 bg-success/5",
  test: "border-warning/40 bg-warning/5",
  wait: "border-orange-500/40 bg-orange-500/5",
  reject: "border-destructive/40 bg-destructive/5",
};

const RISK_BADGE_VARIANT: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  Low: "success",
  Medium: "warning",
  High: "destructive",
};

// The single most important screen in the whole redesign: "Should I launch
// this product?" answered in one glance. Today, Phase 1 has no AI agents, so
// the backend almost always returns "Insufficient Data" (PRS §16 hard floor —
// only 2 of 11 scored dimensions are computable without AI). That's not a bug
// to hide: showing a confident Launch/Reject call built from 2 dimensions
// would be dishonest. So "Insufficient Data" gets its own real, non-alarming
// state here rather than being force-mapped onto Launch/Test/Reject.
export function DecisionCard({ report }: { report: ReportResponse }) {
  const copy = report.recommendation ? RECOMMENDATION_COPY[report.recommendation] : undefined;
  const resolved = copy ?? INSUFFICIENT_DATA_COPY;
  const sentence = copy ? copy.sentence(report.product_name) : INSUFFICIENT_DATA_COPY.sentence;

  return (
    <Card className={cn("border-2", TONE_STYLES[resolved.tone])}>
      <CardContent className="flex flex-col items-center gap-3 py-8 text-center">
        <span className="text-5xl leading-none">{resolved.emoji}</span>
        <h2 className="text-2xl font-semibold">{resolved.label}</h2>
        <p className="max-w-md text-sm text-muted-foreground">{sentence}</p>
        {report.risk_level && (
          <Badge variant={RISK_BADGE_VARIANT[report.risk_level] ?? "muted"} className="mt-1">
            Risk: {report.risk_level}
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
