import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Boxes,
  Brain,
  Building2,
  Cable,
  CircuitBoard,
  Cloud,
  Database,
  FileText,
  FlaskConical,
  Gauge,
  GitBranch,
  Globe2,
  Layers,
  LineChart,
  Lock,
  Network,
  Radar,
  ShieldCheck,
  Sparkles,
  Truck,
  Workflow,
} from "lucide-react";
import { DashboardPreview } from "@/components/marketing/dashboard-preview";
import { IntegrationFlow } from "@/components/marketing/integration-flow";
import { Reveal } from "@/components/marketing/reveal";
import {
  Container,
  CTASection,
  Eyebrow,
  PrimaryButton,
  Section,
  SecondaryButton,
  SectionHeading,
} from "@/components/marketing/ui";

const TRUST = [
  { icon: Building2, label: "Built for enterprise operations" },
  { icon: Layers, label: "Scalable architecture" },
  { icon: Cable, label: "API-first" },
  { icon: Cloud, label: "Cloud-native" },
  { icon: ShieldCheck, label: "Secure by design" },
  { icon: Network, label: "Multi-tenant ready" },
  { icon: GitBranch, label: "Production-ready deployment" },
];

const PROBLEMS = [
  {
    icon: Database,
    title: "Disconnected ERP systems",
    body: "Operational data is scattered across SAP, Oracle, WMS and spreadsheets that never talk to each other.",
  },
  {
    icon: Globe2,
    title: "Poor visibility",
    body: "No single view of shipments, inventory and suppliers means teams react late to problems they can't see.",
  },
  {
    icon: FileText,
    title: "Manual reporting",
    body: "Analysts spend days assembling status decks by hand instead of acting on what the data is telling them.",
  },
  {
    icon: Activity,
    title: "Delayed decisions",
    body: "By the time a disruption surfaces in a report, the window to mitigate it has often already closed.",
  },
  {
    icon: Boxes,
    title: "Inventory blind spots",
    body: "Stockouts and overstock hide in the gaps between systems, tying up capital and missing demand.",
  },
  {
    icon: ShieldCheck,
    title: "Supplier & operational risk",
    body: "Risk lives in people's heads, not in a model — so exposure is discovered after it becomes an incident.",
  },
];

const FEATURES = [
  {
    icon: Radar,
    title: "Mission Control",
    body: "Executive KPIs, health scores, AI situation reports and recommended actions in a single operational cockpit.",
  },
  {
    icon: Truck,
    title: "Shipment Operations",
    body: "Tracking, timelines, filtering and exception management across every lane and carrier.",
  },
  {
    icon: Boxes,
    title: "Inventory Intelligence",
    body: "Stock visibility, forecasts, reorder recommendations and warehouse optimization.",
  },
  {
    icon: Building2,
    title: "Supplier Intelligence",
    body: "Supplier scorecards, performance analysis, risk assessment and reliability trends.",
  },
  {
    icon: ShieldCheck,
    title: "Risk Intelligence",
    body: "Explainable risk scoring across categories, with impact analysis and concrete recommendations.",
  },
  {
    icon: FlaskConical,
    title: "Simulation Center",
    body: "Model supplier shutdowns, port closures, warehouse outages and demand spikes with revenue impact.",
  },
  {
    icon: Sparkles,
    title: "Operations Copilot",
    body: "Natural-language investigation with grounded recommendations and executive explanations.",
  },
  {
    icon: FileText,
    title: "Executive Briefs",
    body: "One-click leadership summaries with PDF and Markdown export.",
  },
  {
    icon: Globe2,
    title: "Interactive Network View",
    body: "An animated map of warehouses, suppliers, routes and delay hotspots.",
  },
];

const STEPS = [
  {
    icon: Cable,
    title: "Connect operational data",
    body: "Bring in ERP, WMS, TMS, CRM, CSV, Excel and REST sources through the integration layer.",
  },
  {
    icon: Workflow,
    title: "Normalize & validate",
    body: "Data is mapped, validated and transformed into a single unified operational model.",
  },
  {
    icon: LineChart,
    title: "Generate intelligence",
    body: "Metrics, trends and health scores are computed across the entire operation.",
  },
  {
    icon: ShieldCheck,
    title: "Assess risk",
    body: "Explainable scoring surfaces exposure across suppliers, lanes and inventory.",
  },
  {
    icon: Brain,
    title: "Recommend actions",
    body: "The decision engine proposes concrete, prioritized mitigations.",
  },
  {
    icon: Gauge,
    title: "Support decisions",
    body: "Teams act from Mission Control with executive briefs and audit trails.",
  },
];

const CONNECTORS = [
  "SAP S/4HANA",
  "Oracle ERP",
  "Salesforce",
  "Microsoft Dynamics",
  "Warehouse Management",
  "Transportation Management",
  "REST APIs",
  "CSV",
  "Excel",
];

export default function LandingPage() {
  return (
    <>
      {/* ===================== HERO ===================== */}
      <section className="relative overflow-hidden">
        <div className="hero-grid pointer-events-none absolute inset-0" />
        <div className="radial-fade pointer-events-none absolute inset-0" />
        <Container className="relative pt-20 pb-16 sm:pt-28 sm:pb-24">
          <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1.2fr] lg:gap-8">
            <div>
              <Reveal>
                <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background/70 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  Operational intelligence platform
                </span>
              </Reveal>
              <Reveal delay={80}>
                <h1 className="mt-5 text-balance text-4xl font-semibold leading-[1.05] tracking-tight text-foreground sm:text-5xl lg:text-6xl">
                  Operational Intelligence for{" "}
                  <span className="text-gradient">Modern Supply Chains</span>
                </h1>
              </Reveal>
              <Reveal delay={160}>
                <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
                  Unify operational data, monitor risk, coordinate decisions, and
                  transform fragmented supply chain information into actionable
                  intelligence.
                </p>
              </Reveal>
              <Reveal delay={240}>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <PrimaryButton href="/get-started">
                    Start Free Demo
                  </PrimaryButton>
                  <SecondaryButton href="/get-started">
                    Book a Demo
                  </SecondaryButton>
                </div>
              </Reveal>
              <Reveal delay={320}>
                <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Cloud className="h-3.5 w-3.5 text-primary" /> Cloud-native
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Cable className="h-3.5 w-3.5 text-primary" /> API-first
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Lock className="h-3.5 w-3.5 text-primary" /> Secure by design
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Network className="h-3.5 w-3.5 text-primary" /> Multi-tenant
                    ready
                  </span>
                </div>
              </Reveal>
            </div>

            <Reveal delay={200} className="lg:pl-6">
              <DashboardPreview />
            </Reveal>
          </div>
        </Container>
      </section>

      {/* ===================== TRUST ===================== */}
      <section className="border-y border-border bg-muted/30 py-10">
        <Container>
          <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Engineered for enterprise operations
          </p>
          <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-7">
            {TRUST.map((t) => (
              <div
                key={t.label}
                className="flex flex-col items-center gap-2 text-center"
              >
                <t.icon className="h-5 w-5 text-primary" />
                <span className="text-[11px] font-medium leading-tight text-muted-foreground">
                  {t.label}
                </span>
              </div>
            ))}
          </div>
        </Container>
      </section>

      {/* ===================== PROBLEM ===================== */}
      <Section>
        <Container>
          <SectionHeading
            eyebrow="The problem"
            title="Supply chain data is everywhere — and nowhere"
            description="Most operations run on a patchwork of systems that were never designed to work together. The result is slow, reactive, and expensive."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {PROBLEMS.map((p, i) => (
              <Reveal
                key={p.title}
                delay={i * 60}
                className="group rounded-2xl border border-border bg-card p-6 transition-all hover:-translate-y-1 hover:shadow-card"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
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

      {/* ===================== SOLUTION ===================== */}
      <Section className="border-y border-border bg-muted/30">
        <Container>
          <SectionHeading
            eyebrow="The solution"
            title="One unified operational picture"
            description="ATLASOPS ingests data from the systems you already run, normalizes it into a single model, and turns it into risk intelligence, decisions, and action."
          />
          <Reveal className="mt-14">
            <IntegrationFlow />
          </Reveal>
        </Container>
      </Section>

      {/* ===================== FEATURES ===================== */}
      <Section>
        <Container>
          <SectionHeading
            eyebrow="Platform"
            title="Everything operations needs, in one place"
            description="From the executive cockpit to deep operational tooling — ATLASOPS spans the full decision loop."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <Reveal
                key={f.title}
                delay={(i % 3) * 60}
                className="group rounded-2xl border border-border bg-card p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-card"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <f.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-foreground">
                  {f.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.body}
                </p>
              </Reveal>
            ))}
          </div>
          <Reveal className="mt-10 flex justify-center">
            <SecondaryButton href="/platform">
              Explore the platform
            </SecondaryButton>
          </Reveal>
        </Container>
      </Section>

      {/* ===================== INTEGRATIONS ===================== */}
      <Section className="border-y border-border bg-muted/30">
        <Container>
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <Eyebrow>Integrations</Eyebrow>
              <h2 className="mt-4 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                An extensible enterprise integration framework
              </h2>
              <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                CSV and Excel ingestion are fully supported today. Connector
                templates provide a foundation for integrating enterprise
                platforms, and the architecture is designed to support enterprise
                integration patterns — connection health, sync status, validation,
                transformation and pipeline monitoring.
              </p>
              <ul className="mt-6 space-y-3">
                {[
                  "Connection health & last-sync visibility",
                  "Validation, transformation & data lineage",
                  "Pipeline monitoring across every source",
                  "Records imported & synchronization status",
                ].map((t) => (
                  <li
                    key={t}
                    className="flex items-center gap-3 text-sm text-foreground"
                  >
                    <CircuitBoard className="h-4 w-4 shrink-0 text-primary" />
                    {t}
                  </li>
                ))}
              </ul>
              <div className="mt-8">
                <PrimaryButton href="/integrations">
                  View integrations
                </PrimaryButton>
              </div>
            </div>

            <Reveal className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {CONNECTORS.map((c, i) => (
                <div
                  key={c}
                  className="flex h-24 flex-col items-center justify-center gap-2 rounded-xl border border-border bg-background p-3 text-center transition-all hover:-translate-y-1 hover:shadow-card"
                  style={{ animation: `fade-up 0.5s ease-out ${i * 50}ms both` }}
                >
                  <Database className="h-5 w-5 text-primary" />
                  <span className="text-xs font-medium text-foreground">
                    {c}
                  </span>
                </div>
              ))}
            </Reveal>
          </div>
        </Container>
      </Section>

      {/* ===================== HOW IT WORKS ===================== */}
      <Section id="how-it-works">
        <Container>
          <SectionHeading
            eyebrow="How it works"
            title="From raw data to confident decisions"
            description="Six steps turn fragmented operational data into action your teams can trust."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal
                key={s.title}
                delay={(i % 3) * 70}
                className="relative rounded-2xl border border-border bg-card p-6"
              >
                <span className="absolute right-5 top-5 font-mono text-xs font-semibold text-muted-foreground/50">
                  0{i + 1}
                </span>
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <s.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-foreground">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {s.body}
                </p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* ===================== SECURITY ===================== */}
      <Section className="border-y border-border bg-muted/30">
        <Container>
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <Reveal className="order-2 lg:order-1">
              <div className="rounded-2xl border border-border bg-background p-6 shadow-card">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { icon: Lock, t: "JWT authentication" },
                    { icon: ShieldCheck, t: "Role-based access control" },
                    { icon: Network, t: "Tenant isolation architecture" },
                    { icon: FileText, t: "Audit logging" },
                    { icon: Database, t: "Secure password hashing" },
                    { icon: Cloud, t: "Containerized deployment" },
                  ].map((s) => (
                    <div
                      key={s.t}
                      className="flex items-center gap-2.5 rounded-xl border border-border bg-card p-3"
                    >
                      <s.icon className="h-4 w-4 shrink-0 text-primary" />
                      <span className="text-xs font-medium text-foreground">
                        {s.t}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Reveal>
            <div className="order-1 lg:order-2">
              <Eyebrow>Security</Eyebrow>
              <h2 className="mt-4 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                Security-first architecture
              </h2>
              <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                ATLASOPS is built on concrete architectural decisions — role-based
                access control, JWT authentication, secure password hashing, tenant
                isolation, audit logging and encrypted communication — not marketing
                claims.
              </p>
              <div className="mt-8">
                <SecondaryButton href="/security">
                  Read the security overview
                </SecondaryButton>
              </div>
            </div>
          </div>
        </Container>
      </Section>

      {/* ===================== ARCHITECTURE ===================== */}
      <Section id="architecture">
        <Container>
          <SectionHeading
            eyebrow="Architecture"
            title="A clean, layered system"
            description="A modern frontend, an API gateway, focused FastAPI services, a risk and analytics core, an AI layer and PostgreSQL — connected to the systems you already run."
          />
          <Reveal className="mt-14">
            <ArchitectureDiagram />
          </Reveal>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}

/* --------------------------- Architecture diagram --------------------------- */

function ArchitectureDiagram() {
  const layers = [
    { icon: Globe2, label: "Frontend", sub: "Next.js · App Router" },
    { icon: Cable, label: "API Gateway", sub: "Auth · routing" },
    { icon: Workflow, label: "FastAPI Services", sub: "Domain logic" },
    { icon: ShieldCheck, label: "Risk Engine", sub: "Explainable scoring" },
    { icon: BarChart3, label: "Analytics", sub: "Metrics & trends" },
    { icon: Brain, label: "AI Layer", sub: "Operations Copilot" },
    { icon: Database, label: "PostgreSQL", sub: "Unified model" },
    { icon: Network, label: "External Systems", sub: "ERP · WMS · TMS" },
  ];
  return (
    <div className="rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {layers.map((l, i) => (
          <div
            key={l.label}
            className="relative flex items-center gap-3 rounded-xl border border-border bg-background p-4"
            style={{ animation: `fade-up 0.5s ease-out ${i * 70}ms both` }}
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <l.icon className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">{l.label}</p>
              <p className="truncate text-xs text-muted-foreground">{l.sub}</p>
            </div>
            {i < layers.length - 1 && (
              <ArrowRight className="absolute -right-2.5 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-border lg:block" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-6 flex items-center justify-center">
        <Link
          href="/platform#architecture"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
        >
          See the full architecture <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
}
