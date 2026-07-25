"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiRequestError } from "@/lib/api-client";
import type { ManualResearchRequest } from "@/lib/types";

const initialForm: ManualResearchRequest = {
  product_name: "",
  category_hint: "",
  selling_price: 0,
  buying_price: 0,
  shipping_cost: 0,
  packaging_cost: 0,
  marketplace_fee_pct: 15,
  ad_cost: 0,
  gst_pct: 18,
  return_cost: 0,
  rto_cost: 0,
  weight_grams: undefined,
  material: "",
  supplier_name: "",
  supplier_notes: "",
  competition_notes: "",
  review_notes: "",
};

function NumberField({
  label,
  value,
  onChange,
  suffix,
  required,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  suffix?: string;
  required?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label} {required && <span className="text-destructive">*</span>}
        {suffix && <span className="text-muted-foreground"> ({suffix})</span>}
      </Label>
      <Input
        type="number"
        step="0.01"
        min={0}
        required={required}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
      />
    </div>
  );
}

export default function NewResearchPage() {
  const router = useRouter();
  const [form, setForm] = useState<ManualResearchRequest>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof ManualResearchRequest>(key: K, value: ManualResearchRequest[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const report = await api.submitManualResearch(form);
      router.push(`/reports/${report.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">New Research</h1>
        <p className="text-sm text-muted-foreground">
          Manual Research Workflow — the deterministic engine computes Profit, Margin, ROI, Break-even and a
          preliminary Logistics Risk read from what you enter below. No AI is used in this phase.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Product</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="product_name">
                Product Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="product_name"
                required
                placeholder="e.g. Drawer Organizer"
                value={form.product_name}
                onChange={(e) => set("product_name", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="category_hint">Category hint (optional)</Label>
              <Input
                id="category_hint"
                placeholder="Deterministically detected if left blank"
                value={form.category_hint}
                onChange={(e) => set("category_hint", e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="material">Material</Label>
              <Input
                id="material"
                placeholder="e.g. plastic, glass, metal"
                value={form.material}
                onChange={(e) => set("material", e.target.value)}
              />
            </div>
            <NumberField label="Weight" suffix="grams" value={form.weight_grams} onChange={(v) => set("weight_grams", v)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Financials</CardTitle>
            <CardDescription>Feeds the deterministic Profit & Unit Economics engine (PRS §9).</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <NumberField
              label="Selling Price"
              suffix="₹"
              required
              value={form.selling_price}
              onChange={(v) => set("selling_price", v ?? 0)}
            />
            <NumberField
              label="Buying Price"
              suffix="₹"
              required
              value={form.buying_price}
              onChange={(v) => set("buying_price", v ?? 0)}
            />
            <NumberField label="Shipping Cost" suffix="₹" value={form.shipping_cost} onChange={(v) => set("shipping_cost", v ?? 0)} />
            <NumberField
              label="Packaging Cost"
              suffix="₹"
              value={form.packaging_cost}
              onChange={(v) => set("packaging_cost", v ?? 0)}
            />
            <NumberField
              label="Marketplace Fee"
              suffix="%"
              value={form.marketplace_fee_pct}
              onChange={(v) => set("marketplace_fee_pct", v ?? 0)}
            />
            <NumberField label="Ad Cost" suffix="₹" value={form.ad_cost} onChange={(v) => set("ad_cost", v ?? 0)} />
            <NumberField label="GST" suffix="%" value={form.gst_pct} onChange={(v) => set("gst_pct", v ?? 18)} />
            <NumberField label="Return Cost" suffix="₹" value={form.return_cost} onChange={(v) => set("return_cost", v ?? 0)} />
            <NumberField label="RTO Cost" suffix="₹" value={form.rto_cost} onChange={(v) => set("rto_cost", v ?? 0)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supplier</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="supplier_name">Supplier name</Label>
              <Input id="supplier_name" value={form.supplier_name} onChange={(e) => set("supplier_name", e.target.value)} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="supplier_notes">Supplier notes</Label>
              <Textarea
                id="supplier_notes"
                placeholder="MOQ, lead time, anything you already know — stored as-is, never scored by AI in this phase."
                value={form.supplier_notes}
                onChange={(e) => set("supplier_notes", e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Market Notes</CardTitle>
            <CardDescription>Free text — kept as manual notes, not analyzed until the AI phase.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="competition_notes">Competition notes</Label>
              <Textarea id="competition_notes" value={form.competition_notes} onChange={(e) => set("competition_notes", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="review_notes">Review notes</Label>
              <Textarea id="review_notes" value={form.review_notes} onChange={(e) => set("review_notes", e.target.value)} />
            </div>
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" disabled={submitting} size="lg" className="w-full sm:w-auto">
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Run Deterministic Research
        </Button>
      </form>
    </div>
  );
}
