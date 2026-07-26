"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProfileEditor } from "@/components/collection/profile-editor";
import { api, ApiRequestError } from "@/lib/api-client";
import type { FieldRegistryResponse } from "@/lib/types";

export default function NewDataCollectionPage() {
  const [registry, setRegistry] = useState<FieldRegistryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getFieldRegistry()
      .then((reg) => {
        setRegistry(reg);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(
          e instanceof ApiRequestError
            ? e.message
            : "Could not reach the server. If this is the first request in a while, the backend may still be waking up — try again in a moment.",
        );
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Data Collection</h1>
        <p className="text-sm text-muted-foreground">
          Every field is classified as Auto Detect, User Input Required, Manual Verification Required, or
          Calculated. Nothing is ever guessed — fill in what you know, and the engine will tell you exactly
          what&apos;s still missing.
        </p>
      </div>

      {error ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-destructive/40 bg-destructive/5 py-16 text-center">
          <AlertTriangle className="h-8 w-8 text-destructive" />
          <p className="max-w-sm text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </div>
      ) : registry ? (
        <ProfileEditor fieldRegistry={registry} initialProfile={null} />
      ) : (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      {loading && !registry && !error && (
        <p className="text-center text-xs text-muted-foreground">
          Connecting to the server — this can take up to a minute if it&apos;s been idle...
        </p>
      )}
    </div>
  );
}
