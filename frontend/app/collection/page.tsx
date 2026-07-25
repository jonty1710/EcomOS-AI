"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardList, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import type { ProductProfileSummary } from "@/lib/types";

export default function DataCollectionListPage() {
  const [profiles, setProfiles] = useState<ProductProfileSummary[] | null>(null);

  function reload() {
    api.listProfiles().then(setProfiles).catch(() => setProfiles([]));
  }

  useEffect(reload, []);

  async function handleDelete(id: string) {
    await api.deleteProfile(id);
    reload();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Data Collection</h1>
          <p className="text-sm text-muted-foreground">Product Profiles — the source of truth for every research run.</p>
        </div>
        <Button asChild size="sm">
          <Link href="/collection/new">
            <Plus className="h-4 w-4" />
            New Profile
          </Link>
        </Button>
      </div>

      <div className="space-y-2">
        {profiles === null ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)
        ) : profiles.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No product profiles yet"
            description="Start a new Data Collection profile to build the source of truth for your next research run."
            actionLabel="New Profile"
            actionHref="/collection/new"
          />
        ) : (
          profiles.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
              <div className="min-w-0">
                <Link href={`/collection/${p.id}`} className="truncate text-sm font-medium hover:underline">
                  {p.product_name}
                </Link>
                <p className="text-xs text-muted-foreground">
                  Version {p.version} · Updated {new Date(p.updated_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Badge variant={p.ready_for_research ? "success" : "warning"}>
                  {p.completeness_pct.toFixed(0)}% complete
                </Badge>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(p.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
