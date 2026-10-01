"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bell,
  Boxes,
  Building2,
  Database,
  Factory,
  FileSpreadsheet,
  FileText,
  FlaskConical,
  Gauge,
  GitBranch,
  Handshake,
  LayoutDashboard,
  type LucideIcon,
  Plug,
  Puzzle,
  Radar,
  Server,
  Settings,
  Share2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  TrendingUp,
  Truck,
  Upload,
  Warehouse,
  Workflow,
} from "lucide-react";
import { NAV_GROUPS, navVisibleForRole } from "@/lib/constants";
import { useAuth } from "@/lib/auth";
import { Logo } from "@/components/brand/logo";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  Radar,
  Truck,
  Boxes,
  Warehouse,
  Factory,
  ShieldAlert,
  Bell,
  BarChart3,
  Share2,
  FlaskConical,
  Sparkles,
  FileText,
  Settings,
  Shield,
  Database,
  Plug,
  Upload,
  FileSpreadsheet,
  Activity,
  Siren,
  GitBranch,
  Gauge,
  Puzzle,
  Workflow,
  TrendingUp,
  LayoutDashboard,
  Server,
  Handshake,
  Building2,
  ShieldCheck,
};

type FeedState = "checking" | "online" | "degraded" | "offline";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { currentMembership, user } = useAuth();
  const role = currentMembership?.role_slug;
  const [feed, setFeed] = useState<FeedState>("checking");

  useEffect(() => {
    let cancelled = false;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    async function ping() {
      try {
        const res = await fetch(`${apiBase.replace(/\/$/, "")}/health/ready`, {
          credentials: "omit",
          cache: "no-store",
        });
        if (cancelled) return;
        setFeed(res.ok ? "online" : "degraded");
      } catch {
        if (!cancelled) setFeed("offline");
      }
    }

    ping();
    const id = window.setInterval(ping, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const groups = NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) =>
      navVisibleForRole(item.access, role, { isPlatformAdmin: !!user?.is_platform_admin })
    ),
  })).filter((group) => group.items.length > 0);

  const feedLabel =
    feed === "online"
      ? "API ready"
      : feed === "degraded"
        ? "API degraded"
        : feed === "offline"
          ? "API unreachable"
          : "Checking API…";

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-card/40">
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <Logo />
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto p-3">
        {groups.map((group, gi) => (
          <div key={gi} className="space-y-1">
            {group.label && (
              <p className="section-label px-3 pb-1 pt-1">{group.label}</p>
            )}
            {group.items.map((item) => {
              const Icon = ICONS[item.icon] ?? Radar;
              const active =
                pathname === item.href ||
                (item.href !== "/settings" && pathname.startsWith(item.href + "/"));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )}
                >
                  {active && (
                    <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                  )}
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">Platform status</p>
          <p className="mt-0.5 flex items-center gap-1.5">
            <span
              className={cn(
                "inline-block h-2 w-2 rounded-full",
                feed === "online" && "bg-success animate-pulse",
                feed === "degraded" && "bg-warning",
                feed === "offline" && "bg-destructive",
                feed === "checking" && "bg-muted-foreground"
              )}
            />
            {feedLabel}
          </p>
        </div>
      </div>
    </aside>
  );
}
