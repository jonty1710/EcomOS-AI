function formatKey(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

// Generic, shallow key/value renderer for a module's `data` payload — every
// module (deterministic today, AI later) shares the same ModuleSection shape
// (SRS §4), so one renderer covers all of them (FBP §19 consistency rule).
export function DataList({ data, title }: { data: Record<string, unknown>; title?: string }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;

  return (
    <div>
      {title && <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
        {entries.map(([key, value]) => {
          if (value && typeof value === "object" && !Array.isArray(value)) {
            return (
              <div key={key} className="col-span-full">
                <DataList data={value as Record<string, unknown>} title={formatKey(key)} />
              </div>
            );
          }
          return (
            <div key={key}>
              <dt className="text-xs text-muted-foreground">{formatKey(key)}</dt>
              <dd className="text-sm font-medium">{formatValue(value)}</dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
