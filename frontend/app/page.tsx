"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { SavedProductCard } from "@/components/dashboard/saved-product-card";
import { useExperienceMode } from "@/lib/experience-mode";
import { getArchivedIds } from "@/lib/local-tracking";
import { api } from "@/lib/api-client";
import type { ReportResponse, ReportSummary } from "@/lib/types";

const DASHBOARD_CARD_LIMIT = 9;

export default function DashboardPage() {
  const { mode } = useExperienceMode();
  const [summaries, setSummaries] = useState<ReportSummary[] | null>(null);
  const [detailed, setDetailed] = useState<Record<string, ReportResponse>>({});

  function reload() {
    api.listReports().then(setSummaries).catch(() => setSummaries([]));
  }

  useEffect(reload, []);

  const archivedIds = getArchivedIds();
  const visibleSummaries = (summaries ?? []).filter((r) => !archivedIds.has(r.id));
  const cardSummaries = visibleSummaries.slice(0, DASHBOARD_CARD_LIMIT);

  // Profit isn't on ReportSummary (only the full ReportResponse carries the
  // Profit section) — fetch the visible cards' full detail so cards can show
  // it. Bounded to DASHBOARD_CARD_LIMIT so this stays a handful of requests,
  // not one per saved report.
  useEffect(() => {
    const missing = cardSummaries.filter((r) => !detailed[r.id]);
    if (missing.length === 0) return;
    Promise.all(missing.map((r) => api.getReport(r.id).catch(() => null))).then((results) => {
      setDetailed((prev) => {
        const next = { ...prev };
        for (const r of results) if (r) next[r.id] = r;
        return next;
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summaries]);

  async function handleFavorite(id: string) {
    const updated = await api.toggleFavorite(id);
    setDetailed((prev) => ({ ...prev, [id]: updated }));
    reload();
  }

  async function handleDelete(id: string) {
    await api.deleteReport(id);
    reload();
  }

  const cards = cardSummaries.map((s) => detailed[s.id]).filter((r): r is ReportResponse => Boolean(r));
  const loadingCards = cardSummaries.length > 0 && cards.length < cardSummaries.length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          {mode === "beginner"
            ? "Everything you've researched, in one place."
            : "One-glance orientation — what's researched, what's next."}
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-8 text-center sm:flex-row sm:justify-between sm:text-left">
          <div>
            <p className="font-medium">{mode === "beginner" ? "Research a New Product" : "Start a Product Profile"}</p>
            <p className="text-sm text-muted-foreground">
              {mode === "beginner"
                ? "Answer a few quick questions and get a clear Launch/Wait/Reject read."
                : "The Data Collection Engine classifies every field and tells you exactly what's missing — no AI, no guessing."}
            </p>
          </div>
          <Button asChild>
            <Link href="/collection/new">
              <Plus className="h-4 w-4" />
              New Research
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <LayoutDashboard className="h-4 w-4" />
            Your Products
          </CardTitle>
        </CardHeader>
        <CardContent>
          {summaries === null ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </div>
          ) : visibleSummaries.length === 0 ? (
            <EmptyState
              icon={Search}
              title="You haven't researched any products yet"
              description="Research Your First Product to see it appear here."
              actionLabel="Research Your First Product"
              actionHref="/collection/new"
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {cards.map((r) => (
                <SavedProductCard key={r.id} report={r} onFavorite={handleFavorite} onDelete={handleDelete} />
              ))}
              {loadingCards &&
                Array.from({ length: cardSummaries.length - cards.length }).map((_, i) => (
                  <Skeleton key={`loading-${i}`} className="h-32 w-full" />
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
