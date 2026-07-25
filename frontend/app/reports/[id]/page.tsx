"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, Star, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreRing } from "@/components/report/score-ring";
import { ModuleCard } from "@/components/report/module-card";
import { api, ApiRequestError } from "@/lib/api-client";
import type { ReportResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

function recommendationVariant(recommendation: string | null) {
  switch (recommendation) {
    case "Launch":
    case "Strong Candidate":
      return "success" as const;
    case "Test First":
    case "Needs Review":
      return "warning" as const;
    case "Reject":
      return "destructive" as const;
    default:
      return "muted" as const;
  }
}

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .getReport(id)
      .then(setReport)
      .catch((e: ApiRequestError) => setError(e.message));
  }, [id]);

  async function handleFavorite() {
    if (!report) return;
    setBusy(true);
    try {
      const updated = await api.toggleFavorite(report.id);
      setReport(updated);
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!report) return;
    setBusy(true);
    try {
      await api.deleteReport(report.id);
      router.push("/history");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-destructive" />
        <p className="font-medium">{error}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={() => router.push("/history")}>
          Back to History
        </Button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={busy} onClick={handleFavorite}>
            <Star className={cn("h-4 w-4", report.is_saved && "fill-warning text-warning")} />
            {report.is_saved ? "Saved" : "Save"}
          </Button>
          <Button variant="outline" size="sm" disabled={busy} onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold">{report.product_name}</h1>
        <p className="text-sm text-muted-foreground">
          {report.category ?? "Uncategorized"} · Researched {new Date(report.created_at).toLocaleString()}
        </p>
      </div>

      {/* Decision block — always first, per FBP §8.2 */}
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <ScoreRing score={report.overall_score} />
            <div>
              <Badge variant={recommendationVariant(report.recommendation)} className="mb-1.5 text-sm">
                {report.recommendation}
              </Badge>
              <p className="text-sm text-muted-foreground">
                Risk level: <span className="font-medium text-foreground">{report.risk_level ?? "Unknown"}</span>
              </p>
            </div>
          </div>
          <div className="text-right text-sm text-muted-foreground">
            <p>Research Completeness</p>
            <p className="text-lg font-semibold text-foreground">{report.research_completeness_pct}%</p>
          </div>
        </CardContent>
      </Card>

      {/* Explanation — PRS §13 Decision Record */}
      <Card>
        <CardContent className="py-4">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Why this result?</p>
          <p className="text-sm">{report.recommendation_explanation}</p>
        </CardContent>
      </Card>

      {/* Manual verification alerts — directly under the decision block, per FBP §8.3 */}
      {report.manual_verification_checklist.length > 0 && (
        <Card className="border-warning/40 bg-warning/5">
          <CardContent className="py-4">
            <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-warning">
              <AlertTriangle className="h-4 w-4" />
              Manual Verification Checklist
            </div>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
              {report.manual_verification_checklist.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Module sections, fixed order (FBP §8.1) */}
      <div className="space-y-2">
        {report.sections.map((section) => (
          <ModuleCard key={section.agent_type} section={section} />
        ))}
      </div>
    </div>
  );
}
