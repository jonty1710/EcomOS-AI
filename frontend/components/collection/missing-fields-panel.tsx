import { CheckCircle2, ListChecks } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FieldDefinition } from "@/lib/types";

// Never overwhelm the user — show only what's actually missing, split into
// Required vs Optional exactly like the Phase 2 brief's own worked example.
export function MissingFieldsPanel({
  requiredKeys,
  optionalKeys,
  fieldsByKey,
}: {
  requiredKeys: string[];
  optionalKeys: string[];
  fieldsByKey: Record<string, FieldDefinition>;
}) {
  if (requiredKeys.length === 0 && optionalKeys.length === 0) {
    return (
      <Card className="border-success/40 bg-success/5">
        <CardContent className="flex items-center gap-2 py-4 text-sm text-success">
          <CheckCircle2 className="h-4 w-4" />
          All fields are filled — nothing outstanding.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={requiredKeys.length > 0 ? "border-warning/40 bg-warning/5" : undefined}>
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5 text-sm">
          <ListChecks className="h-4 w-4" />
          What&apos;s still needed
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {requiredKeys.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-warning">Required Inputs</p>
            <div className="flex flex-wrap gap-1.5">
              {requiredKeys.map((k) => (
                <Badge key={k} variant="warning">
                  {fieldsByKey[k]?.label ?? k}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {optionalKeys.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">Optional Inputs</p>
            <div className="flex flex-wrap gap-1.5">
              {optionalKeys.slice(0, 20).map((k) => (
                <Badge key={k} variant="outline">
                  {fieldsByKey[k]?.label ?? k}
                </Badge>
              ))}
              {optionalKeys.length > 20 && (
                <Badge variant="outline">+{optionalKeys.length - 20} more</Badge>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
