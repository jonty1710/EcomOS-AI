import type { FieldDefinition } from "./types";

export type ExperienceMode = "beginner" | "professional" | "enterprise";

// Product Name is always shown as the primary entry field — it's the thing
// being named, not really "a field to fill in a form" in a seller's mental
// model — so it's counted separately from the "6 questions" framing.
export const BEGINNER_FIELD_KEYS = [
  "selling_price",
  "buying_price",
  "shipping_cost",
  "packaging_cost",
  "weight_grams",
  "supplier_name",
];

// 20 fields total, including Product Name and every backend-required field —
// curated across all 5 sections so Professional mode still feels complete
// without the long tail of rarely-used fields.
export const PROFESSIONAL_FIELD_KEYS = [
  "product_name",
  "category",
  "brand",
  "sku",
  "selling_price",
  "buying_price",
  "shipping_cost",
  "packaging_cost",
  "mrp",
  "gst_pct",
  "marketplace_fee_pct",
  "ad_cost",
  "weight_grams",
  "material",
  "competition_notes",
  "review_notes",
  "average_rating",
  "supplier_name",
  "moq",
  "lead_time_days",
];

export const MODE_META: Record<ExperienceMode, { label: string; shortDescription: string; description: string }> = {
  beginner: {
    label: "Beginner",
    shortDescription: "6 quick questions",
    description: "Just the essentials — answer 6 quick questions and you're done.",
  },
  professional: {
    label: "Professional",
    shortDescription: "20 fields",
    description: "More control — 20 fields covering pricing, sourcing, and market notes.",
  },
  enterprise: {
    label: "Enterprise",
    shortDescription: "Everything",
    description: "Everything — the full field set, data sources, and audit trail.",
  },
};

/** Calculated fields are never "asked" — they're always shown as results in
 * every mode once their inputs are available, so they pass through
 * regardless of which input fields the current mode requests.
 */
export function getVisibleFields(mode: ExperienceMode, allFields: FieldDefinition[]): FieldDefinition[] {
  if (mode === "enterprise") return allFields;
  const keySet = new Set(mode === "professional" ? PROFESSIONAL_FIELD_KEYS : ["product_name", ...BEGINNER_FIELD_KEYS]);
  return allFields.filter((f) => keySet.has(f.key) || f.collection_type === "calculated");
}
