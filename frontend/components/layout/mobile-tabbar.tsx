"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ClipboardList, History, GitCompare, MoreHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

const TABS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/collection", label: "Collect", icon: ClipboardList },
  { href: "/history", label: "History", icon: History },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/settings", label: "More", icon: MoreHorizontal },
];

// FBP §3.3: sidebar collapses to a bottom tab bar below 768px.
export function MobileTabbar() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 flex h-14 border-t border-border bg-card md:hidden">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        const Icon = tab.icon;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px]",
              active ? "text-primary" : "text-muted-foreground",
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
