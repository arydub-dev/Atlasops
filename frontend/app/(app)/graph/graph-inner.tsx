"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { GitBranch, Radar, Search } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import type { TimelineEvent } from "@/lib/types";
import { relativeTime } from "@/lib/format";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type GraphStats = {
  node_counts?: Record<string, number>;
  total_nodes?: number;
  total_edges?: number;
  edge_count?: number;
};

type TraverseResult = {
  nodes: { id: string; type: string; label?: string; status?: string }[];
  edges: { source: string; target: string; relation: string }[];
  stats?: { node_count: number; edge_count: number };
};

type ImpactResult = {
  impact?: {
    summary?: string;
    by_type?: Record<string, number>;
    delayed_shipments?: number;
    open_alerts?: number;
    elevated_risk_nodes?: number;
  };
};

const ENTITY_TYPES = [
  "supplier",
  "warehouse",
  "shipment",
  "purchase_order",
  "sales_order",
  "alert",
  "risk",
  "incident",
];

export default function GraphExplorerInner() {
  const sp = useSearchParams();
  const initialType = sp.get("type") || "supplier";
  const initialId = sp.get("id") || "";

  return (
    <GraphExplorerStateful
      key={`${initialType}:${initialId}`}
      initialEntityType={initialType}
      initialEntityId={initialId}
    />
  );
}

function GraphExplorerStateful({
  initialEntityType,
  initialEntityId,
}: {
  initialEntityType: string;
  initialEntityId: string;
}) {
  const { data: stats, loading, error } = useFetch<GraphStats>("/graph/stats");
  const { data: timeline } = useFetch<{ items: TimelineEvent[] }>("/timeline?limit=30");

  const [entityType, setEntityType] = useState(initialEntityType);
  const [entityId, setEntityId] = useState(initialEntityId);
  const [depth, setDepth] = useState("2");
  const [traverse, setTraverse] = useState<TraverseResult | null>(null);
  const [impact, setImpact] = useState<ImpactResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const counts = useMemo(() => Object.entries(stats?.node_counts || {}), [stats]);

  async function runExplore() {
    if (!entityId.trim()) {
      setMsg("Enter an entity UUID to traverse");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      const [t, i] = await Promise.all([
        api.get<TraverseResult>(
          `/graph/traverse/${entityType}/${entityId.trim()}?depth=${depth}`
        ),
        api.get<ImpactResult>(`/graph/impact/${entityType}/${entityId.trim()}`),
      ]);
      setTraverse(t);
      setImpact(i);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Traversal failed");
      setTraverse(null);
      setImpact(null);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Graph"
        description="Traverse operational relationships, impact, and timeline context."
      >
        <Badge variant="secondary" className="gap-1">
          <GitBranch className="h-3 w-3" />
          {stats?.total_nodes ?? 0} nodes
        </Badge>
      </PageHeader>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        {counts.map(([type, n]) => (
          <Card key={type}>
            <CardContent className="pt-4">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {type.replace(/_/g, " ")}
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">{n}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Search className="h-4 w-4" /> Explore entity
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 lg:flex-row">
          <Select value={entityType} onValueChange={setEntityType}>
            <SelectTrigger className="w-full lg:w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ENTITY_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            placeholder="Entity UUID"
            className="flex-1 font-mono text-xs"
          />
          <Select value={depth} onValueChange={setDepth}>
            <SelectTrigger className="w-full lg:w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4].map((d) => (
                <SelectItem key={d} value={String(d)}>
                  depth {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={runExplore} disabled={busy}>
            <Radar className="h-3.5 w-3.5" /> {busy ? "Traversing…" : "Traverse"}
          </Button>
        </CardContent>
        {msg && <p className="px-6 pb-4 text-sm text-destructive">{msg}</p>}
      </Card>

      {(traverse || impact) && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
          <Card className="lg:col-span-7">
            <CardHeader>
              <CardTitle className="text-sm">
                Neighborhood ({traverse?.stats?.node_count ?? traverse?.nodes?.length ?? 0} nodes)
              </CardTitle>
            </CardHeader>
            <CardContent className="max-h-96 space-y-2 overflow-auto">
              {(traverse?.nodes || []).map((n) => (
                <div
                  key={`${n.type}-${n.id}`}
                  className="flex items-center justify-between rounded-md border border-border/60 px-3 py-2 text-xs"
                >
                  <div>
                    <p className="font-medium">{n.label || n.id}</p>
                    <p className="text-muted-foreground capitalize">{n.type}</p>
                  </div>
                  {n.status && <Badge variant="secondary">{n.status}</Badge>}
                </div>
              ))}
              {(traverse?.edges || []).slice(0, 20).map((e, i) => (
                <p key={i} className="font-mono text-[11px] text-muted-foreground">
                  {e.source.slice(0, 8)} —{e.relation}→ {e.target.slice(0, 8)}
                </p>
              ))}
            </CardContent>
          </Card>
          <Card className="lg:col-span-5">
            <CardHeader>
              <CardTitle className="text-sm">Impact Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>{impact?.impact?.summary || "No impact summary"}</p>
              <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                <span>Delayed: {impact?.impact?.delayed_shipments ?? 0}</span>
                <span>Alerts: {impact?.impact?.open_alerts ?? 0}</span>
                <span>Elevated risk: {impact?.impact?.elevated_risk_nodes ?? 0}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Global Operational Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="relative border-l border-border/70 pl-4">
            {(timeline?.items || []).map((e) => (
              <li key={e.id} className="pb-3 last:pb-0">
                <div className="flex justify-between gap-2">
                  <p className="text-sm font-medium">{e.title}</p>
                  {e.occurred_at && (
                    <span className="text-[11px] text-muted-foreground">{relativeTime(e.occurred_at)}</span>
                  )}
                </div>
                {e.summary && <p className="text-xs text-muted-foreground">{e.summary}</p>}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
