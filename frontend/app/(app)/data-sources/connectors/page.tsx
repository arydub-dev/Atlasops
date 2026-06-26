"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { Plus, Settings2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/use-fetch";
import type { DataSource, IntegrationTemplate } from "@/lib/types";
import { formatNumber, relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { CardGridSkeleton, ErrorState } from "@/components/shared/states";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ConnectorIcon, HealthDot, StatusBadge } from "@/components/data/data-bits";

export default function ConnectorsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const canWrite = user && user.role !== "executive";
  const { data: sources, loading, error, refetch } = useFetch<DataSource[]>("/data/sources");
  const { data: integrations, refetch: refetchTemplates } = useFetch<IntegrationTemplate[]>("/data/integrations");
  const [adding, setAdding] = useState<string | null>(null);

  async function connect(type: string) {
    setAdding(type);
    try {
      const created = await api.post<DataSource>("/data/sources", { connector_type: type });
      refetch();
      refetchTemplates();
      router.push(`/data-sources/connectors/${created.id}`);
    } finally {
      setAdding(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Connectors" description="Enterprise connector framework — ERP, CRM, WMS, TMS and custom APIs." />
        <CardGridSkeleton count={6} />
      </div>
    );
  }
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader title="Connectors" description="Enterprise connector framework — ERP, CRM, WMS, TMS and custom APIs." />

      {/* Configured connectors */}
      {sources && sources.length > 0 && (
        <div className="space-y-3">
          <h2 className="section-label">Configured Connectors</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sources.map((s) => (
              <Card key={s.id} className="p-5 transition-shadow hover:shadow-md">
                <div className="flex items-start justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <ConnectorIcon type={s.connector_type} className="h-5 w-5" />
                  </span>
                  <StatusBadge status={s.status} />
                </div>
                <p className="mt-3 font-semibold leading-tight">{s.name}</p>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="section-label">Records</p>
                    <p className="mt-0.5 font-mono tabular-nums">{formatNumber(s.record_count)}</p>
                  </div>
                  <div>
                    <p className="section-label">Last Sync</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {s.last_sync_at ? relativeTime(s.last_sync_at) : "never"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <HealthDot health={s.health} withLabel />
                  <Link href={`/data-sources/connectors/${s.id}`}>
                    <Button variant="outline" size="sm">
                      <Settings2 className="h-3.5 w-3.5" /> Configure
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Available integrations */}
      <div className="space-y-3">
        <h2 className="section-label">Available Integrations</h2>
        <p className="text-sm text-muted-foreground">
          Connect SAP, Oracle, Salesforce, Microsoft Dynamics, your WMS/TMS and
          any REST API. CSV and Excel import are self-serve; enterprise systems
          are connected with help from our team during onboarding.
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(integrations ?? []).map((i) => (
            <Card key={i.type} className="flex flex-col p-5">
              <div className="flex items-start justify-between">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <ConnectorIcon type={i.type} className="h-5 w-5" />
                </span>
                <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {i.category}
                </span>
              </div>
              <p className="mt-3 font-semibold leading-tight">{i.name}</p>
              <p className="mt-1 flex-1 text-xs leading-relaxed text-muted-foreground">{i.description}</p>
              <div className="mt-3 flex flex-wrap gap-1">
                {i.auth_methods.map((m) => (
                  <span key={m} className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {m}
                  </span>
                ))}
              </div>
              {canWrite && (
                <Button
                  variant={i.configured ? "outline" : "default"}
                  size="sm"
                  className="mt-4 w-full"
                  onClick={() => connect(i.type)}
                  disabled={adding === i.type}
                >
                  <Plus className="h-3.5 w-3.5" />
                  {adding === i.type ? "Adding…" : i.configured ? "Add another" : "Connect"}
                </Button>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
