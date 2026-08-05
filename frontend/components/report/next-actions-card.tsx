import { CircleCheck, Package, Phone, Receipt, Search, ShieldCheck } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReportResponse } from "@/lib/types";

// Translates the backend's real manual_verification_checklist (PRS §17 —
// nothing on this list is invented, every item is something the Research
// Engine actually flagged) into plain, task-shaped language. Never adds
// items the backend didn't produce.
const ACTION_MAP: { match: string; icon: typeof Phone; label: string; detail: string }[] = [
  {
    match: "Supplier contacted and terms confirmed directly.",
    icon: Phone,
    label: "Call Your Supplier",
    detail: "Confirm pricing and terms directly before you commit.",
  },
  {
    match: "GST category confirmed with a qualified professional.",
    icon: Receipt,
    label: "Confirm Tax With an Expert",
    detail: "Get your GST category checked by a qualified professional.",
  },
  {
    match: "Pricing confirmed against live marketplace listings.",
    icon: Search,
    label: "Check Live Prices Online",
    detail: "Make sure your numbers still match what's selling today.",
  },
  {
    match: "Trademark / brand-name clearance searched independently.",
    icon: ShieldCheck,
    label: "Check the Trademark",
    detail: "Search independently that the brand name is free to use.",
  },
  {
    match: "Packaging tested — high-fragility item flagged by the preliminary logistics read.",
    icon: Package,
    label: "Test Your Packaging",
    detail: "This item is fragile — test packaging before you ship at scale.",
  },
];

export function NextActionsCard({ report }: { report: ReportResponse }) {
  const items = report.manual_verification_checklist
    .slice(0, 3)
    .map((text) => ACTION_MAP.find((a) => a.match === text) ?? { icon: CircleCheck, label: text, detail: "" });

  if (items.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Next Actions</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        {items.map((item, i) => {
          const Icon = item.icon;
          return (
            <div key={i} className="flex flex-col items-start gap-2 rounded-lg border border-border p-4">
              <Icon className="h-5 w-5 text-primary" />
              <p className="text-sm font-medium">{item.label}</p>
              {item.detail && <p className="text-xs text-muted-foreground">{item.detail}</p>}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
