// Product Timeline and Archive state — tracked entirely in this browser's
// localStorage, not the backend. The backend has no lifecycle/archived
// column on reports (and this redesign is explicitly UX-only — no schema
// changes), so these are personal trackers: useful on this device, but they
// don't sync across devices or browsers. Reports themselves are the source
// of truth for everything else; this file only ever stores small UI state.

export type TimelineStage = "research_started" | "supplier_contacted" | "sample_ordered" | "ready_to_launch" | "launched";

export const TIMELINE_STAGES: { key: TimelineStage; label: string }[] = [
  { key: "research_started", label: "Research Started" },
  { key: "supplier_contacted", label: "Supplier Pending" },
  { key: "sample_ordered", label: "Sample Pending" },
  { key: "ready_to_launch", label: "Ready to Launch" },
  { key: "launched", label: "Launched" },
];

const TIMELINE_KEY = "ecomos_timeline_v1";
const ARCHIVED_KEY = "ecomos_archived_v1";

function readMap(key: string): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(key) ?? "{}");
  } catch {
    return {};
  }
}

function writeMap(key: string, map: Record<string, string>) {
  window.localStorage.setItem(key, JSON.stringify(map));
}

export function getReportStage(reportId: string): TimelineStage {
  const stage = readMap(TIMELINE_KEY)[reportId];
  return (TIMELINE_STAGES.find((s) => s.key === stage)?.key ?? "research_started") as TimelineStage;
}

export function setReportStage(reportId: string, stage: TimelineStage) {
  const map = readMap(TIMELINE_KEY);
  map[reportId] = stage;
  writeMap(TIMELINE_KEY, map);
}

export function isArchived(reportId: string): boolean {
  return readMap(ARCHIVED_KEY)[reportId] === "1";
}

export function setArchived(reportId: string, archived: boolean) {
  const map = readMap(ARCHIVED_KEY);
  if (archived) map[reportId] = "1";
  else delete map[reportId];
  writeMap(ARCHIVED_KEY, map);
}

export function getArchivedIds(): Set<string> {
  return new Set(Object.keys(readMap(ARCHIVED_KEY)));
}

// Bridge for values the wizard collected but the Report API doesn't echo
// back (e.g. buying_price, used to caption the Break-Even card with a real
// investment estimate right after a fresh research run). Session-scoped,
// keyed by report id, and deliberately best-effort — older/reloaded reports
// simply won't have an entry, and every consumer must handle that.
const WIZARD_CONTEXT_KEY = "ecomos_wizard_context_v1";

export interface WizardReportContext {
  buying_price: number;
}

export function stashWizardContext(reportId: string, ctx: WizardReportContext) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(`${WIZARD_CONTEXT_KEY}:${reportId}`, JSON.stringify(ctx));
  } catch {
    // sessionStorage unavailable — non-fatal, the Break-Even card just omits the caption
  }
}

export function readWizardContext(reportId: string): WizardReportContext | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(`${WIZARD_CONTEXT_KEY}:${reportId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
