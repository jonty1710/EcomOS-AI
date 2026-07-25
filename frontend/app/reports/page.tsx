"use client";

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ReportRow } from "@/components/report/report-row";
import { api } from "@/lib/api-client";
import type { ReportSummary } from "@/lib/types";

export default function SavedReportsPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);

  function reload() {
    api.listReports(true).then(setReports).catch(() => setReports([]));
  }

  useEffect(reload, []);

  async function handleFavorite(id: string) {
    await api.toggleFavorite(id);
    reload();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Saved Reports</h1>
        <p className="text-sm text-muted-foreground">Reports you&apos;ve explicitly saved for later.</p>
      </div>

      <div className="space-y-2">
        {reports === null ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)
        ) : reports.length === 0 ? (
          <EmptyState icon={FileText} title="No saved reports" description="Save a report to find it here." actionLabel="Go to History" actionHref="/history" />
        ) : (
          reports.map((r) => <ReportRow key={r.id} report={r} onFavorite={handleFavorite} />)
        )}
      </div>
    </div>
  );
}
