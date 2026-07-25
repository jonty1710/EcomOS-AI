"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ReportRow } from "@/components/report/report-row";
import { api } from "@/lib/api-client";
import type { ReportSummary } from "@/lib/types";

export default function DashboardPage() {
  const [reports, setReports] = useState<ReportSummary[] | null>(null);

  useEffect(() => {
    api.listReports().then(setReports).catch(() => setReports([]));
  }, []);

  const savedReports = reports?.filter((r) => r.is_saved) ?? [];
  const recent = reports?.slice(0, 6) ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">One-glance orientation — what&apos;s researched, what&apos;s next.</p>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-8 text-center sm:flex-row sm:justify-between sm:text-left">
          <div>
            <p className="font-medium">Start a Product Profile</p>
            <p className="text-sm text-muted-foreground">
              The Data Collection Engine classifies every field and tells you exactly what&apos;s missing — no AI, no guessing.
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
            Recent Research
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {reports === null ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)
          ) : recent.length === 0 ? (
            <EmptyState
              icon={Search}
              title="You haven't researched any products yet"
              description="Start with your first product to see it appear here."
              actionLabel="Start Research"
              actionHref="/research/new"
            />
          ) : (
            recent.map((r) => <ReportRow key={r.id} report={r} />)
          )}
        </CardContent>
      </Card>

      {savedReports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Saved Reports</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {savedReports.map((r) => (
              <ReportRow key={r.id} report={r} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
