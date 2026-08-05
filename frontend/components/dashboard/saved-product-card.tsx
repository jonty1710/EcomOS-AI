import Link from "next/link";
import { Star, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { INSUFFICIENT_DATA_COPY, RECOMMENDATION_COPY } from "@/lib/friendly-labels";
import { getProfitExpectedCase } from "@/lib/report-helpers";
import { cn } from "@/lib/utils";
import type { ReportResponse } from "@/lib/types";

export function SavedProductCard({
  report,
  onFavorite,
  onDelete,
}: {
  report: ReportResponse;
  onFavorite?: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  const copy = report.recommendation ? RECOMMENDATION_COPY[report.recommendation] : undefined;
  const resolved = copy ?? INSUFFICIENT_DATA_COPY;
  const profit = getProfitExpectedCase(report);

  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div className="flex items-start justify-between gap-2">
          <Link href={`/reports/${report.id}`} className="min-w-0">
            <p className="truncate font-medium hover:underline">{report.product_name}</p>
            <p className="text-xs text-muted-foreground">
              {report.category ?? "Uncategorized"} · {new Date(report.created_at).toLocaleDateString()}
            </p>
          </Link>
          <span className="shrink-0 text-xl leading-none">{resolved.emoji}</span>
        </div>

        <div className="flex items-center justify-between">
          <Badge variant="muted">{resolved.label}</Badge>
          {profit && (
            <span className={cn("text-sm font-semibold", profit.net_profit >= 0 ? "text-success" : "text-destructive")}>
              ₹{profit.net_profit.toLocaleString("en-IN")} profit
            </span>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border pt-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/reports/${report.id}`}>Open</Link>
          </Button>
          <div className="flex items-center gap-1">
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
      </CardContent>
    </Card>
  );
}
