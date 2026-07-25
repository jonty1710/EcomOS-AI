"use client";

import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function SettingsPage() {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    setSessionId(window.localStorage.getItem("ecomos_session_id") ?? "—");
  }, []);

  function clearSession() {
    window.localStorage.removeItem("ecomos_session_id");
    window.localStorage.removeItem("ecomos_theme");
    window.location.reload();
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">The minimum controls an anonymous-session product needs.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Appearance</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Dark / light mode</p>
          <ThemeToggle />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Session</CardTitle>
          <CardDescription>No accounts in Phase 1 — history is scoped to this browser only.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="break-all text-xs text-muted-foreground">Session ID: {sessionId}</p>
          <Button variant="outline" size="sm" onClick={clearSession}>
            <Trash2 className="h-4 w-4" />
            Clear local session data
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">AI Providers</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Not configured — Phase 1 (Foundation) runs the deterministic research engine only. Provider
            configuration (OpenAI, Claude, Gemini, local model) is planned for the AI Integration phase.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
