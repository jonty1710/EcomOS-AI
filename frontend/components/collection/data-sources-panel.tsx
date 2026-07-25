"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, Clock, RefreshCw, ShieldAlert, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { api, ApiRequestError } from "@/lib/api-client";
import type { DataLineageReport, FieldLineage, VerificationStatus, DsmSourceType } from "@/lib/types";

function verificationBadge(status: VerificationStatus) {
  switch (status) {
    case "verified":
      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="h-3 w-3" />
          Verified
        </Badge>
      );
    case "pending":
      return (
        <Badge variant="warning" className="gap-1">
          <ShieldAlert className="h-3 w-3" />
          Pending Verification
        </Badge>
      );
    case "rejected":
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Rejected
        </Badge>
      );
    default:
      return <Badge variant="muted">Not Required</Badge>;
  }
}

function sourceTypeBadge(type: DsmSourceType) {
  const labels: Record<DsmSourceType, string> = {
    auto_collected: "Auto Collected",
    user_entered: "User Entered",
    calculated: "Calculated",
    imported: "Imported",
    unknown: "Unknown",
  };
  return <Badge variant={type === "unknown" ? "muted" : "outline"}>{labels[type]}</Badge>;
}

function pctLabel(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function DataSourcesPanel({ profileId }: { profileId: string }) {
  const [report, setReport] = useState<DataLineageReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    api.getLineage(profileId).then(setReport).catch((e: ApiRequestError) => setError(e.message));
  }

  useEffect(reload, [profileId]);

  async function handleAction(fieldKey: string, action: "reject" | "clear" | "refresh", note?: string) {
    if (action === "reject") await api.rejectField(profileId, fieldKey, note);
    if (action === "clear") await api.clearFieldRejection(profileId, fieldKey);
    if (action === "refresh") await api.requestFieldRefresh(profileId, fieldKey);
    reload();
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertTriangle className="h-4 w-4" />
        {error}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  const bySection: Record<string, FieldLineage[]> = {};
  for (const f of report.fields) {
    (bySection[f.section] ??= []).push(f);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Data Source Summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Traceable" value={`${report.summary.traceable_fields}/${report.summary.total_fields}`} />
          <Stat label="Verified" value={String(report.summary.verified_fields)} />
          <Stat label="Pending Verification" value={String(report.summary.pending_verification_fields)} />
          <Stat label="Rejected" value={String(report.summary.rejected_fields)} />
          <Stat label="Expired" value={String(report.summary.expired_fields)} />
          <Stat label="Avg Reliability" value={pctLabel(report.summary.average_reliability)} />
          <Stat label="Avg Confidence" value={pctLabel(report.summary.average_confidence)} />
        </CardContent>
      </Card>

      {Object.entries(bySection).map(([section, fields]) => (
        <Card key={section}>
          <CardHeader>
            <CardTitle className="text-sm">{section}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {fields.map((f) => (
              <FieldSourceRowWrapper key={f.field_key} field={f} onAction={handleAction} />
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

// Thin wrapper so FieldSourceRow's action handlers can call back up with the
// field_key without needing profileId threaded through every prop.
function FieldSourceRowWrapper({
  field,
  onAction,
}: {
  field: FieldLineage;
  onAction: (fieldKey: string, action: "reject" | "clear" | "refresh", note?: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const p = field.provenance;

  async function run(action: "reject" | "clear" | "refresh") {
    setBusy(true);
    try {
      let note: string | undefined;
      if (action === "reject") {
        note = window.prompt("Why is this value being rejected? (optional)") ?? undefined;
      }
      onAction(field.field_key, action, note);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-md border border-border">
      <div className="flex cursor-pointer flex-wrap items-center justify-between gap-2 p-3" onClick={() => setOpen((v) => !v)}>
        <div className="min-w-0">
          <p className="text-sm font-medium">{field.label}</p>
          <p className="truncate text-xs text-muted-foreground">
            {field.value === null || field.value === undefined || field.value === "" ? "No value" : String(field.value)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {sourceTypeBadge(p.source_type)}
          {verificationBadge(p.verification_status)}
          {p.expiry?.is_expired && (
            <Badge variant="warning" className="gap-1">
              <Clock className="h-3 w-3" />
              Expired
            </Badge>
          )}
          <span className="text-xs text-muted-foreground">Reliability {pctLabel(p.reliability_score)}</span>
          <span className="text-xs text-muted-foreground">Confidence {pctLabel(p.confidence_score)}</span>
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
        </div>
      </div>

      {open && (
        <div className="space-y-3 border-t border-border p-3 text-sm">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted-foreground">Source</dt>
              <dd className="font-medium">{p.source_name ?? "Unknown"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Collection Method</dt>
              <dd className="font-medium">{p.collection_method ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Intended Source (policy)</dt>
              <dd className="font-medium">{p.intended_source_hint}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Last Updated</dt>
              <dd className="font-medium">{p.last_updated ? new Date(p.last_updated).toLocaleString() : "—"}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Refresh Strategy</dt>
              <dd className="font-medium capitalize">{p.refresh_strategy.replace(/_/g, " ")}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Expiry</dt>
              <dd className="font-medium">
                {p.expiry?.ttl_days ? `${p.expiry.ttl_days} day TTL${p.expiry.is_expired ? " — expired" : ""}` : "No expiry policy"}
              </dd>
            </div>
            <div className="col-span-full">
              <dt className="text-xs text-muted-foreground">Manual Verification Required</dt>
              <dd className="font-medium">{p.requires_manual_verification ? "Yes" : "No"}</dd>
            </div>
          </dl>

          {field.audit_trail.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Audit Trail</p>
              <ul className="space-y-1">
                {field.audit_trail.map((e, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{e.event_type.replace(/_/g, " ")}</span>{" "}
                    — {new Date(e.timestamp).toLocaleString()} ({e.actor})
                    {e.notes && <span> — {e.notes}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            {p.verification_status === "rejected" ? (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => run("clear")}>
                Clear Rejection
              </Button>
            ) : (
              <Button size="sm" variant="outline" disabled={busy} onClick={() => run("reject")}>
                <XCircle className="h-3.5 w-3.5" />
                Reject Value
              </Button>
            )}
            <Button size="sm" variant="outline" disabled={busy} onClick={() => run("refresh")}>
              <RefreshCw className="h-3.5 w-3.5" />
              Request Refresh
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
