// Plain-language overrides for Beginner/Professional mode, per the "ChatGPT
// simple, not engineer jargon" redesign. Enterprise mode keeps the technical
// vocabulary from the field registry / backend as-is — that audience wants
// precision, not simplification. Nothing here changes what a field IS, only
// what it's called and how it's explained.

export const FRIENDLY_FIELD_LABELS: Record<string, string> = {
  marketplace_fee_pct: "Marketplace Charges",
  gst_pct: "Tax (GST) %",
  hsn_code: "Tax Code (HSN)",
  weight_grams: "Approx. Weight",
  shipping_cost: "Approx. Shipping Cost",
  packaging_cost: "Approx. Packaging Cost",
  fragility: "Breakable Risk",
  ad_cost: "Advertising Spend",
  moq: "Minimum Order Quantity",
  lead_time_days: "Supplier Lead Time",
  roi_pct: "Return on Investment",
  breakeven_units: "Break-Even Point",
};

export const FRIENDLY_FIELD_TOOLTIPS: Record<string, string> = {
  marketplace_fee_pct: "The cut the marketplace (Amazon, Flipkart, etc.) takes from every sale.",
  gst_pct: "The Goods & Services Tax rate that applies to this product.",
  weight_grams: "Doesn't need to be exact — a close estimate is fine to start.",
  fragility: "How likely this product is to break or get damaged in shipping.",
  roi_pct: "For every rupee you spend buying stock, how much you get back as profit.",
  breakeven_units: "How many units you need to sell before you've earned back what you spent.",
  moq: "The smallest quantity your supplier will let you order at once.",
  supplier_name: "Who you'd buy this product from in bulk.",
};

/** Falls back to the backend label when there's no friendly override. */
export function friendlyFieldLabel(key: string, backendLabel: string, mode: "beginner" | "professional" | "enterprise"): string {
  if (mode === "enterprise") return backendLabel;
  return FRIENDLY_FIELD_LABELS[key] ?? backendLabel;
}

// Metric names shown on quality/confidence panels — same simplification rule.
export const FRIENDLY_METRIC_LABELS = {
  completeness: "Information Available",
  researchCompleteness: "Information Available",
  confidence: "How Reliable Is This Report?",
  validation: "Data Checks Passed",
  verificationPending: "Still Needs Your Confirmation",
} as const;

export const RECOMMENDATION_COPY: Record<
  string,
  { label: string; emoji: string; sentence: (productName: string) => string; tone: "launch" | "test" | "wait" | "reject" | "unknown" }
> = {
  Launch: {
    label: "Launch",
    emoji: "🟢",
    sentence: (name) => `${name} looks like a strong opportunity based on what we could calculate.`,
    tone: "launch",
  },
  "Strong Candidate": {
    label: "Launch",
    emoji: "🟢",
    sentence: (name) => `${name} looks like a strong opportunity based on what we could calculate.`,
    tone: "launch",
  },
  "Test First": {
    label: "Test First",
    emoji: "🟡",
    sentence: () => "The numbers are promising, but a few things are worth checking before you commit.",
    tone: "test",
  },
  "Needs Review": {
    label: "Test First",
    emoji: "🟡",
    sentence: () => "The numbers are promising, but a few things are worth checking before you commit.",
    tone: "test",
  },
  Reject: {
    label: "Reject",
    emoji: "🔴",
    sentence: () => "The numbers we could calculate don't support this product right now.",
    tone: "reject",
  },
};

export const INSUFFICIENT_DATA_COPY = {
  label: "Needs More Research",
  emoji: "🟠",
  sentence:
    "We don't have enough automated evidence yet to give you a full Launch/Reject call — that part of the system is still being built. Here's everything we could calculate from your numbers below.",
  tone: "wait" as const,
};
