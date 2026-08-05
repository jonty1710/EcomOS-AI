"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import type { ExperienceMode } from "./field-modes";

const STORAGE_KEY = "ecomos_experience_mode";

interface ExperienceModeContextValue {
  mode: ExperienceMode;
  setMode: (mode: ExperienceMode) => void;
}

const ExperienceModeContext = createContext<ExperienceModeContextValue | null>(null);

function isExperienceMode(value: string | null): value is ExperienceMode {
  return value === "beginner" || value === "professional" || value === "enterprise";
}

// Defaults to "beginner" — the whole point of progressive disclosure is that
// a first-time seller should never land on the most complex view by accident.
export function ExperienceModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ExperienceMode>("beginner");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isExperienceMode(stored)) setModeState(stored);
  }, []);

  function setMode(next: ExperienceMode) {
    setModeState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  return <ExperienceModeContext.Provider value={{ mode, setMode }}>{children}</ExperienceModeContext.Provider>;
}

export function useExperienceMode(): ExperienceModeContextValue {
  const ctx = useContext(ExperienceModeContext);
  if (!ctx) throw new Error("useExperienceMode must be used within ExperienceModeProvider");
  return ctx;
}
