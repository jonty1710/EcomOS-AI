"use client";

import { useExperienceMode } from "@/lib/experience-mode";
import { MODE_META, type ExperienceMode } from "@/lib/field-modes";
import { cn } from "@/lib/utils";

const MODES: ExperienceMode[] = ["beginner", "professional", "enterprise"];

export function ModeSelector({ compact = false }: { compact?: boolean }) {
  const { mode, setMode } = useExperienceMode();

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-lg border border-border bg-card p-3",
        !compact && "sm:flex-row sm:items-center sm:justify-between",
      )}
    >
      <div className="flex gap-1 rounded-md bg-secondary p-1">
        {MODES.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={cn(
              "rounded px-3 py-1.5 text-sm font-medium transition-colors",
              mode === m ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {MODE_META[m].label}
          </button>
        ))}
      </div>
      {!compact && <p className="text-xs text-muted-foreground">{MODE_META[mode].description}</p>}
    </div>
  );
}
