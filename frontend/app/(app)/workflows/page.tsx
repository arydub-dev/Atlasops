"use client";

import { useState } from "react";
import { Play, Plus, Workflow } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
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

type Rule = {
  id: string;
  name: string;
  trigger: string;
  is_active: boolean;
  run_count: number;
  actions: unknown[];
  conditions: unknown[];
};

const TRIGGERS = [
  "manual",
  "connector_sync",
  "risk_change",
  "inventory",
  "shipment",
  "purchase_order",
  "incident",
  "schedule",
];

export default function WorkflowsPage() {
  const { data, loading, error, refetch } = useFetch<Rule[]>("/workflows");
  const { data: runs, refetch: refetchRuns } = useFetch<{ items: { id: string; status: string; rule_id: string }[] }>(
    "/workflows/runs/recent"
  );
  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("manual");
  const [busy, setBusy] = useState(false);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.post("/workflows", {
        name,
        trigger,
        conditions: [],
        actions: [{ type: "escalate", level: "leadership" }],
      });
      setName("");
      await refetch();
    } finally {
      setBusy(false);
    }
  }

  async function execute(id: string) {
    setBusy(true);
    try {
      await api.post(`/workflows/${id}/execute`, { payload: { source: "ui" } });
      await refetchRuns();
      await refetch();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Workflow Automations"
        description="Trigger → conditions → actions. Executed by ARQ workers."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Plus className="h-4 w-4" /> New automation
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 lg:flex-row">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Rule name — e.g. High supplier risk → incident"
            className="flex-1"
          />
          <Select value={trigger} onValueChange={setTrigger}>
            <SelectTrigger className="w-full lg:w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TRIGGERS.map((t) => (
                <SelectItem key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={create} disabled={busy || !name.trim()}>
            Create
          </Button>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Workflow className="h-4 w-4" /> Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(data || []).length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">No automations yet</p>
            )}
            {(data || []).map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border/60 p-3"
              >
                <div>
                  <p className="text-sm font-medium">{r.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {r.trigger} · {r.run_count} runs · {(r.actions || []).length} actions
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={r.is_active ? "success" : "secondary"}>
                    {r.is_active ? "active" : "paused"}
                  </Badge>
                  <Button size="sm" variant="outline" disabled={busy} onClick={() => execute(r.id)}>
                    <Play className="h-3.5 w-3.5" /> Run
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="text-sm">Recent runs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(runs?.items || []).map((run) => (
              <div key={run.id} className="flex justify-between text-xs">
                <span className="truncate font-mono">{run.id.slice(0, 8)}</span>
                <Badge variant="secondary">{run.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
