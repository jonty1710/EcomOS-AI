const SESSION_STORAGE_KEY = "ecomos_session_id";

// Anonymous session id, generated once per browser and persisted (SRS §18).
// No login, no accounts.
export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(SESSION_STORAGE_KEY, id);
  }
  return id;
}
