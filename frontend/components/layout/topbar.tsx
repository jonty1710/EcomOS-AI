import Link from "next/link";
import { Boxes, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export function Topbar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4 md:px-6 print:hidden">
      <Link href="/" className="flex items-center gap-2 md:hidden">
        <Boxes className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold">EcomOS AI</span>
      </Link>
      <div className="hidden md:block" />
      <div className="flex items-center gap-2">
        <Button asChild size="sm">
          <Link href="/collection/new">
            <Plus className="h-4 w-4" />
            New Research
          </Link>
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}
