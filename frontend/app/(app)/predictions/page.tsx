"use client";

import { RefreshCw, TrendingUp } from "lucide-react";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/use-fetch";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useState } from "react";

type Prediction = {
  id: string;
  kind: string;
  title: string;
  confidence: number;
  reasoning: string;
  contributing_factors: string[];
  recommended_actions: string[];
  linked_entities: { type: string; id: string; label?: string }[];
  score: number;
};

export default function PredictionsPage() {
  const { data, loading, error, refetch } = useFetch<{ items: Prediction[] }>("/predictions");
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    try {
      await api.post("/predictions/generate");
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
        title="Predictive Intelligence"
        description="Shipment delays, supplier deterioration, shortages, congestion, and anomalies."
      >
        <Button onClick={generate} disabled={busy}>
          <RefreshCw className={`h-3.5 w-3.5 ${busy ? "animate-spin" : ""}`} />
          Generate
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(data?.items || []).length === 0 && (
          <Card className="lg:col-span-2">
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              No active predictions. Generate from historical operational data.
            </CardContent>
          </Card>
        )}
        {(data?.items || []).map((p) => (
          <Card key={p.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  {p.title}
                </CardTitle>
                <Badge variant="secondary">{Math.round(p.confidence * 100)}%</Badge>
              </div>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                {p.kind.replace(/_/g, " ")}
              </p>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">{p.reasoning}</p>
              <div>
                <p className="text-[11px] font-semibold uppercase text-muted-foreground">Factors</p>
                <ul className="mt-1 list-disc pl-4 text-xs">
                  {(p.contributing_factors || []).map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase text-muted-foreground">Actions</p>
                <ul className="mt-1 list-disc pl-4 text-xs">
                  {(p.recommended_actions || []).map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
