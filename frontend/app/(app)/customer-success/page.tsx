"use client";

import { Handshake, RefreshCw } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CustomerSuccessPage() {
  const { data: onboarding, loading, error, refetch } = useFetch<{
    progress_pct: number;
    completed: number;
    total: number;
    steps: { id: string; label: string; done: boolean }[];
  }>("/customer-success/onboarding");
  const { data: health } = useFetch<{
    recommendations: string[];
    adoption: { score: number; unused_modules: string[] };
    data_health: { overall_score: number; grade: string };
  }>("/customer-success/health-report");

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customer Success"
        description="Onboarding checklist, adoption score, and health recommendations."
      >
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs uppercase text-muted-foreground">Onboarding</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">{onboarding?.progress_pct ?? 0}%</p>
            <p className="text-xs text-muted-foreground">
              {onboarding?.completed}/{onboarding?.total} steps
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs uppercase text-muted-foreground">Adoption</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">{health?.adoption?.score ?? 0}</p>
            <p className="text-xs text-muted-foreground">
              Unused: {(health?.adoption?.unused_modules || []).join(", ") || "none"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs uppercase text-muted-foreground">Data health</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">
              {health?.data_health?.overall_score ?? "—"}
            </p>
            <Badge variant="secondary">{health?.data_health?.grade || "—"}</Badge>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-7">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Handshake className="h-4 w-4" /> Onboarding checklist
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(onboarding?.steps || []).map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-sm"
              >
                <span>{s.label}</span>
                <Badge variant={s.done ? "success" : "outline"}>{s.done ? "done" : "todo"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="lg:col-span-5">
          <CardHeader>
            <CardTitle className="text-sm">Recommendations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {(health?.recommendations || []).map((r, i) => (
                <li key={i} className="rounded-md bg-muted/40 px-3 py-2 text-xs">
                  {r}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
