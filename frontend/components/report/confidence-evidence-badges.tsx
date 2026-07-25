import { ShieldCheck, BrainCircuit } from "lucide-react";

import { cn } from "@/lib/utils";

function levelClass(value: number) {
  if (value >= 0.7) return "text-success";
  if (value >= 0.4) return "text-warning";
  return "text-destructive";
}

// Always shown together, never merged — distinct icon per PRS §14 / FBP §11:
// Confidence ("how sure is the model") vs. Evidence ("how much can we verify").
export function ConfidenceEvidenceBadges({
  confidence,
  evidence,
}: {
  confidence: number | null;
  evidence: number | null;
}) {
  if (confidence === null && evidence === null) return null;
  return (
    <div className="flex items-center gap-3 text-xs">
      {confidence !== null && (
        <span className={cn("flex items-center gap-1", levelClass(confidence))}>
          <BrainCircuit className="h-3.5 w-3.5" />
          Confidence {(confidence * 100).toFixed(0)}%
        </span>
      )}
      {evidence !== null && (
        <span className={cn("flex items-center gap-1", levelClass(evidence))}>
          <ShieldCheck className="h-3.5 w-3.5" />
          Evidence {(evidence * 100).toFixed(0)}%
        </span>
      )}
    </div>
  );
}
