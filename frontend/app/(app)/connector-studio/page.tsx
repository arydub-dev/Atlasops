"use client";

import Link from "next/link";
import { Puzzle, RefreshCw } from "lucide-react";
import { useFetch } from "@/lib/use-fetch";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type CatalogueItem = {
  type: string;
  display_name: string;
  auth_methods: string[];
  version: string;
  capabilities: string[];
};

type Diagnostics = {
  total: number;
  avg_health_score: number;
  items: { id: string; name: string; type: string; health_score: number; status: string }[];
};

export default function ConnectorStudioPage() {
  const { data: catalogue, loading, error } = useFetch<{ items: CatalogueItem[] }>(
    "/connector-studio/catalogue"
  );
  const { data: diag, refetch } = useFetch<Diagnostics>("/connector-studio/diagnostics");

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Connector Studio"
        description="Install, map, schedule, and diagnose integrations without code."
      >
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh health
        </Button>
        <Link href="/data-sources/connectors">
          <Button size="sm">Manage connections</Button>
        </Link>
      </PageHeader>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Catalogue" value={catalogue?.items.length ?? 0} />
        <Stat label="Installed" value={diag?.total ?? 0} />
        <Stat label="Avg health" value={diag?.avg_health_score ?? 0} />
        <Stat
          label="At risk"
          value={(diag?.items || []).filter((i) => i.health_score < 50).length}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Puzzle className="h-4 w-4" /> Connector catalogue
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {(catalogue?.items || []).map((c) => (
            <div key={c.type} className="rounded-lg border border-border/60 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium">{c.display_name}</p>
                  <p className="text-xs text-muted-foreground">{c.type}</p>
                </div>
                <Badge variant="secondary">v{c.version}</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {(c.auth_methods || []).map((a) => (
                  <Badge key={a} variant="outline" className="text-[10px]">
                    {a}
                  </Badge>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                {(c.capabilities || []).slice(0, 5).join(" · ")}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Installed connection health</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(diag?.items || []).length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No connectors installed yet. Create one from Data Sources.
            </p>
          )}
          {(diag?.items || []).map((c) => (
            <Link
              key={c.id}
              href={`/connector-studio/${c.id}`}
              className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-sm hover:bg-accent/40"
            >
              <div>
                <p className="font-medium">{c.name}</p>
                <p className="text-xs text-muted-foreground">{c.type}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={c.health_score >= 70 ? "success" : "warning"}>
                  {c.health_score}
                </Badge>
                <Badge variant="secondary">{c.status}</Badge>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
