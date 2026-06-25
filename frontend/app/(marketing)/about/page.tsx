import type { Metadata } from "next";
import {
  Brain,
  Compass,
  Eye,
  Layers,
  ShieldCheck,
  Workflow,
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
  title: "About",
  description:
    "ATLASOPS builds operational intelligence software that turns fragmented supply chain data into clear, explainable decisions.",
};

const PRINCIPLES = [
  {
    icon: Eye,
    title: "Clarity over noise",
    body: "Operations teams are drowning in dashboards. We surface what matters and explain why it matters.",
  },
  {
    icon: Brain,
    title: "Explainable by default",
    body: "Every risk score and recommendation can be traced back to the data behind it. No black boxes.",
  },
  {
    icon: Workflow,
    title: "Decisions, not just data",
    body: "Visibility is the starting point. The platform exists to drive better, faster operational decisions.",
  },
  {
    icon: ShieldCheck,
    title: "Built for production",
    body: "Security, configuration and deployment are first-class concerns, not afterthoughts.",
  },
  {
    icon: Layers,
    title: "Open by architecture",
    body: "An API-first, extensible design means ATLASOPS fits into the systems you already run.",
  },
  {
    icon: Compass,
    title: "Operator-led design",
    body: "The product is shaped by how operations actually work — from the floor to the boardroom.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHero
        eyebrow="About"
        title="We turn operational data into operational intelligence"
        description="ATLASOPS exists to give supply chain teams a single, trustworthy view of their operation — and the intelligence to act on it."
      />

      <Section>
        <Container>
          <div className="mx-auto max-w-3xl space-y-6 text-pretty text-lg leading-relaxed text-muted-foreground">
            <Reveal>
              <p>
                Modern supply chains run on a patchwork of systems — ERP, warehouse
                and transportation platforms, CRMs, spreadsheets and email. Each
                holds a piece of the truth, and none of them holds all of it. The
                cost shows up as blind spots, manual reporting, and decisions made
                too late.
              </p>
            </Reveal>
            <Reveal delay={80}>
              <p>
                ATLASOPS brings those pieces together into a single operational
                model, then layers risk intelligence, simulation and an Operations
                Copilot on top. The result is a platform that answers three
                questions clearly:{" "}
                <span className="font-medium text-foreground">
                  what is happening, why is it happening, and what should we do next.
                </span>
              </p>
            </Reveal>
            <Reveal delay={160}>
              <p>
                We build deliberately — favoring explainable models, clean
                architecture and concrete security decisions over hype. The goal is
                software that operations teams can trust with real decisions.
              </p>
            </Reveal>
          </div>
        </Container>
      </Section>

      <Section className="border-y border-border bg-muted/30">
        <Container>
          <SectionHeading eyebrow="Principles" title="What guides the product" />
          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {PRINCIPLES.map((p, i) => (
              <Reveal
                key={p.title}
                delay={(i % 3) * 60}
                className="rounded-2xl border border-border bg-background p-6"
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

      <CTASection />
    </>
  );
}
