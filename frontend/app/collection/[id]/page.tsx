"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileEditor } from "@/components/collection/profile-editor";
import { DataSourcesPanel } from "@/components/collection/data-sources-panel";
import { api, ApiRequestError } from "@/lib/api-client";
import type { FieldRegistryResponse, ProductProfile } from "@/lib/types";

export default function EditDataCollectionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [registry, setRegistry] = useState<FieldRegistryResponse | null>(null);
  const [profile, setProfile] = useState<ProductProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getFieldRegistry(), api.getProfile(id)])
      .then(([reg, prof]) => {
        setRegistry(reg);
        setProfile(prof);
      })
      .catch((e: ApiRequestError) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-destructive" />
        <p className="font-medium">{error}</p>
        <Button variant="outline" size="sm" className="mt-4" asChild>
          <Link href="/collection">Back to Data Collection</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">{profile?.product_name ?? "Loading..."}</h1>
        <p className="text-sm text-muted-foreground">
          {profile ? `Version ${profile.version}` : "Editing this profile creates a new version — nothing is overwritten."}
        </p>
      </div>

      {registry && profile ? (
        <Tabs defaultValue="edit">
          <TabsList>
            <TabsTrigger value="edit">Edit Profile</TabsTrigger>
            <TabsTrigger value="sources">Data Sources</TabsTrigger>
          </TabsList>
          <TabsContent value="edit">
            <ProfileEditor fieldRegistry={registry} initialProfile={profile} />
          </TabsContent>
          <TabsContent value="sources">
            <DataSourcesPanel profileId={profile.id} />
          </TabsContent>
        </Tabs>
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
