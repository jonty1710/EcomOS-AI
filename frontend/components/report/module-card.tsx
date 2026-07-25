"use client";

import { useState } from "react";
import { ChevronDown, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ConfidenceEvidenceBadges } from "@/components/report/confidence-evidence-badges";
import { DataList } from "@/components/report/data-list";
import { PlannedForAiBadge, PlannedForAiPanel } from "@/components/planned-for-ai";
import { cn } from "@/lib/utils";
import type { ModuleSection } from "@/lib/types";

function statusBadge(section: ModuleSection) {
  switch (section.status) {
    case "completed":
      return <Badge variant="success">Completed</Badge>;
    case "unscored_insufficient_evidence":
      return <Badge variant="warning">Insufficient Evidence</Badge>;
    case "planned_for_ai_phase":
      return <PlannedForAiBadge />;
    case "failed":
      return <Badge variant="destructive">Failed</Badge>;
  }
}

export function ModuleCard({ section }: { section: ModuleSection }) {
  const [open, setOpen] = useState(section.status === "completed");
  const isPlanned = section.status === "planned_for_ai_phase";

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none flex-row items-center justify-between gap-2 space-y-0"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2.5">
          <span className="text-sm font-medium">{section.label}</span>
          <span className="text-xs text-muted-foreground">Weight {section.weight_in_decision_engine}</span>
          {section.requires_manual_verification && (
            <Badge variant="warning" className="gap-1">
              <ShieldAlert className="h-3 w-3" />
              Manual verification required
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3">
          {statusBadge(section)}
          {section.sub_score !== null && <span className="text-sm font-semibold">{section.sub_score}</span>}
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
        </div>
      </CardHeader>

      {open && (
        <CardContent className="space-y-3">
          {isPlanned ? (
            <PlannedForAiPanel reason={section.unavailable_reason} />
          ) : (
            <>
              <ConfidenceEvidenceBadges confidence={section.confidence_score} evidence={section.evidence_score} />
              {section.reasoning && <p className="text-sm text-muted-foreground">{section.reasoning}</p>}
              <DataList data={section.data} />
              {section.sources.length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Sources</p>
                  <ul className="space-y-0.5 text-xs text-muted-foreground">
                    {section.sources.map((s, i) => (
                      <li key={i}>
                        {s.name} <span className="opacity-60">({s.type})</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </CardContent>
      )}
    </Card>
  );
}
