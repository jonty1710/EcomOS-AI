// Mirrors backend/app/models/schemas.py. Keep in sync manually in Phase 1
// (no codegen yet — see README "Next recommended milestone").

export type ModuleStatus =
  | "completed"
  | "unscored_insufficient_evidence"
  | "planned_for_ai_phase"
  | "failed";

export interface SourceRef {
  type: "manual" | "deterministic" | "connector" | "web_search" | "llm_reasoning";
  name: string;
  url?: string | null;
  retrieved_at?: string | null;
}

export interface ModuleSection {
  agent_type: string;
  label: string;
  status: ModuleStatus;
  data: Record<string, unknown>;
  signals: Record<string, unknown>;
  reasoning: string | null;
  confidence_score: number | null;
  evidence_score: number | null;
  sub_score: number | null;
  sources: SourceRef[];
  requires_manual_verification: boolean;
  weight_in_decision_engine: number;
  unavailable_reason: string | null;
}

export interface ReportResponse {
  id: string;
  product_name: string;
  category: string | null;
  status: string;
  research_mode: string;
  overall_score: number | null;
  risk_level: string | null;
  recommendation: string | null;
  is_saved: boolean;
  sections: ModuleSection[];
  manual_verification_checklist: string[];
  research_completeness_pct: number;
  recommendation_explanation: string;
  created_at: string;
  completed_at: string | null;
}

export interface ReportSummary {
  id: string;
  product_name: string;
  category: string | null;
  status: string;
  overall_score: number | null;
  recommendation: string | null;
  is_saved: boolean;
  created_at: string;
}

export interface CompareResponse {
  reports: ReportResponse[];
  dimensions: string[];
}

export interface ManualResearchRequest {
  product_name: string;
  category_hint?: string;
  selling_price: number;
  buying_price: number;
  shipping_cost?: number;
  packaging_cost?: number;
  marketplace_fee_pct?: number;
  ad_cost?: number;
  gst_pct?: number;
  return_cost?: number;
  rto_cost?: number;
  weight_grams?: number;
  material?: string;
  supplier_name?: string;
  supplier_notes?: string;
  competition_notes?: string;
  review_notes?: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

// --- Data Collection Engine (Phase 2) — mirrors backend/app/collection/schemas.py ---

export type FieldDataType = "text" | "long_text" | "number" | "boolean" | "enum";
export type FieldCollectionType = "auto_detect" | "user_input" | "calculated";
export type EffectiveClassification =
  | "auto_detect"
  | "user_input_required"
  | "manual_verification_required"
  | "calculated";
export type FieldStatus = "filled" | "missing" | "invalid";

export interface FieldDefinition {
  key: string;
  label: string;
  section: string;
  data_type: FieldDataType;
  collection_type: FieldCollectionType;
  requires_manual_verification: boolean;
  required: boolean;
  source_hint: string;
  help_text: string | null;
  unit: string | null;
  enum_options: string[] | null;
  min_value: number | null;
  max_value: number | null;
}

export interface FieldRegistryResponse {
  sections: string[];
  fields: FieldDefinition[];
}

export interface FieldValue {
  key: string;
  value: unknown;
  status: FieldStatus;
  effective_classification: EffectiveClassification;
  confidence: number | null;
  verified: boolean;
  source: string;
  errors: string[];
  warnings: string[];
}

export interface DataQualityScore {
  completeness_pct: number;
  validation_pct: number;
  confidence_pct: number;
  verification_pending_pct: number;
}

export interface ProductProfile {
  id: string;
  session_id: string;
  product_name: string;
  source_url: string | null;
  detected_marketplace: string | null;
  version: number;
  previous_version_id: string | null;
  fields: Record<string, FieldValue>;
  cost_structure: Record<string, number>;
  data_quality: DataQualityScore;
  missing_required: string[];
  missing_optional: string[];
  ready_for_research: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductProfileSummary {
  id: string;
  product_name: string;
  version: number;
  completeness_pct: number;
  ready_for_research: boolean;
  created_at: string;
  updated_at: string;
}

// --- Data Source Manager (Phase 4) — mirrors backend/app/provenance/schemas.py ---

export type DsmSourceType = "auto_collected" | "user_entered" | "calculated" | "imported" | "unknown";
export type VerificationStatus = "not_required" | "pending" | "verified" | "rejected";
export type RefreshStrategy = "never" | "on_edit" | "periodic" | "on_demand" | "manual_only";

export interface ExpiryInfo {
  ttl_days: number | null;
  expires_at: string | null;
  is_expired: boolean;
  checked_at: string;
}

export interface AuditTrailEntry {
  timestamp: string;
  event_type: string;
  field_key: string;
  previous_value: unknown;
  new_value: unknown;
  actor: string;
  notes: string | null;
  profile_version: number | null;
}

export interface FieldProvenance {
  field_key: string;
  source_type: DsmSourceType;
  source_name: string | null;
  collection_method: string | null;
  intended_source_hint: string;
  reliability_score: number | null;
  confidence_score: number | null;
  last_updated: string | null;
  verification_status: VerificationStatus;
  refresh_strategy: RefreshStrategy;
  expiry: ExpiryInfo | null;
  requires_manual_verification: boolean;
}

export interface FieldLineage {
  field_key: string;
  label: string;
  section: string;
  value: unknown;
  provenance: FieldProvenance;
  audit_trail: AuditTrailEntry[];
}

export interface LineageSummary {
  total_fields: number;
  traceable_fields: number;
  unknown_fields: number;
  verified_fields: number;
  pending_verification_fields: number;
  rejected_fields: number;
  expired_fields: number;
  average_reliability: number | null;
  average_confidence: number | null;
  source_type_breakdown: Record<string, number>;
}

export interface DataLineageReport {
  profile_id: string;
  product_name: string;
  profile_version: number;
  generated_at: string;
  fields: FieldLineage[];
  summary: LineageSummary;
}

export interface ProvenanceEventRecord {
  id: string;
  profile_id: string;
  field_key: string;
  event_type: string;
  note: string | null;
  actor: string;
  created_at: string;
}
