import { getSessionId } from "./session";
import type {
  ApiError,
  CompareResponse,
  DataLineageReport,
  FieldRegistryResponse,
  ManualResearchRequest,
  ProductProfile,
  ProductProfileSummary,
  ProvenanceEventRecord,
  ReportResponse,
  ReportSummary,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let body: ApiError | null = null;
    try {
      body = await res.json();
    } catch {
      // no JSON body
    }
    throw new ApiRequestError(
      res.status,
      body?.error?.code ?? "UNKNOWN_ERROR",
      body?.error?.message ?? "Something went wrong talking to the server. Please try again.",
    );
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  submitManualResearch: (payload: ManualResearchRequest) =>
    request<ReportResponse>("/research/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listReports: (savedOnly = false) =>
    request<ReportSummary[]>(`/reports?saved=${savedOnly}`),

  getReport: (id: string) => request<ReportResponse>(`/reports/${id}`),

  deleteReport: (id: string) => request<void>(`/reports/${id}`, { method: "DELETE" }),

  toggleFavorite: (id: string) =>
    request<ReportResponse>(`/reports/${id}/favorite`, { method: "POST" }),

  compareReports: (ids: string[]) =>
    request<CompareResponse>(`/reports/compare?ids=${ids.join(",")}`),

  // --- Data Collection Engine (Phase 2) ---

  getFieldRegistry: () => request<FieldRegistryResponse>("/collection/field-registry"),

  previewProfile: (payload: Record<string, unknown>) =>
    request<ProductProfile>("/collection/preview", { method: "POST", body: JSON.stringify(payload) }),

  createProfile: (payload: Record<string, unknown>) =>
    request<ProductProfile>("/collection/profiles", { method: "POST", body: JSON.stringify(payload) }),

  updateProfile: (id: string, payload: Record<string, unknown>) =>
    request<ProductProfile>(`/collection/profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),

  listProfiles: () => request<ProductProfileSummary[]>("/collection/profiles"),

  getProfile: (id: string) => request<ProductProfile>(`/collection/profiles/${id}`),

  getProfileVersions: (id: string) => request<ProductProfileSummary[]>(`/collection/profiles/${id}/versions`),

  deleteProfile: (id: string) => request<void>(`/collection/profiles/${id}`, { method: "DELETE" }),

  sendProfileToResearch: (id: string) =>
    request<ReportResponse>(`/collection/profiles/${id}/send-to-research`, { method: "POST" }),

  // --- Data Source Manager (Phase 4) ---

  getLineage: (profileId: string) => request<DataLineageReport>(`/provenance/profiles/${profileId}/lineage`),

  rejectField: (profileId: string, fieldKey: string, note?: string) =>
    request<ProvenanceEventRecord>(`/provenance/profiles/${profileId}/fields/${fieldKey}/reject`, {
      method: "POST",
      body: JSON.stringify({ note: note ?? null }),
    }),

  clearFieldRejection: (profileId: string, fieldKey: string) =>
    request<ProvenanceEventRecord>(`/provenance/profiles/${profileId}/fields/${fieldKey}/clear-rejection`, {
      method: "POST",
    }),

  requestFieldRefresh: (profileId: string, fieldKey: string) =>
    request<ProvenanceEventRecord>(`/provenance/profiles/${profileId}/fields/${fieldKey}/request-refresh`, {
      method: "POST",
    }),
};
