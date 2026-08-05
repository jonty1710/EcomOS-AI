"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  History,
  GitCompare,
  FileText,
  Settings,
  BookOpen,
  Boxes,
  ClipboardList,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useExperienceMode } from "@/lib/experience-mode";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/collection", label: "Data Collection", icon: ClipboardList },
  { href: "/research/new", label: "Quick Manual Research", icon: Search },
  { href: "/history", label: "History", icon: History },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/methodology", label: "Methodology", icon: BookOpen },
];

const FUTURE_MODULES = [
  "Inventory",
  "Orders",
  "Advertising",
  "Keyword Tracking",
  "Profit Tracking",
  "Brand Health",
  "Pricing Alerts",
  "Sales Dashboard",
  "AI Automation",
];

// Progressive disclosure applies to navigation too — a first-time seller
// doesn't need Compare/Reports/Methodology or a list of 9 unbuilt future
// modules cluttering the first thing they see.
const BEGINNER_VISIBLE_HREFS = new Set(["/", "/collection", "/history"]);
const PROFESSIONAL_HIDDEN_HREFS = new Set(["/methodology"]);

export function Sidebar() {
  const pathname = usePathname();
  const { mode } = useExperienceMode();

  const navItems = NAV_ITEMS.filter((item) => {
    if (mode === "beginner") return BEGINNER_VISIBLE_HREFS.has(item.href);
    if (mode === "professional") return !PROFESSIONAL_HIDDEN_HREFS.has(item.href);
    return true;
  });
  const showFutureModules = mode === "enterprise";

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Boxes className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold">EcomOS AI</span>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}

        {showFutureModules && (
          <>
            <div className="my-2 border-t border-border" />
            <p className="px-3 pb-1 pt-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Future Modules
            </p>
            {FUTURE_MODULES.map((label) => (
              <div
                key={label}
                title="Coming soon"
                className="flex cursor-not-allowed items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground/50"
              >
                {label}
              </div>
            ))}
          </>
        )}
      </nav>

      <div className="border-t border-border p-2">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
            pathname === "/settings"
              ? "bg-primary/10 font-medium text-primary"
              : "text-muted-foreground hover:bg-secondary hover:text-foreground",
          )}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
