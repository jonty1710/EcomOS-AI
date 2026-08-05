"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save, Send, History as HistoryIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SectionCard } from "@/components/collection/section-card";
import { QualityScorePanel } from "@/components/collection/quality-score-panel";
import { MissingFieldsPanel } from "@/components/collection/missing-fields-panel";
import { ModeSelector } from "@/components/collection/mode-selector";
import { useExperienceMode } from "@/lib/experience-mode";
import { getVisibleFields } from "@/lib/field-modes";
import { api, ApiRequestError } from "@/lib/api-client";
import type { FieldDefinition, FieldRegistryResponse, ProductProfile, ProductProfileSummary } from "@/lib/types";

export function ProfileEditor({
  fieldRegistry,
  initialProfile,
}: {
  fieldRegistry: FieldRegistryResponse;
  initialProfile: ProductProfile | null;
}) {
  const router = useRouter();
  const { mode } = useExperienceMode();
  const [values, setValues] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    if (initialProfile) {
      for (const [key, fv] of Object.entries(initialProfile.fields)) {
        if (fv.value !== null && fv.value !== undefined) initial[key] = fv.value;
      }
    }
    return initial;
  });
  const [verified, setVerified] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    if (initialProfile) {
      for (const [key, fv] of Object.entries(initialProfile.fields)) {
        if (fv.verified) initial[key] = true;
      }
    }
    return initial;
  });
  const [sourceUrl, setSourceUrl] = useState(initialProfile?.source_url ?? "");
  const [profile, setProfile] = useState<ProductProfile | null>(initialProfile);
  const [currentId, setCurrentId] = useState<string | null>(initialProfile?.id ?? null);
  const [versions, setVersions] = useState<ProductProfileSummary[]>([]);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = { ...values, source_url: sourceUrl || undefined };
    for (const [key, isVerified] of Object.entries(verified)) {
      if (isVerified) payload[`${key}_verified`] = true;
    }
    return payload;
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      api.previewProfile(buildPayload()).then(setProfile).catch(() => {
        // preview failures are non-fatal — nothing has been saved yet
      });
    }, 600);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, sourceUrl]);

  useEffect(() => {
    if (currentId) {
      api.getProfileVersions(currentId).then(setVersions).catch(() => setVersions([]));
    }
  }, [currentId]);

  function handleChange(key: string, value: unknown) {
    setValues((v) => ({ ...v, [key]: value }));
  }
  function handleVerifiedChange(key: string, isVerified: boolean) {
    setVerified((v) => ({ ...v, [key]: isVerified }));
  }

  async function persist(): Promise<ProductProfile> {
    const saved = currentId
      ? await api.updateProfile(currentId, buildPayload())
      : await api.createProfile(buildPayload());
    setProfile(saved);
    if (saved.id !== currentId) {
      setCurrentId(saved.id);
      router.replace(`/collection/${saved.id}`);
    }
    return saved;
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await persist();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not save this profile.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSendToResearch() {
    setSending(true);
    setError(null);
    try {
      const saved = await persist();
      const report = await api.sendProfileToResearch(saved.id);
      router.push(`/reports/${report.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Could not send this profile to research.");
    } finally {
      setSending(false);
    }
  }

  // Progressive disclosure: only the fields this mode asks for ever reach
  // the form below — Beginner/Professional never even mount the hidden
  // fields' inputs, they're not just visually collapsed.
  const visibleFields = useMemo(() => getVisibleFields(mode, fieldRegistry.fields), [mode, fieldRegistry.fields]);
  const visibleKeySet = useMemo(() => new Set(visibleFields.map((f) => f.key)), [visibleFields]);

  const fieldsBySection = useMemo(() => {
    const map: Record<string, FieldDefinition[]> = {};
    for (const section of fieldRegistry.sections) map[section] = [];
    for (const f of visibleFields) map[f.section]?.push(f);
    return map;
  }, [fieldRegistry.sections, visibleFields]);

  const visibleSections = fieldRegistry.sections.filter((s) => (fieldsBySection[s]?.length ?? 0) > 0);

  const fieldsByKey = useMemo(() => Object.fromEntries(visibleFields.map((f) => [f.key, f])), [visibleFields]);

  // Filter the backend's missing_required/missing_optional (computed against
  // the FULL 53-field set) down to only what this mode actually shows —
  // never surface a "missing" badge for a field the user can't even see.
  const visibleMissingRequired = (profile?.missing_required ?? []).filter((k) => visibleKeySet.has(k));
  const visibleMissingOptional = (profile?.missing_optional ?? []).filter((k) => visibleKeySet.has(k));

  const showAdvancedCards = mode !== "beginner";

  return (
    <div className="space-y-6">
      <ModeSelector />

      {showAdvancedCards && versions.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-sm">
              <HistoryIcon className="h-4 w-4" />
              Version History
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {versions.map((v) => (
              <Badge
                key={v.id}
                variant={v.id === currentId ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => v.id !== currentId && router.push(`/collection/${v.id}`)}
              >
                v{v.version} · {v.completeness_pct.toFixed(0)}%
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {showAdvancedCards && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Marketplace URL (optional)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <Label htmlFor="source_url">Paste a product URL to record which marketplace this is from</Label>
            <Input
              id="source_url"
              placeholder="https://www.amazon.in/dp/..."
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
            {profile?.detected_marketplace && (
              <p className="text-xs text-muted-foreground">
                Detected: <span className="font-medium capitalize">{profile.detected_marketplace}</span> — no data is
                fetched automatically in this phase; the fields below still need to be filled in manually.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {profile && (
        <>
          <QualityScorePanel quality={profile.data_quality} mode={mode} />
          <MissingFieldsPanel
            requiredKeys={visibleMissingRequired}
            optionalKeys={visibleMissingOptional}
            fieldsByKey={fieldsByKey}
          />
        </>
      )}

      {visibleSections.map((section) => (
        <SectionCard
          key={section}
          section={section}
          fields={fieldsBySection[section] ?? []}
          values={values}
          fieldStates={profile?.fields ?? {}}
          onChange={handleChange}
          onVerifiedChange={handleVerifiedChange}
          mode={mode}
        />
      ))}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="sticky bottom-4 flex flex-col gap-3 rounded-lg border border-border bg-card p-4 shadow-lg sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {profile?.ready_for_research
            ? mode === "beginner"
              ? "Ready to analyze!"
              : "Ready to send to the Research Engine."
            : mode === "beginner"
              ? "Answer the questions above to continue."
              : "Complete the required fields to enable Send to Research."}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {mode === "beginner" ? "Save" : "Save Profile"}
          </Button>
          <Button onClick={handleSendToResearch} disabled={!profile?.ready_for_research || sending}>
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {mode === "beginner" ? "Analyze This Product" : "Send to Research"}
          </Button>
        </div>
      </div>
    </div>
  );
}
