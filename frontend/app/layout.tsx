import type { Metadata } from "next";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { MobileTabbar } from "@/components/layout/mobile-tabbar";
import { ExperienceModeProvider } from "@/lib/experience-mode";

import "./globals.css";

export const metadata: Metadata = {
  title: "EcomOS AI",
  description: "The AI Operating System for Ecommerce Product Decisions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body className="antialiased">
        <ExperienceModeProvider>
          <div className="flex h-dvh overflow-hidden">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">
              <Topbar />
              <main className="flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6">{children}</main>
            </div>
          </div>
          <MobileTabbar />
        </ExperienceModeProvider>
      </body>
    </html>
  );
}
