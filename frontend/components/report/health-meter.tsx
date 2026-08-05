import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/tooltip";

const ZONES = [
  { label: "Poor", className: "bg-destructive" },
  { label: "Average", className: "bg-warning" },
  { label: "Good", className: "bg-primary" },
  { label: "Excellent", className: "bg-success" },
];

function zoneLabel(score: number): string {
  if (score < 40) return "Poor";
  if (score < 60) return "Average";
  if (score < 80) return "Good";
  return "Excellent";
}

// Reads the Decision Engine's real overall_score directly — no new scoring
// logic here. Phase 1 has no AI agents wired in yet, so overall_score is
// null until then (PRS §16 hard floor); the gauge shows an honest "Pending"
// state rather than a fabricated number in that case.
export function HealthMeter({ score }: { score: number | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5 text-sm">
          Product Health
          <InfoTooltip text="An overall read on how strong this product looks, once full research is available." />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex h-3 w-full overflow-hidden rounded-full">
          {ZONES.map((z) => (
            <div key={z.label} className={`h-full flex-1 ${z.className} ${score === null ? "opacity-25" : ""}`} />
          ))}
        </div>
        {score === null ? (
          <p className="text-sm text-muted-foreground">
            Pending — full health scoring needs AI-powered research, coming soon.
          </p>
        ) : (
          <p className="text-sm">
            <span className="font-semibold">{zoneLabel(score)}</span>{" "}
            <span className="text-muted-foreground">({score.toFixed(0)} / 100)</span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
