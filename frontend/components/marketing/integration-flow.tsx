import {
  Brain,
  Database,
  FileText,
  Layers,
  Radar,
  ShieldCheck,
  Workflow,
  Zap,
} from "lucide-react";

const SOURCES = [
  "SAP",
  "Oracle",
  "Salesforce",
  "Microsoft Dynamics",
  "WMS",
  "TMS",
  "CSV",
  "Excel",
  "REST APIs",
];

const STAGES = [
  { icon: Workflow, label: "Integration Layer", sub: "Connect & ingest" },
  { icon: Layers, label: "Unified Operational Model", sub: "Normalize & validate" },
  { icon: ShieldCheck, label: "Risk Intelligence", sub: "Explainable scoring" },
  { icon: Brain, label: "Decision Engine", sub: "Recommended actions" },
  { icon: Radar, label: "Mission Control", sub: "Operational cockpit" },
  { icon: FileText, label: "Executive Reporting", sub: "Briefs & exports" },
];

function Connector() {
  return (
    <div className="flex items-center justify-center py-1" aria-hidden="true">
      <svg width="2" height="26" className="overflow-visible">
        <line
          x1="1"
          y1="0"
          x2="1"
          y2="26"
          stroke="hsl(var(--border))"
          strokeWidth="2"
        />
        <line
          x1="1"
          y1="0"
          x2="1"
          y2="26"
          stroke="hsl(221 83% 53%)"
          strokeWidth="2"
          strokeDasharray="4 6"
          className="animate-dash-flow"
        />
      </svg>
    </div>
  );
}

export function IntegrationFlow() {
  return (
    <div className="mx-auto max-w-3xl">
      {/* Sources */}
      <div className="rounded-2xl border border-border bg-background p-5">
        <p className="mb-3 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          External Systems
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {SOURCES.map((s, i) => (
            <span
              key={s}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground"
              style={{ animation: `fade-up 0.5s ease-out ${i * 50}ms both` }}
            >
              <Database className="h-3.5 w-3.5 text-primary" />
              {s}
            </span>
          ))}
        </div>
      </div>

      <Connector />

      {/* Stages */}
      <div className="space-y-0">
        {STAGES.map((st, i) => (
          <div key={st.label}>
            <div
              className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 transition-all hover:shadow-card"
              style={{ animation: `fade-up 0.5s ease-out ${i * 80}ms both` }}
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <st.icon className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-foreground">
                  {st.label}
                </p>
                <p className="text-xs text-muted-foreground">{st.sub}</p>
              </div>
              {i === 0 && (
                <span className="hidden items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-semibold text-success sm:flex">
                  <Zap className="h-3 w-3" /> Live
                </span>
              )}
            </div>
            {i < STAGES.length - 1 && <Connector />}
          </div>
        ))}
      </div>
    </div>
  );
}
