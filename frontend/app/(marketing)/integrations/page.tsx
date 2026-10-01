import type { Metadata } from "next";
import Link from "next/link";
import {
  CheckCircle2,
  Database,
  FileSpreadsheet,
  FileText,
  GitBranch,
  Globe2,
  Layers,
  Plug,
  RefreshCw,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { Reveal } from "@/components/marketing/reveal";
import {
  Container,
  CTASection,
  Eyebrow,
  PageHero,
  PrimaryButton,
  Section,
  SectionHeading,
} from "@/components/marketing/ui";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Integrations",
  description:
    "Connect ATLASOPS with Dynamics 365 Business Central, Salesforce, and UPS (Beta), plus self-serve CSV and Excel import. Additional ERPs coming soon.",
};

const CONNECTORS: {
  name: string;
  kind: string;
  status: "Self-serve" | "Available" | "Beta" | "Coming Soon";
  note: string;
}[] = [
  { name: "CSV Import", kind: "File", status: "Self-serve", note: "Drag-and-drop, mapping, validation" },
  { name: "Excel Import", kind: "File", status: "Self-serve", note: "Worksheet selection & mapping" },
  { name: "Microsoft Dynamics 365 BC", kind: "ERP", status: "Beta", note: "OAuth + companies, items, sales orders" },
  { name: "Salesforce", kind: "CRM", status: "Beta", note: "OAuth + Account/Opportunity → suppliers" },
  { name: "UPS Tracking", kind: "TMS", status: "Beta", note: "OAuth + tracking updates on shipments" },
  { name: "REST API", kind: "API", status: "Coming Soon", note: "Generic REST connector planned" },
  { name: "SAP S/4HANA", kind: "ERP", status: "Coming Soon", note: "Not yet shipped" },
  { name: "Oracle ERP", kind: "ERP", status: "Coming Soon", note: "Not yet shipped" },
  { name: "Warehouse Mgmt (WMS)", kind: "WMS", status: "Coming Soon", note: "Not yet shipped" },
];

const PIPELINE = [
  { icon: Plug, title: "Connector Layer", body: "Files, APIs and enterprise connectors bring data in from external systems." },
  { icon: ShieldCheck, title: "Validation Layer", body: "Rows are type-checked, required fields enforced and errors reported clearly." },
  { icon: Workflow, title: "Transformation Layer", body: "Field mapping and reference resolution shape data into the unified model." },
  { icon: RefreshCw, title: "Synchronization", body: "Sync status, records imported and pipeline runs are tracked end to end." },
];

const MONITORING = [
  { icon: CheckCircle2, t: "Connection health" },
  { icon: RefreshCw, t: "Last sync time" },
  { icon: Database, t: "Records imported" },
  { icon: Layers, t: "Pipeline monitoring" },
  { icon: GitBranch, t: "Data lineage" },
  { icon: ShieldCheck, t: "Validation & transformation" },
];

export default function IntegrationsPage() {
  return (
    <>
      <PageHero
        eyebrow="Integrations"
        title="Connect ATLASOPS to the systems you already run"
        description="Import from CSV and Excel yourself. Dynamics 365 Business Central, Salesforce, and UPS Tracking are in Beta. Additional ERP and WMS connectors are Coming Soon."
      >
        <PrimaryButton href="/get-started">Talk to us to connect</PrimaryButton>
      </PageHero>

      {/* Capability note */}
      <Section className="pb-0">
        <Container>
          <Reveal className="mx-auto flex max-w-3xl items-start gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-5">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            <p className="text-sm leading-relaxed text-foreground">
              Status badges reflect what ships today: Self-serve file import,
              Beta connectors for Dynamics BC, Salesforce, and UPS, and Coming Soon
              for SAP, Oracle, generic REST, and WMS. Beta connectors use real OAuth
              and live APIs when credentials are configured.{" "}
              <Link href="/get-started" className="font-medium text-primary hover:underline">
                Get in touch to connect your systems.
              </Link>
            </p>
          </Reveal>
        </Container>
      </Section>

      {/* Connector grid */}
      <Section>
        <Container>
          <SectionHeading
            eyebrow="Connectors"
            title="Bring data in from anywhere"
          />
          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CONNECTORS.map((c, i) => (
              <Reveal
                key={c.name}
                delay={(i % 3) * 60}
                className="rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-1 hover:shadow-card"
              >
                <div className="flex items-start justify-between">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    {c.kind === "File" ? (
                      c.name.includes("Excel") ? (
                        <FileSpreadsheet className="h-5 w-5" />
                      ) : (
                        <FileText className="h-5 w-5" />
                      )
                    ) : c.kind === "API" ? (
                      <Globe2 className="h-5 w-5" />
                    ) : (
                      <Database className="h-5 w-5" />
                    )}
                  </span>
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[10px] font-semibold",
                      c.status === "Self-serve" || c.status === "Available"
                        ? "bg-success/10 text-success"
                        : c.status === "Beta"
                          ? "bg-primary/10 text-primary"
                          : "bg-muted text-muted-foreground",
                    )}
                  >
                    {c.status}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-semibold text-foreground">
                  {c.name}
                </h3>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {c.kind}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">{c.note}</p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* Pipeline */}
      <Section className="border-y border-border bg-muted/30">
        <Container>
          <SectionHeading
            eyebrow="Ingestion pipeline"
            title="Every source flows through the same path"
            description="External systems → connector layer → validation → transformation → unified model → risk & analytics → Operations Copilot."
          />
          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((p, i) => (
              <Reveal
                key={p.title}
                delay={i * 70}
                className="relative rounded-2xl border border-border bg-background p-6"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <p.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-foreground">
                  {p.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {p.body}
                </p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* Monitoring */}
      <Section>
        <Container>
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <Eyebrow>Operational visibility</Eyebrow>
              <h2 className="mt-4 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                Monitor every pipeline in one place
              </h2>
              <p className="mt-4 leading-relaxed text-muted-foreground">
                The Data Pipeline Monitor shows source system, sync status, last
                run, duration, records processed and failed records — so data
                problems are operational events, not silent surprises.
              </p>
            </div>
            <Reveal className="grid grid-cols-2 gap-3">
              {MONITORING.map((m, i) => (
                <div
                  key={m.t}
                  className="flex items-center gap-2.5 rounded-xl border border-border bg-card p-4"
                  style={{ animation: `fade-up 0.5s ease-out ${i * 60}ms both` }}
                >
                  <m.icon className="h-4 w-4 shrink-0 text-primary" />
                  <span className="text-xs font-medium text-foreground">
                    {m.t}
                  </span>
                </div>
              ))}
            </Reveal>
          </div>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
