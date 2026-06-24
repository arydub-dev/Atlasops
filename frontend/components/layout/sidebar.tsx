"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bell,
  Boxes,
  Database,
  Factory,
  FileSpreadsheet,
  FileText,
  FlaskConical,
  Hexagon,
  type LucideIcon,
  Plug,
  Radar,
  Settings,
  Share2,
  ShieldAlert,
  Sparkles,
  Truck,
  Upload,
  Warehouse,
} from "lucide-react";
import { NAV_GROUPS } from "@/lib/constants";
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
  Database,
  Plug,
  Upload,
  FileSpreadsheet,
  Activity,
};

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-card/40">
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Hexagon className="h-5 w-5" />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight">SupplyChain</p>
          <p className="text-[11px] text-muted-foreground">Command Center</p>
        </div>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto p-3">
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi} className="space-y-1">
            {group.label && (
              <p className="section-label px-3 pb-1 pt-1">{group.label}</p>
            )}
            {group.items.map((item) => {
              const Icon = ICONS[item.icon] ?? Radar;
              const active =
                pathname === item.href || pathname.startsWith(item.href + "/");
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
          <p className="font-medium text-foreground">Operations Online</p>
          <p className="mt-0.5 flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-success" />
            Live data feed active
          </p>
        </div>
      </div>
    </aside>
  );
}
