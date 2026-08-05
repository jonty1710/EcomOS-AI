"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, Search, Sparkles, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { InfoTooltip } from "@/components/ui/tooltip";
import { api, ApiRequestError } from "@/lib/api-client";
import { stashWizardContext } from "@/lib/local-tracking";
import type { ProductProfile } from "@/lib/types";

type Step = "identity" | "autofill" | "questions" | "submitting";

const STEP_ORDER: Step[] = ["identity", "autofill", "questions", "submitting"];

function StepProgress({ step }: { step: Step }) {
  const idx = STEP_ORDER.indexOf(step);
  return (
    <div className="mb-8 flex items-center justify-center gap-2">
      {STEP_ORDER.slice(0, 3).map((s, i) => (
        <div
          key={s}
          className={`h-1.5 w-12 rounded-full transition-colors ${i <= idx ? "bg-primary" : "bg-secondary"}`}
        />
      ))}
    </div>
  );
}

function numOrUndefined(raw: string): number | undefined {
  if (raw.trim() === "") return undefined;
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

export function ResearchWizard() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("identity");
  const [error, setError] = useState<string | null>(null);

  // Step 1 — "Duplicate Research" quick action pre-fills just the product
  // name (that's the only field a Report response carries back; buying
  // price, weight etc. aren't preserved on a Report, so they're re-asked).
  // Read directly from window.location rather than useSearchParams to avoid
  // a Suspense-boundary requirement for what's otherwise a fully client page.
  const [entry, setEntry] = useState("");
  useEffect(() => {
    const name = new URLSearchParams(window.location.search).get("name");
    if (name) setEntry(name);
  }, []);
  const [productName, setProductName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const looksLikeUrl = /^https?:\/\//i.test(entry.trim());

  // Step 2 (autofill result)
  const [preview, setPreview] = useState<ProductProfile | null>(null);
  const [autofillLoading, setAutofillLoading] = useState(true);

  // Step 3
  const [buyingPrice, setBuyingPrice] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [shippingCost, setShippingCost] = useState("");
  const [packagingCost, setPackagingCost] = useState("");
  const [weightGrams, setWeightGrams] = useState("");
  const [notes, setNotes] = useState("");
  const [q3Profile, setQ3Profile] = useState<ProductProfile | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleEntryContinue() {
    if (looksLikeUrl) setSourceUrl(entry.trim());
    else setProductName(entry.trim());
    setStep("autofill");
  }

  useEffect(() => {
    if (step !== "autofill") return;
    setAutofillLoading(true);
    const started = Date.now();
    api
      .previewProfile({
        product_name: productName || entry,
        source_url: sourceUrl || undefined,
        selling_price: numOrUndefined(sellingPrice),
      })
      .then((p) => setPreview(p))
      .catch(() => setPreview(null))
      .finally(() => {
        // A short, real minimum delay — the analysis IS happening (a real API
        // call), this just keeps the loading state from flashing by too fast
        // to register as "we looked something up for you."
        const elapsed = Date.now() - started;
        setTimeout(() => setAutofillLoading(false), Math.max(0, 900 - elapsed));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  useEffect(() => {
    if (step !== "questions") return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      api
        .previewProfile({
          product_name: productName || entry,
          source_url: sourceUrl || undefined,
          selling_price: numOrUndefined(sellingPrice),
          buying_price: numOrUndefined(buyingPrice),
          supplier_name: supplierName || undefined,
          shipping_cost: numOrUndefined(shippingCost),
          packaging_cost: numOrUndefined(packagingCost),
          weight_grams: numOrUndefined(weightGrams),
          supplier_notes: notes || undefined,
        })
        .then(setQ3Profile)
        .catch(() => {
          // preview failures are non-fatal — nothing has been saved yet
        });
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, buyingPrice, supplierName, shippingCost, packagingCost, weightGrams, notes]);

  const requiredFilled =
    buyingPrice.trim() !== "" && supplierName.trim() !== "" && shippingCost.trim() !== "" &&
    packagingCost.trim() !== "" && weightGrams.trim() !== "";
  const hasBlockingErrors = q3Profile ? Object.values(q3Profile.fields).some((f) => f.errors.length > 0) : false;

  function errorsFor(key: string): string[] {
    return q3Profile?.fields[key]?.errors ?? [];
  }

  async function handleGenerateReport() {
    setStep("submitting");
    setError(null);
    try {
      const payload = {
        product_name: productName || entry,
        source_url: sourceUrl || undefined,
        selling_price: numOrUndefined(sellingPrice),
        buying_price: numOrUndefined(buyingPrice),
        supplier_name: supplierName || undefined,
        shipping_cost: numOrUndefined(shippingCost),
        packaging_cost: numOrUndefined(packagingCost),
        weight_grams: numOrUndefined(weightGrams),
        supplier_notes: notes || undefined,
      };
      const profile = await api.createProfile(payload);
      const report = await api.sendProfileToResearch(profile.id);
      const bp = numOrUndefined(buyingPrice);
      if (bp) stashWizardContext(report.id, { buying_price: bp });
      router.push(`/reports/${report.id}`);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Something went wrong generating your report.");
      setStep("questions");
    }
  }

  if (step === "identity") {
    return (
      <div className="mx-auto max-w-lg py-10">
        <StepProgress step={step} />
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold">What product do you want to research?</h1>
          <p className="mt-1 text-sm text-muted-foreground">Paste a product link, or just type its name.</p>
        </div>
        <Card>
          <CardContent className="space-y-4 py-6">
            <div className="space-y-1.5">
              <Input
                autoFocus
                className="h-12 text-base"
                placeholder="e.g. Ceramic Coffee Mug, or https://amazon.in/..."
                value={entry}
                onChange={(e) => setEntry(e.target.value)}
              />
            </div>
            {looksLikeUrl && (
              <div className="space-y-1.5">
                <Label htmlFor="product_name">
                  We can&apos;t read data from links yet — what&apos;s this product called?
                </Label>
                <Input
                  id="product_name"
                  className="h-12 text-base"
                  placeholder="Product name"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="selling_price">What will you sell it for? (₹)</Label>
              <Input
                id="selling_price"
                type="number"
                step="any"
                className="h-12 text-base"
                placeholder="e.g. 499"
                value={sellingPrice}
                onChange={(e) => setSellingPrice(e.target.value)}
              />
            </div>
            <Button
              size="lg"
              className="h-12 w-full text-base"
              disabled={
                (looksLikeUrl ? productName.trim() === "" : entry.trim() === "") || sellingPrice.trim() === ""
              }
              onClick={handleEntryContinue}
            >
              <Search className="h-4 w-4" />
              Start Research
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (step === "autofill") {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <StepProgress step={step} />
        {autofillLoading ? (
          <div className="space-y-4">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Looking up what we already know about this product...</p>
          </div>
        ) : (
          <div className="space-y-5">
            <Sparkles className="mx-auto h-8 w-8 text-primary" />
            <div>
              <p className="font-medium">
                {preview?.detected_marketplace ? (
                  <>Detected marketplace: <span className="capitalize">{preview.detected_marketplace}</span></>
                ) : (
                  "We're ready to research this product."
                )}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {preview?.fields.category?.value
                  ? `Category detected: ${String(preview.fields.category.value)}. `
                  : "We couldn't auto-detect a category — no problem, that won't stop your research. "}
                Just a few quick questions and we&apos;ll generate your report.
              </p>
            </div>
            <Button size="lg" className="h-12 w-full max-w-xs text-base" onClick={() => setStep("questions")}>
              Continue
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (step === "submitting") {
    return (
      <div className="mx-auto max-w-lg py-24 text-center">
        <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
        <p className="font-medium">Generating your report...</p>
        <p className="mt-1 text-sm text-muted-foreground">Running your numbers through the Research Engine.</p>
      </div>
    );
  }

  // step === "questions"
  return (
    <div className="mx-auto max-w-lg py-10">
      <StepProgress step="questions" />
      <div className="mb-6 text-center">
        <h1 className="text-2xl font-semibold">A few quick questions</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Six quick answers about <span className="font-medium text-foreground">{productName || entry}</span> and we&apos;ll do the rest.
        </p>
      </div>
      <Card>
        <CardContent className="space-y-4 py-6">
          <div className="space-y-1.5">
            <Label htmlFor="buying_price">Buying Price (₹)</Label>
            <Input
              id="buying_price"
              type="number"
              step="any"
              className="h-11"
              placeholder="What you pay your supplier, per unit"
              value={buyingPrice}
              onChange={(e) => setBuyingPrice(e.target.value)}
            />
            {errorsFor("buying_price").map((e) => (
              <p key={e} className="flex items-center gap-1 text-xs text-destructive">
                <XCircle className="h-3 w-3 shrink-0" />
                {e}
              </p>
            ))}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="supplier_name">Supplier Name</Label>
            <Input
              id="supplier_name"
              className="h-11"
              placeholder="Who you'd buy this from"
              value={supplierName}
              onChange={(e) => setSupplierName(e.target.value)}
            />
            {errorsFor("supplier_name").map((e) => (
              <p key={e} className="flex items-center gap-1 text-xs text-destructive">
                <XCircle className="h-3 w-3 shrink-0" />
                {e}
              </p>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="shipping_cost" className="flex items-center gap-1">
                Shipping Cost (₹)
                <InfoTooltip text="Roughly what it costs to ship one unit to your customer." />
              </Label>
              <Input
                id="shipping_cost"
                type="number"
                step="any"
                className="h-11"
                placeholder="Approx."
                value={shippingCost}
                onChange={(e) => setShippingCost(e.target.value)}
              />
              {errorsFor("shipping_cost").map((e) => (
                <p key={e} className="text-xs text-destructive">{e}</p>
              ))}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="packaging_cost">Packaging Cost (₹)</Label>
              <Input
                id="packaging_cost"
                type="number"
                step="any"
                className="h-11"
                placeholder="Approx."
                value={packagingCost}
                onChange={(e) => setPackagingCost(e.target.value)}
              />
              {errorsFor("packaging_cost").map((e) => (
                <p key={e} className="text-xs text-destructive">{e}</p>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="weight_grams" className="flex items-center gap-1">
              Weight (grams)
              <InfoTooltip text="Doesn't need to be exact — a close estimate is fine." />
            </Label>
            <Input
              id="weight_grams"
              type="number"
              step="any"
              className="h-11"
              placeholder="Approx."
              value={weightGrams}
              onChange={(e) => setWeightGrams(e.target.value)}
            />
            {errorsFor("weight_grams").map((e) => (
              <p key={e} className="text-xs text-destructive">{e}</p>
            ))}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="Anything else worth remembering about this product or supplier?"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            size="lg"
            className="h-12 w-full text-base"
            disabled={!requiredFilled || hasBlockingErrors}
            onClick={handleGenerateReport}
          >
            <Sparkles className="h-4 w-4" />
            Generate Report
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
