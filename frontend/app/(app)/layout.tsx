"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { LoadingState } from "@/components/shared/states";
import { useDemoMode } from "@/lib/demo-mode";
import { cn } from "@/lib/utils";

const DEMO_SANDBOX = process.env.NEXT_PUBLIC_DEMO_SANDBOX === "true";

function DemoBanner() {
  const { enabled } = useDemoMode();
  if (!DEMO_SANDBOX || !enabled) return null;
  return (
    <div className="no-print flex items-center justify-center gap-2 border-b border-primary/30 bg-primary/10 px-4 py-1.5 text-xs font-medium text-primary">
      <Sparkles className="h-3.5 w-3.5" />
      Demo Mode active — alerts, disruptions and AI recommendations are populated for demonstration.
    </div>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, currentOrganization, loading } = useAuth();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!currentOrganization) {
      router.replace("/onboarding");
    }
  }, [loading, user, currentOrganization, router]);

  if (loading || !user || !currentOrganization) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingState label="Authenticating…" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      <div
        className={cn(
          "fixed inset-0 z-50 lg:hidden",
          mobileOpen ? "pointer-events-auto" : "pointer-events-none"
        )}
      >
        <div
          className={cn(
            "absolute inset-0 bg-black/50 transition-opacity",
            mobileOpen ? "opacity-100" : "opacity-0"
          )}
          onClick={() => setMobileOpen(false)}
        />
        <div
          className={cn(
            "absolute left-0 top-0 h-full transition-transform",
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          <Sidebar onNavigate={() => setMobileOpen(false)} />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setMobileOpen(true)} />
        <DemoBanner />
        <main className="flex-1 space-y-6 p-4 lg:p-6 animate-fade-in">{children}</main>
      </div>
    </div>
  );
}
