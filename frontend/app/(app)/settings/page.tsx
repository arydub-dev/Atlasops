"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sparkles, Sun, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useDemoMode } from "@/lib/demo-mode";
import { api, API_BASE } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/constants";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const { user } = useAuth();
  const { enabled, toggle, seeding, lastSeededAt } = useDemoMode();
  const { theme, setTheme } = useTheme();
  const [provider, setProvider] = useState<string>("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    api.get<{ provider: string }>("/ai/status").then((s) => setProvider(s.provider)).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Manage your account, workspace appearance and demonstration tools." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <UserIcon className="h-4 w-4" /> Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Name" value={user?.full_name ?? "—"} />
            <Row label="Email" value={user?.email ?? "—"} />
            <Row label="Role" value={user ? ROLE_LABELS[user.role] : "—"} />
            <Row label="Status" value={user?.is_active ? "Active" : "Inactive"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Monitor className="h-4 w-4" /> Appearance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">Theme</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: "dark", label: "Dark", icon: Moon },
                { id: "light", label: "Light", icon: Sun },
                { id: "system", label: "System", icon: Monitor },
              ].map((opt) => {
                const Icon = opt.icon;
                const active = mounted && theme === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setTheme(opt.id)}
                    className={cn(
                      "flex flex-col items-center gap-2 rounded-lg border p-3 text-xs font-medium transition-colors",
                      active ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-accent"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Sparkles className="h-4 w-4" /> Demonstration Mode
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="text-xs text-muted-foreground">
              Demo Mode regenerates alerts and risk assessments so the platform always presents a
              rich operational picture during walkthroughs.
            </p>
            <div className="flex items-center justify-between rounded-lg border border-border/60 p-3">
              <div>
                <p className="font-medium">Demo Mode</p>
                <p className="text-xs text-muted-foreground">
                  {enabled ? "Enabled" : "Disabled"}
                  {lastSeededAt && enabled ? ` · seeded ${new Date(lastSeededAt).toLocaleTimeString()}` : ""}
                </p>
              </div>
              <Button variant={enabled ? "default" : "outline"} size="sm" onClick={toggle} disabled={seeding}>
                {seeding ? "Seeding…" : enabled ? "Turn off" : "Turn on"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">System</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="API endpoint" value={API_BASE} mono />
            <Row
              label="AI engine"
              value={
                <Badge variant={provider === "openai" ? "success" : "secondary"}>
                  {provider === "openai" ? "OpenAI" : "Local Engine"}
                </Badge>
              }
            />
            <Row label="Environment" value="Development" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border/40 pb-2 last:border-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("text-right font-medium", mono && "font-mono text-xs")}>{value}</span>
    </div>
  );
}
