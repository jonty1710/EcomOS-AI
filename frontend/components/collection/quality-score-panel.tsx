import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FRIENDLY_METRIC_LABELS } from "@/lib/friendly-labels";
import { cn } from "@/lib/utils";
import type { ExperienceMode } from "@/lib/field-modes";
import type { DataQualityScore } from "@/lib/types";

function barColor(pct: number, invert = false) {
  const good = invert ? pct <= 20 : pct >= 80;
  const mid = invert ? pct <= 50 : pct >= 50;
  if (good) return "bg-success";
  if (mid) return "bg-warning";
  return "bg-destructive";
}

function Metric({ label, pct, invert }: { label: string; pct: number; invert?: boolean }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={cn("h-full rounded-full transition-all", barColor(pct, invert))}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
    </div>
  );
}

// Enterprise: four independent numbers, four independent questions — never
// collapsed into one "quality" figure (same principle as Confidence vs
// Evidence throughout this app). Beginner/Professional: that's four jargon
// terms a seller doesn't need — one plain-language progress bar instead.
export function QualityScorePanel({ quality, mode }: { quality: DataQualityScore; mode: ExperienceMode }) {
  if (mode !== "enterprise") {
    const pct = quality.completeness_pct;
    return (
      <Card>
        <CardContent className="space-y-2 py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">{FRIENDLY_METRIC_LABELS.completeness}</span>
            <span className="text-muted-foreground">{pct.toFixed(0)}% done</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Data Quality</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <Metric label="Completeness" pct={quality.completeness_pct} />
        <Metric label="Validation" pct={quality.validation_pct} />
        <Metric label="Confidence" pct={quality.confidence_pct} />
        <Metric label="Verification Pending" pct={quality.verification_pending_pct} invert />
      </CardContent>
    </Card>
  );
}
