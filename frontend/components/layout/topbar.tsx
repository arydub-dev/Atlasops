"use client";

import { useEffect, useState } from "react";
import { Database, Loader2, LogOut, Menu, Plug, Sparkles, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useDemoMode } from "@/lib/demo-mode";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { GlobalSearch } from "@/components/layout/global-search";

function DatasetBadge() {
  const [mode, setMode] = useState<"demo" | "connected" | null>(null);
  useEffect(() => {
    api.get<{ mode: "demo" | "connected" }>("/data/mode").then((d) => setMode(d.mode)).catch(() => {});
  }, []);
  if (!mode) return null;
  const demo = mode === "demo";
  return (
    <span
      title={demo ? "Seeded demo dataset is active — no setup required" : "Connected to external data sources"}
      className={cn(
        "hidden items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium md:flex",
        demo
          ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
          : "border-success/30 bg-success/10 text-success"
      )}
    >
      {demo ? <Database className="h-3.5 w-3.5" /> : <Plug className="h-3.5 w-3.5" />}
      {demo ? "Demo Dataset Active" : "Connected Mode"}
    </span>
  );
}

function DemoToggle() {
  const { enabled, seeding, toggle } = useDemoMode();
  return (
    <button
      onClick={toggle}
      title="Demo Mode populates alerts, disruptions and AI recommendations for presentations"
      className={cn(
        "hidden items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors sm:flex",
        enabled
          ? "border-primary/40 bg-primary/10 text-primary"
          : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
      )}
    >
      {seeding ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Sparkles className="h-3.5 w-3.5" />
      )}
      Demo Mode
      <span
        className={cn(
          "ml-0.5 inline-block h-1.5 w-1.5 rounded-full",
          enabled ? "bg-success animate-pulse" : "bg-muted-foreground/40"
        )}
      />
    </button>
  );
}

export function Topbar({ onMenu }: { onMenu?: () => void }) {
  const { user, logout } = useAuth();
  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")
    : "??";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur lg:px-6">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenu}>
        <Menu className="h-5 w-5" />
      </Button>
      <div className="flex-1">
        <GlobalSearch />
      </div>
      <div className="flex items-center gap-1.5">
        <DatasetBadge />
        <DemoToggle />
        <ThemeToggle />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors hover:bg-accent">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                {initials}
              </span>
              <span className="hidden text-left leading-tight sm:block">
                <span className="block text-sm font-medium">{user?.full_name}</span>
                <span className="block text-xs text-muted-foreground">
                  {user ? ROLE_LABELS[user.role] : ""}
                </span>
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>
              <div className="leading-tight">
                <p className="text-sm font-medium">{user?.full_name}</p>
                <p className="text-xs font-normal text-muted-foreground">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>
              <UserIcon className="mr-1 h-4 w-4" />
              {user ? ROLE_LABELS[user.role] : ""}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
              <LogOut className="mr-1 h-4 w-4" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
