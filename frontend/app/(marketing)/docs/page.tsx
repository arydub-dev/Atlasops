import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Boxes,
  Cable,
  Database,
  Rocket,
  ShieldCheck,
  Sparkles,
  Terminal,
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
  title: "Documentation",
  description:
    "ATLASOPS documentation: getting started, platform concepts, integrations, the Operations Copilot, security and deployment.",
};

const SECTIONS = [
  {
    icon: Rocket,
    title: "Getting started",
    body: "Provision a demo workspace, sign in, and explore Mission Control in minutes.",
    href: "/get-started",
  },
  {
    icon: Boxes,
    title: "Platform concepts",
    body: "The unified operational model, health scores, and the decision loop.",
    href: "/platform",
  },
  {
    icon: Cable,
    title: "Integrations",
    body: "CSV & Excel ingestion, connector templates, and the ingestion pipeline.",
    href: "/integrations",
  },
  {
    icon: Database,
    title: "Data & pipeline",
    body: "Validation, transformation, data lineage and pipeline monitoring.",
    href: "/integrations#ingestion",
  },
  {
    icon: Sparkles,
    title: "Operations Copilot",
    body: "Natural-language investigation grounded in your operational data.",
    href: "/platform#copilot",
  },
  {
    icon: ShieldCheck,
    title: "Security",
    body: "Authentication, access control, tenancy, and deployment hardening.",
    href: "/security",
  },
];

export default function DocsPage() {
  return (
    <>
      <PageHero
        eyebrow="Documentation"
        title="Everything you need to run ATLASOPS"
        description="Conceptual guides and reference material for operators, analysts and engineers."
      />

      <Section>
        <Container>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {SECTIONS.map((s, i) => (
              <Reveal key={s.title} delay={(i % 3) * 60}>
                <Link
                  href={s.href}
                  className="group flex h-full flex-col rounded-2xl border border-border bg-card p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-card"
                >
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                    <s.icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 text-base font-semibold text-foreground">
                    {s.title}
                  </h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">
                    {s.body}
                  </p>
                  <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                    Read more
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      {/* Quick start */}
      <Section className="border-t border-border bg-muted/30">
        <Container>
          <SectionHeading
            eyebrow="Quick start"
            title="Run the platform locally"
            description="ATLASOPS ships with Docker Compose so you can stand up the full stack with a single command."
          />
          <Reveal className="mx-auto mt-12 max-w-3xl overflow-hidden rounded-2xl border border-border bg-foreground shadow-card">
            <div className="flex items-center gap-2 border-b border-background/10 px-4 py-2.5">
              <Terminal className="h-3.5 w-3.5 text-background/60" />
              <span className="text-xs font-medium text-background/60">
                Terminal
              </span>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-relaxed text-background/90">
              <code>{`# clone & start the full stack
git clone https://github.com/your-org/atlasops.git
cd atlasops

# bring up backend, frontend and database
docker compose up --build

# open the platform
open http://localhost:3000`}</code>
            </pre>
          </Reveal>
          <Reveal className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <BookOpen className="h-4 w-4 text-primary" />
            A demo workspace is seeded automatically on first run.
          </Reveal>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
