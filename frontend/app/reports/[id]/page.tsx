"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Archive, ArchiveRestore, ArrowLeft, Copy, Printer, Star, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DecisionCard } from "@/components/report/decision-card";
import { HealthMeter } from "@/components/report/health-meter";
import { ProfitSnapshotCard } from "@/components/report/profit-snapshot-card";
import { RiskSummaryCard } from "@/components/report/risk-summary-card";
import { NextActionsCard } from "@/components/report/next-actions-card";
import { ProductTimeline } from "@/components/report/product-timeline";
import { AdvancedAnalysis } from "@/components/report/advanced-analysis";
import { isArchived, setArchived } from "@/lib/local-tracking";
import { api, ApiRequestError } from "@/lib/api-client";
import type { ReportResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [archived, setArchivedState] = useState(false);

  useEffect(() => {
    api
      .getReport(id)
      .then(setReport)
      .catch((e: ApiRequestError) => setError(e.message));
    setArchivedState(isArchived(id));
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

  function handleArchiveToggle() {
    if (!report) return;
    const next = !archived;
    setArchived(report.id, next);
    setArchivedState(next);
  }

  function handleDuplicate() {
    if (!report) return;
    router.push(`/collection/new?name=${encodeURIComponent(report.product_name)}`);
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
      <div className="mx-auto max-w-3xl space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" disabled={busy} onClick={handleFavorite}>
            <Star className={cn("h-4 w-4", report.is_saved && "fill-warning text-warning")} />
            {report.is_saved ? "Saved" : "Save"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleDuplicate}>
            <Copy className="h-4 w-4" />
            Duplicate
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="h-4 w-4" />
            Print / Save PDF
          </Button>
          <Button variant="outline" size="sm" onClick={handleArchiveToggle}>
            {archived ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
            {archived ? "Unarchive" : "Archive"}
          </Button>
          <Button variant="outline" size="sm" disabled={busy} onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <div>
        <h1 className="text-xl font-semibold">{report.product_name}</h1>
        <p className="text-sm text-muted-foreground">
          {report.category ?? "Uncategorized"} · Researched {new Date(report.created_at).toLocaleString()}
          {archived && <span className={cn("ml-2 text-warning")}>· Archived</span>}
        </p>
      </div>

      <DecisionCard report={report} />
      <HealthMeter score={report.overall_score} />
      <ProfitSnapshotCard report={report} />
      <RiskSummaryCard report={report} />
      <NextActionsCard report={report} />
      <ProductTimeline reportId={report.id} />
      <AdvancedAnalysis report={report} />
    </div>
  );
}
