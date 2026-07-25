"use client";

import Link from "next/link";
import { Star, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ReportSummary } from "@/lib/types";

function recommendationVariant(recommendation: string | null) {
  switch (recommendation) {
    case "Launch":
    case "Strong Candidate":
      return "success" as const;
    case "Test First":
    case "Needs Review":
      return "warning" as const;
    case "Reject":
      return "destructive" as const;
    default:
      return "muted" as const;
  }
}

export function ReportRow({
  report,
  selectable,
  selected,
  onToggleSelect,
  onFavorite,
  onDelete,
}: {
  report: ReportSummary;
  selectable?: boolean;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
  onFavorite?: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect?.(report.id)}
            className="h-4 w-4 accent-primary"
          />
        )}
        <div className="min-w-0">
          <Link href={`/reports/${report.id}`} className="truncate text-sm font-medium hover:underline">
            {report.product_name}
          </Link>
          <p className="truncate text-xs text-muted-foreground">
            {report.category ?? "Uncategorized"} · {new Date(report.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge variant={recommendationVariant(report.recommendation)}>{report.recommendation}</Badge>
        {onFavorite && (
          <Button variant="ghost" size="icon" onClick={() => onFavorite(report.id)}>
            <Star className={cn("h-4 w-4", report.is_saved && "fill-warning text-warning")} />
          </Button>
        )}
        {onDelete && (
          <Button variant="ghost" size="icon" onClick={() => onDelete(report.id)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
