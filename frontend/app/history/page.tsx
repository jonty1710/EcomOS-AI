"use client";

import { useEffect, useState } from "react";
import { History as HistoryIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ReportRow } from "@/components/report/report-row";
import { getArchivedIds } from "@/lib/local-tracking";
import { api } from "@/lib/api-client";
import type { ReportSummary } from "@/lib/types";

export default function HistoryPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);
  const [query, setQuery] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  function reload() {
    api.listReports().then(setReports).catch(() => setReports([]));
  }

  useEffect(reload, []);

  async function handleFavorite(id: string) {
    await api.toggleFavorite(id);
    reload();
  }

  async function handleDelete(id: string) {
    await api.deleteReport(id);
    reload();
  }

  const archivedIds = getArchivedIds();
  const archivedCount = reports?.filter((r) => archivedIds.has(r.id)).length ?? 0;
  const filtered =
    reports?.filter(
      (r) => r.product_name.toLowerCase().includes(query.toLowerCase()) && (showArchived || !archivedIds.has(r.id)),
    ) ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">History</h1>
        <p className="text-sm text-muted-foreground">Every research run, permanent — nothing is silently rewritten.</p>
      </div>

      <div className="flex items-center gap-2">
        <Input placeholder="Search by product name..." value={query} onChange={(e) => setQuery(e.target.value)} />
        {archivedCount > 0 && (
          <Button variant="outline" size="sm" className="shrink-0" onClick={() => setShowArchived((v) => !v)}>
            {showArchived ? "Hide Archived" : `Show Archived (${archivedCount})`}
          </Button>
        )}
      </div>

      <div className="space-y-2">
        {reports === null ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={HistoryIcon}
            title={query ? `No matches for "${query}"` : "No research yet"}
            description={query ? "Try a different search term." : "Your research history will appear here."}
            actionLabel={query ? undefined : "Research Your First Product"}
            actionHref={query ? undefined : "/collection/new"}
          />
        ) : (
          filtered.map((r) => (
            <ReportRow key={r.id} report={r} onFavorite={handleFavorite} onDelete={handleDelete} />
          ))
        )}
      </div>
    </div>
  );
}
