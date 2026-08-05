"use client";

import { useState } from "react";
import { AlertTriangle, ChevronDown } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ModuleCard } from "@/components/report/module-card";
import { InfoTooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { ReportResponse } from "@/lib/types";

// Everything a beginner doesn't need up front, but an Enterprise/technical
// user still wants: the full per-dimension breakdown, evidence/confidence
// scores, sources, and the raw completeness figure. Collapsed by default —
// same content the old Report screen always showed, just no longer forced
// on every visitor.
export function AdvancedAnalysis({ report }: { report: ReportResponse }) {
  const [open, setOpen] = useState(false);

  return (
    <Card className="print:hidden">
      <CardHeader
        className="cursor-pointer select-none flex-row items-center justify-between gap-2 space-y-0"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="flex items-center gap-1.5 text-sm font-medium">
          Advanced Analysis
          <InfoTooltip text="The full technical breakdown — every research dimension, evidence, and sources." />
        </span>
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </CardHeader>

      {open && (
        <CardContent className="space-y-4">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Why this result?</p>
            <p className="text-sm text-muted-foreground">{report.recommendation_explanation}</p>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
            <span className="text-muted-foreground">Information Available</span>
            <span className="font-medium">{report.research_completeness_pct}%</span>
          </div>

          {report.manual_verification_checklist.length > 0 && (
            <div className="rounded-md border border-warning/40 bg-warning/5 p-3">
              <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-warning">
                <AlertTriangle className="h-4 w-4" />
                Full Manual Verification Checklist
              </div>
              <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                {report.manual_verification_checklist.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-2">
            {report.sections.map((section) => (
              <ModuleCard key={section.agent_type} section={section} />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
