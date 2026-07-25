import { Sparkles, User, ShieldAlert, Calculator } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { EffectiveClassification } from "@/lib/types";

// One badge, one meaning, reused everywhere a field appears — same principle
// as the AI PlannedForAiBadge (FBP §19 consistency rule). These are the
// Phase 2 brief's three collection categories, plus Calculated shown
// distinctly since it's never "requested" from anyone.
export function ClassificationBadge({ classification }: { classification: EffectiveClassification }) {
  switch (classification) {
    case "auto_detect":
      return (
        <Badge variant="secondary" className="gap-1">
          <Sparkles className="h-3 w-3" />
          Auto Detect
        </Badge>
      );
    case "manual_verification_required":
      return (
        <Badge variant="warning" className="gap-1">
          <ShieldAlert className="h-3 w-3" />
          Manual Verification Required
        </Badge>
      );
    case "calculated":
      return (
        <Badge variant="success" className="gap-1">
          <Calculator className="h-3 w-3" />
          Calculated
        </Badge>
      );
    case "user_input_required":
    default:
      return (
        <Badge variant="outline" className="gap-1">
          <User className="h-3 w-3" />
          User Input
        </Badge>
      );
  }
}
