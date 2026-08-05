"use client";

import { useState, type ReactNode } from "react";
import { HelpCircle } from "lucide-react";

import { cn } from "@/lib/utils";

// Deliberately no Radix dependency — this redesign is UX-only, and a plain
// hover/focus-triggered tooltip covers every use case here (one-line plain-
// language explanations of jargon terms) without adding a new primitive
// dependency for a single interaction pattern.
export function InfoTooltip({ text, className }: { text: string; className?: string }) {
  const [open, setOpen] = useState(false);

  return (
    <span
      className={cn("relative inline-flex", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="inline-flex text-muted-foreground hover:text-foreground"
        onClick={(e) => {
          e.preventDefault();
          setOpen((v) => !v);
        }}
        onBlur={() => setOpen(false)}
        aria-label={text}
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-20 mb-1.5 w-max max-w-[220px] -translate-x-1/2 rounded-md bg-foreground px-2.5 py-1.5 text-xs text-background shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
}

export function TooltipLabel({ label, tooltip, children }: { label: ReactNode; tooltip?: string | null; children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1">
      {label}
      {tooltip && <InfoTooltip text={tooltip} />}
      {children}
    </span>
  );
}
