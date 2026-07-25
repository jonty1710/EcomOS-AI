import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";

// Every unfinished AI section must clearly say so — never a fake or placeholder
// number (Phase 1 brief). Used identically everywhere an AI-dependent dimension
// renders (PRS §6-§11 dimensions not yet wired to a provider).
export function PlannedForAiBadge() {
  return (
    <Badge variant="muted" className="gap-1.5">
      <Sparkles className="h-3 w-3" />
      Planned for AI Phase
    </Badge>
  );
}

export function PlannedForAiPanel({ reason }: { reason?: string | null }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-secondary/40 p-4 text-sm text-muted-foreground">
      <div className="mb-1 flex items-center gap-1.5 font-medium text-foreground">
        <Sparkles className="h-3.5 w-3.5" />
        Not yet connected
      </div>
      <p>
        {reason ??
          "This section requires AI-driven research that hasn't been built yet. Planned for the AI Integration phase."}
      </p>
    </div>
  );
}
