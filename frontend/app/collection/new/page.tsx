"use client";

import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { ProfileEditor } from "@/components/collection/profile-editor";
import { api } from "@/lib/api-client";
import type { FieldRegistryResponse } from "@/lib/types";

export default function NewDataCollectionPage() {
  const [registry, setRegistry] = useState<FieldRegistryResponse | null>(null);

  useEffect(() => {
    api.getFieldRegistry().then(setRegistry);
  }, []);

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

      {registry ? (
        <ProfileEditor fieldRegistry={registry} initialProfile={null} />
      ) : (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
    </div>
  );
}
