"use client";

import { useEffect, useState } from "react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/tooltip";
import { getReportStage, setReportStage, TIMELINE_STAGES, type TimelineStage } from "@/lib/local-tracking";
import { cn } from "@/lib/utils";

// Tracked entirely in this browser's local storage — the backend has no
// lifecycle/status column on reports, and this redesign doesn't add one.
// This is a personal checklist, not a synced record (see lib/local-tracking.ts).
export function ProductTimeline({ reportId }: { reportId: string }) {
  const [stage, setStage] = useState<TimelineStage>("research_started");

  useEffect(() => {
    setStage(getReportStage(reportId));
  }, [reportId]);

  const currentIdx = TIMELINE_STAGES.findIndex((s) => s.key === stage);
  const next = TIMELINE_STAGES[currentIdx + 1];

  function advance() {
    if (!next) return;
    setReportStage(reportId, next.key);
    setStage(next.key);
  }

  return (
    <Card className="print:hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-1.5 text-sm">
          Product Timeline
          <InfoTooltip text="Tracked only on this device — a personal checklist, not synced anywhere." />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center">
          {TIMELINE_STAGES.map((s, i) => (
            <div key={s.key} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-medium",
                    i < currentIdx
                      ? "bg-success text-success-foreground"
                      : i === currentIdx
                        ? "bg-primary text-primary-foreground"
                        : "bg-secondary text-muted-foreground",
                  )}
                >
                  {i < currentIdx ? <Check className="h-3.5 w-3.5" /> : i + 1}
                </div>
                <span
                  className={cn(
                    "hidden max-w-[70px] text-center text-[10px] leading-tight sm:block",
                    i === currentIdx ? "font-medium text-foreground" : "text-muted-foreground",
                  )}
                >
                  {s.label}
                </span>
              </div>
              {i < TIMELINE_STAGES.length - 1 && (
                <div className={cn("mx-1 h-0.5 flex-1", i < currentIdx ? "bg-success" : "bg-secondary")} />
              )}
            </div>
          ))}
        </div>
        {next && (
          <Button variant="outline" size="sm" onClick={advance}>
            Mark as &quot;{next.label}&quot;
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
