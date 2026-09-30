"use client";

import { Suspense, useEffect, useState } from "react";
import { Download, FileText, Printer, RefreshCw, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { ExecutiveBrief } from "@/lib/types";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/shared/markdown";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

type GeneratedReport = {
  kind: string;
  title: string;
  generated_at: string;
  health: { score: number; grade?: string; label: string };
  narrative: string;
  confidence?: number;
  model?: string;
};

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading reports…</div>}>
      <ReportsInner />
    </Suspense>
  );
}

function ReportsInner() {
  const [brief, setBrief] = useState<ExecutiveBrief | null>(null);
  const [report, setReport] = useState<GeneratedReport | null>(null);
  const [kinds, setKinds] = useState<Record<string, string>>({});
  const [kind, setKind] = useState("executive");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<{ kinds: Record<string, string> }>("/reports/kinds")
      .then((d) => setKinds(d.kinds || {}))
      .catch(() => {});
  }, []);

  async function generateClassic() {
    setLoading(true);
    setError("");
    setReport(null);
    try {
      const b = await api.get<ExecutiveBrief>("/ai/brief");
      setBrief(b);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate brief");
    } finally {
      setLoading(false);
    }
  }

  async function generateKind() {
    setLoading(true);
    setError("");
    setBrief(null);
    try {
      const r = await api.post<GeneratedReport>(`/reports/generate?kind=${encodeURIComponent(kind)}`);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report");
    } finally {
      setLoading(false);
    }
  }

  function toMarkdown(b: ExecutiveBrief): string {
    const date = new Date(b.generated_at).toLocaleString();
    const list = (items: string[]) => items.map((i) => `- ${i}`).join("\n");
    return [
      `# Supply Chain Operations Brief`,
      `_Generated ${date} · Health Score ${b.health.score}/100 (${b.health.label})_`,
      ``,
      `## Executive Summary`,
      b.executive_summary.replace(/\*\*/g, "**"),
      ``,
      `## Current Risks`,
      list(b.current_risks),
      ``,
      `## Operational Performance`,
      list(b.operational_performance),
      ``,
      `## Key Recommendations`,
      list(b.key_recommendations),
      ``,
      `## Strategic Concerns`,
      list(b.strategic_concerns),
      ``,
    ].join("\n");
  }

  function downloadMarkdown() {
    if (report) {
      const blob = new Blob([`# ${report.title}\n\n${report.narrative}`], {
        type: "text/markdown",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report.kind}-${new Date().toISOString().slice(0, 10)}.md`;
      a.click();
      URL.revokeObjectURL(url);
      return;
    }
    if (!brief) return;
    const blob = new Blob([toMarkdown(brief)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `operations-brief-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const hasDoc = Boolean(brief || report);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Briefs"
        description="Graph-grounded leadership reports — morning brief, risk, supplier, weekly, and monthly KPIs."
      >
        {hasDoc && (
          <div className="no-print flex gap-2">
            <Button variant="outline" size="sm" onClick={downloadMarkdown}>
              <Download className="h-3.5 w-3.5" /> Markdown
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer className="h-3.5 w-3.5" /> PDF
            </Button>
          </div>
        )}
      </PageHeader>

      <Card>
        <CardContent className="flex flex-col gap-3 pt-5 lg:flex-row lg:items-end">
          <div className="flex-1 space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Report kind</p>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(kinds).map(([k, label]) => (
                  <SelectItem key={k} value={k}>
                    {label}
                  </SelectItem>
                ))}
                {Object.keys(kinds).length === 0 && (
                  <SelectItem value="executive">Executive Summary</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={generateKind} disabled={loading}>
            <Sparkles className={cn("h-4 w-4", loading && "animate-pulse")} />
            {loading ? "Generating…" : "Generate report"}
          </Button>
          <Button variant="outline" onClick={generateClassic} disabled={loading}>
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Classic brief
          </Button>
        </CardContent>
        {error && <p className="px-6 pb-4 text-xs text-destructive">{error}</p>}
      </Card>

      {!hasDoc ? (
        <Card className="flex min-h-[280px] flex-col items-center justify-center p-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <FileText className="h-7 w-7" />
          </div>
          <p className="mt-4 text-base font-medium">Generate an executive report</p>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            Combines knowledge graph, risk engine, timeline, and AI orchestration into a
            leadership-ready narrative.
          </p>
        </Card>
      ) : report ? (
        <Card className="print-area mx-auto max-w-3xl">
          <CardContent className="space-y-6 p-8 lg:p-10">
            <header className="border-b border-border pb-5">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{report.title}</Badge>
                {report.confidence != null && (
                  <Badge variant="outline">{(report.confidence * 100).toFixed(0)}% confidence</Badge>
                )}
              </div>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight">{report.title}</h1>
              <p className="mt-2 text-xs text-muted-foreground">
                Generated {new Date(report.generated_at).toLocaleString()} · Health{" "}
                {report.health.score}/100 ({report.health.label})
                {report.model ? ` · ${report.model}` : ""}
              </p>
            </header>
            <Markdown content={report.narrative} />
          </CardContent>
        </Card>
      ) : brief ? (
        <BriefDocument brief={brief} />
      ) : null}
    </div>
  );
}

function BriefDocument({ brief }: { brief: ExecutiveBrief }) {
  const date = new Date(brief.generated_at).toLocaleString("en-US", {
    dateStyle: "long",
    timeStyle: "short",
  });
  return (
    <Card className="print-area mx-auto max-w-3xl">
      <CardContent className="space-y-8 p-8 lg:p-10">
        <header className="border-b border-border pb-5">
          <p className="section-label">Confidential · Operations Leadership</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Supply Chain Operations Brief</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>Generated {date}</span>
            <span>
              Health Score:{" "}
              <span className="font-semibold text-foreground">
                {brief.health.score}/100 ({brief.health.label})
              </span>
            </span>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">{brief.situation_headline}</p>
        </header>

        <Section title="Executive Summary">
          <Markdown content={brief.executive_summary} />
        </Section>

        <Section title="Current Risks">
          <BulletList items={brief.current_risks} />
        </Section>

        <Section title="Operational Performance">
          <BulletList items={brief.operational_performance} />
        </Section>

        <Section title="Key Recommendations">
          <BulletList items={brief.key_recommendations} ordered />
        </Section>

        <Section title="Strategic Concerns">
          <BulletList items={brief.strategic_concerns} />
        </Section>

        <footer className="border-t border-border pt-4 text-[11px] text-muted-foreground">
          ATLASOPS · Auto-generated operational intelligence. Figures derived from
          live network telemetry at time of generation.
        </footer>
      </CardContent>
    </Card>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-primary">{title}</h2>
      <div className="text-sm leading-relaxed">{children}</div>
    </section>
  );
}

function BulletList({ items, ordered }: { items: string[]; ordered?: boolean }) {
  if (ordered) {
    return (
      <ol className="space-y-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex gap-3">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
              {i + 1}
            </span>
            <span>{it}</span>
          </li>
        ))}
      </ol>
    );
  }
  return (
    <ul className="space-y-1.5">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}
