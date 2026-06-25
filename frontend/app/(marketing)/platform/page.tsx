import type { Metadata } from "next";
import type { ReactNode } from "react";
import {
  BarChart3,
  Brain,
  Boxes,
  Building2,
  Cable,
  Cloud,
  Database,
  FileText,
  FlaskConical,
  Globe2,
  Network,
  Radar,
  ShieldCheck,
  Sparkles,
  Truck,
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
  title: "Platform",
  description:
    "The ATLASOPS platform: Mission Control, shipment operations, inventory and supplier intelligence, risk scoring, simulation, Operations Copilot and executive briefs.",
};

type Feature = {
  icon: typeof Radar;
  eyebrow: string;
  title: string;
  body: string;
  points: string[];
  visual: ReactNode;
};

function MiniBars() {
  const bars = [40, 62, 50, 74, 58, 82, 70, 90];
  return (
    <div className="flex h-32 items-end gap-2">
      {bars.map((h, i) => (
        <div
          key={i}
          className="flex-1 origin-bottom rounded-t bg-gradient-to-t from-primary/30 to-primary"
          style={{
            height: `${h}%`,
            animation: `bar-rise 0.9s cubic-bezier(0.16,1,0.3,1) ${i * 60}ms both`,
          }}
        />
      ))}
    </div>
  );
}

function MiniGauge({ value = 72 }: { value?: number }) {
  return (
    <div className="flex items-center justify-center">
      <div className="relative h-32 w-32">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth="12"
          />
          <circle
            cx="60"
            cy="60"
            r="50"
            fill="none"
            stroke="hsl(221 83% 53%)"
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${(value / 100) * 314} 314`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-semibold text-foreground">
            {value}
          </span>
          <span className="text-[10px] text-muted-foreground">Health</span>
        </div>
      </div>
    </div>
  );
}

function MiniRows({ items }: { items: { l: string; r: string; tone?: string }[] }) {
  return (
    <div className="space-y-2">
      {items.map((it, i) => (
        <div
          key={i}
          className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2"
          style={{ animation: `fade-up 0.5s ease-out ${i * 80}ms both` }}
        >
          <span className="text-xs font-medium text-foreground">{it.l}</span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
              it.tone ?? "bg-primary/10 text-primary",
            )}
          >
            {it.r}
          </span>
        </div>
      ))}
    </div>
  );
}

const FEATURES: Feature[] = [
  {
    icon: Radar,
    eyebrow: "Mission Control",
    title: "The operational cockpit",
    body: "A single screen that answers what is happening, why it's happening, and what to do next — with executive KPIs, health scores and AI situation reports.",
    points: [
      "Executive KPIs & operational health score",
      "AI situation report",
      "Prioritized recommended actions",
    ],
    visual: <MiniGauge value={78} />,
  },
  {
    icon: Truck,
    eyebrow: "Shipment Operations",
    title: "Every shipment, every lane",
    body: "Track shipments end to end with timelines, powerful filtering and exception management so problems surface before they escalate.",
    points: ["End-to-end tracking & timelines", "Filtering across lanes & carriers", "Exception management"],
    visual: (
      <MiniRows
        items={[
          { l: "SHP-2041 · Rotterdam", r: "In transit" },
          { l: "SHP-1888 · Singapore", r: "Delayed", tone: "bg-destructive/10 text-destructive" },
          { l: "SHP-2103 · Chicago", r: "Delivered", tone: "bg-success/10 text-success" },
        ]}
      />
    ),
  },
  {
    icon: Boxes,
    eyebrow: "Inventory Intelligence",
    title: "Visibility without blind spots",
    body: "Understand stock positions, forecasts and reorder points across every warehouse, with recommendations that protect availability and capital.",
    points: ["Stock visibility & forecasts", "Reorder recommendations", "Warehouse optimization"],
    visual: <MiniBars />,
  },
  {
    icon: Building2,
    eyebrow: "Supplier Intelligence",
    title: "Know which suppliers to trust",
    body: "Supplier scorecards combine performance, reliability trends and risk into a single view you can act on.",
    points: ["Supplier scorecards", "Performance & reliability trends", "Supplier risk assessment"],
    visual: (
      <MiniRows
        items={[
          { l: "Meridian Components", r: "A · 92", tone: "bg-success/10 text-success" },
          { l: "Orion Logistics", r: "B · 78" },
          { l: "Apex Materials", r: "C · 64", tone: "bg-warning/10 text-warning" },
        ]}
      />
    ),
  },
  {
    icon: ShieldCheck,
    eyebrow: "Risk Intelligence",
    title: "Explainable risk scoring",
    body: "Risk is scored across categories with the reasoning made transparent — plus impact analysis and concrete recommendations.",
    points: ["Explainable scoring by category", "Impact analysis", "Risk recommendations"],
    visual: <MiniGauge value={37} />,
  },
  {
    icon: FlaskConical,
    eyebrow: "Simulation Center",
    title: "Model disruptions before they happen",
    body: "Run what-if analysis for supplier shutdowns, port closures, warehouse outages and demand spikes — with revenue impact and mitigation plans.",
    points: ["Supplier shutdown & port closure", "Warehouse outage & demand spike", "Revenue impact & mitigation planning"],
    visual: (
      <MiniRows
        items={[
          { l: "Port closure · Rotterdam", r: "-$1.2M", tone: "bg-destructive/10 text-destructive" },
          { l: "Mitigation: reroute", r: "-68% impact", tone: "bg-success/10 text-success" },
          { l: "Demand spike · Q4", r: "+18% load", tone: "bg-warning/10 text-warning" },
        ]}
      />
    ),
  },
  {
    icon: Sparkles,
    eyebrow: "Operations Copilot",
    title: "Investigate in plain language",
    body: "Ask questions about your operation and get grounded answers, operational summaries and executive explanations — always tied back to your data.",
    points: ["Natural-language investigation", "Grounded recommendations", "Executive explanations"],
    visual: (
      <div className="space-y-2">
        <div className="ml-auto w-fit rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-xs text-primary-foreground">
          Why is on-time delivery down this week?
        </div>
        <div className="w-fit rounded-2xl rounded-bl-sm border border-border bg-background px-3 py-2 text-xs text-foreground">
          Three delayed lanes through Rotterdam account for 71% of the drop.
          Rerouting two shipments recovers ~1.4 pts.
        </div>
      </div>
    ),
  },
  {
    icon: FileText,
    eyebrow: "Executive Briefs",
    title: "Leadership-ready in one click",
    body: "Generate management-consulting-style summaries of the operation and export to PDF or Markdown.",
    points: ["One-click leadership summaries", "PDF export", "Markdown export"],
    visual: (
      <div className="rounded-xl border border-border bg-background p-4">
        <div className="h-2 w-1/3 rounded bg-primary/30" />
        <div className="mt-3 space-y-1.5">
          <div className="h-1.5 w-full rounded bg-muted" />
          <div className="h-1.5 w-5/6 rounded bg-muted" />
          <div className="h-1.5 w-4/6 rounded bg-muted" />
        </div>
        <div className="mt-3 h-2 w-1/4 rounded bg-primary/30" />
        <div className="mt-2 space-y-1.5">
          <div className="h-1.5 w-full rounded bg-muted" />
          <div className="h-1.5 w-3/4 rounded bg-muted" />
        </div>
      </div>
    ),
  },
  {
    icon: Globe2,
    eyebrow: "Network View",
    title: "Your network on a live map",
    body: "An animated world map of warehouses, suppliers, routes and delay hotspots — and the operational relationships between them.",
    points: ["Warehouses, suppliers & routes", "Delay hotspots", "Operational relationships"],
    visual: (
      <svg viewBox="0 0 280 120" className="w-full">
        <path
          d="M30 80 C 90 30, 160 100, 250 40"
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="1.5"
        />
        <path
          d="M30 80 C 90 30, 160 100, 250 40"
          fill="none"
          stroke="hsl(221 83% 53%)"
          strokeWidth="1.8"
          strokeDasharray="6 8"
          className="animate-dash-flow"
        />
        {[
          [30, 80],
          [250, 40],
          [140, 66],
        ].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="4" fill="hsl(221 83% 53%)" />
        ))}
        <circle r="3" fill="hsl(142 71% 45%)">
          <animateMotion
            dur="4s"
            repeatCount="indefinite"
            path="M30 80 C 90 30, 160 100, 250 40"
          />
        </circle>
      </svg>
    ),
  },
];

const STEPS = [
  { icon: Cable, t: "Connect operational data" },
  { icon: Workflow, t: "Normalize & validate" },
  { icon: BarChart3, t: "Generate intelligence" },
  { icon: ShieldCheck, t: "Assess risk" },
  { icon: Brain, t: "Recommend actions" },
  { icon: Radar, t: "Support decisions" },
];

const ARCH = [
  { icon: Globe2, label: "Frontend" },
  { icon: Cable, label: "API Gateway" },
  { icon: Workflow, label: "FastAPI Services" },
  { icon: ShieldCheck, label: "Risk Engine" },
  { icon: BarChart3, label: "Analytics" },
  { icon: Brain, label: "AI Layer" },
  { icon: Database, label: "PostgreSQL" },
  { icon: Network, label: "External Systems" },
];

export default function PlatformPage() {
  return (
    <>
      <PageHero
        eyebrow="Platform"
        title="The full operational decision loop"
        description="ATLASOPS spans connect, understand, assess, decide and act — so your operation runs on intelligence instead of guesswork."
      >
        <PrimaryButton href="/get-started">Start Free Demo</PrimaryButton>
      </PageHero>

      {/* Feature deep-dives */}
      <Section>
        <Container>
          <div className="space-y-20 sm:space-y-28">
            {FEATURES.map((f, i) => {
              const flip = i % 2 === 1;
              return (
                <div
                  key={f.title}
                  className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16"
                  id={f.eyebrow === "Operations Copilot" ? "copilot" : undefined}
                >
                  <Reveal className={cn(flip && "lg:order-2")}>
                    <Eyebrow>{f.eyebrow}</Eyebrow>
                    <h3 className="mt-4 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                      {f.title}
                    </h3>
                    <p className="mt-4 leading-relaxed text-muted-foreground">
                      {f.body}
                    </p>
                    <ul className="mt-6 space-y-3">
                      {f.points.map((p) => (
                        <li
                          key={p}
                          className="flex items-center gap-3 text-sm text-foreground"
                        >
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary">
                            <f.icon className="h-3 w-3" />
                          </span>
                          {p}
                        </li>
                      ))}
                    </ul>
                  </Reveal>
                  <Reveal
                    delay={120}
                    className={cn(
                      "rounded-2xl border border-border bg-card p-6 shadow-card",
                      flip && "lg:order-1",
                    )}
                  >
                    {f.visual}
                  </Reveal>
                </div>
              );
            })}
          </div>
        </Container>
      </Section>

      {/* How it works */}
      <Section id="how-it-works" className="border-y border-border bg-muted/30">
        <Container>
          <SectionHeading
            eyebrow="How it works"
            title="From raw data to confident decisions"
          />
          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
            {STEPS.map((s, i) => (
              <Reveal
                key={s.t}
                delay={i * 60}
                className="rounded-2xl border border-border bg-background p-5 text-center"
              >
                <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <s.icon className="h-5 w-5" />
                </span>
                <p className="mt-3 font-mono text-[11px] font-semibold text-muted-foreground/60">
                  0{i + 1}
                </p>
                <p className="mt-1 text-sm font-medium text-foreground">{s.t}</p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* Architecture */}
      <Section id="architecture">
        <Container>
          <SectionHeading
            eyebrow="Architecture"
            title="A clean, layered system"
            description="Each layer has a single responsibility, which keeps the platform observable, testable and ready for production deployment."
          />
          <Reveal className="mt-14 rounded-2xl border border-border bg-card p-6 sm:p-8">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {ARCH.map((l, i) => (
                <div
                  key={l.label}
                  className="flex items-center gap-3 rounded-xl border border-border bg-background p-4"
                  style={{ animation: `fade-up 0.5s ease-out ${i * 70}ms both` }}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <l.icon className="h-5 w-5" />
                  </span>
                  <p className="text-sm font-semibold text-foreground">
                    {l.label}
                  </p>
                </div>
              ))}
            </div>
          </Reveal>
          <Reveal className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Cloud className="h-4 w-4 text-primary" />
            Containerized with Docker · documented API · environment-based
            configuration
          </Reveal>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
