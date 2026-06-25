import type { Metadata } from "next";
import {
  Boxes,
  Building2,
  Factory,
  HeartPulse,
  LineChart,
  Radar,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Users,
} from "lucide-react";
import { Reveal } from "@/components/marketing/reveal";
import {
  Container,
  CTASection,
  PageHero,
  Section,
  SectionHeading,
} from "@/components/marketing/ui";

export const metadata: Metadata = {
  title: "Solutions",
  description:
    "ATLASOPS solutions for operations leaders, analysts and executives across manufacturing, retail, logistics and life sciences.",
};

const ROLES = [
  {
    icon: Radar,
    title: "Operations Leaders",
    body: "See the whole operation at a glance, catch disruptions early, and coordinate the response from a single cockpit.",
    points: ["Live operational health", "Exception management", "Recommended actions"],
  },
  {
    icon: LineChart,
    title: "Analysts",
    body: "Stop assembling decks by hand. Investigate in natural language and ground every finding in unified operational data.",
    points: ["Operations Copilot", "Scenario simulation", "Risk analysis"],
  },
  {
    icon: Users,
    title: "Executives",
    body: "Get leadership-ready situation reports and executive briefs without waiting on a reporting cycle.",
    points: ["Executive KPIs", "One-click briefs", "Impact analysis"],
  },
];

const INDUSTRIES = [
  {
    icon: Factory,
    title: "Manufacturing",
    body: "Tie supplier reliability, inbound logistics and inventory to production continuity.",
  },
  {
    icon: ShoppingCart,
    title: "Retail & CPG",
    body: "Protect availability across SKUs and channels while keeping working capital in check.",
  },
  {
    icon: Truck,
    title: "Logistics & 3PL",
    body: "Monitor lanes, carriers and delay hotspots across a distributed network.",
  },
  {
    icon: HeartPulse,
    title: "Life Sciences",
    body: "Track high-value, time-sensitive shipments with explainable risk and audit trails.",
  },
];

const OUTCOMES = [
  { stat: "Hours → minutes", label: "Reporting cycle time" },
  { stat: "Single pane", label: "Across every system" },
  { stat: "Proactive", label: "Risk detection" },
  { stat: "Explainable", label: "Decision support" },
];

export default function SolutionsPage() {
  return (
    <>
      <PageHero
        eyebrow="Solutions"
        title="Built for the people who run operations"
        description="ATLASOPS adapts to how your teams work — from the operations floor to the executive suite, across industries with complex supply chains."
      />

      <Section>
        <Container>
          <SectionHeading
            eyebrow="By role"
            title="One platform, every operational role"
          />
          <div className="mt-14 grid gap-5 lg:grid-cols-3">
            {ROLES.map((r, i) => (
              <Reveal
                key={r.title}
                delay={i * 70}
                className="rounded-2xl border border-border bg-card p-7"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <r.icon className="h-6 w-6" />
                </span>
                <h3 className="mt-5 text-lg font-semibold text-foreground">
                  {r.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {r.body}
                </p>
                <ul className="mt-5 space-y-2">
                  {r.points.map((p) => (
                    <li
                      key={p}
                      className="flex items-center gap-2 text-sm text-foreground"
                    >
                      <ShieldCheck className="h-4 w-4 text-primary" />
                      {p}
                    </li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section className="border-y border-border bg-muted/30">
        <Container>
          <SectionHeading
            eyebrow="By industry"
            title="Wherever supply chains get complex"
            description="The unified operational model fits the realities of different industries without a custom build for each one."
          />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {INDUSTRIES.map((ind, i) => (
              <Reveal
                key={ind.title}
                delay={i * 60}
                className="rounded-2xl border border-border bg-background p-6 transition-all hover:-translate-y-1 hover:shadow-card"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <ind.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-foreground">
                  {ind.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {ind.body}
                </p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section>
        <Container>
          <div className="grid gap-4 rounded-3xl border border-border bg-card p-8 sm:grid-cols-2 lg:grid-cols-4">
            {OUTCOMES.map((o, i) => (
              <Reveal key={o.label} delay={i * 60} className="text-center">
                <p className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                  {o.stat}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">{o.label}</p>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
