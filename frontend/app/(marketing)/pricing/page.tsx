import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { Reveal } from "@/components/marketing/reveal";
import {
  Container,
  CTASection,
  PageHero,
  Section,
  SectionHeading,
} from "@/components/marketing/ui";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "ATLASOPS pricing: start free with a fully populated demo workspace, scale with Professional, or deploy across the organization with Enterprise.",
};

const TIERS = [
  {
    name: "Demo",
    price: "Free",
    cadence: "",
    desc: "A fully populated workspace to explore the entire platform.",
    cta: "Start Free Demo",
    href: "/get-started",
    featured: false,
    features: [
      "Pre-seeded suppliers, warehouses & shipments",
      "Mission Control & all modules",
      "Operations Copilot",
      "Risk intelligence & simulation",
      "Executive briefs",
    ],
  },
  {
    name: "Professional",
    price: "Custom",
    cadence: "/ per workspace",
    desc: "For teams running real operations on connected data.",
    cta: "Book a Demo",
    href: "/get-started",
    featured: true,
    features: [
      "Everything in Demo",
      "Connect your own data sources",
      "Self-serve CSV & Excel ingestion",
      "Connect ERP, CRM, WMS, TMS & REST APIs",
      "Pipeline monitoring & data lineage",
      "Role-based access control",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "/ per organization",
    desc: "For organizations standardizing operations across business units.",
    cta: "Contact Sales",
    href: "/get-started",
    featured: false,
    features: [
      "Everything in Professional",
      "Multi-tenant deployment",
      "Audit logging & advanced governance",
      "SSO-ready authentication architecture",
      "Custom integration support",
      "Deployment & onboarding assistance",
    ],
  },
];

const FAQ = [
  {
    q: "Can I try ATLASOPS without connecting any systems?",
    a: "Yes. The demo workspace provisions a complete, realistic dataset so you can explore every module immediately — no integration required.",
  },
  {
    q: "What data sources can I connect?",
    a: "Import from CSV and Excel yourself, or connect enterprise systems — SAP, Oracle, Salesforce, Microsoft Dynamics, your WMS/TMS and any REST API. CSV and Excel are self-serve; our team helps you connect enterprise systems during onboarding.",
  },
  {
    q: "How is access controlled?",
    a: "Authentication uses JWTs over an OAuth2 flow, and role-based access control enforces permissions per endpoint following least privilege.",
  },
  {
    q: "How is ATLASOPS deployed?",
    a: "The platform is cloud-native and containerized with Docker, configured through environment variables, and designed for multi-tenant deployment.",
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        eyebrow="Pricing"
        title="Start free. Scale when you're ready."
        description="Explore the full platform in a demo workspace at no cost, then move to connected data and organization-wide deployment when it's time."
      />

      <Section>
        <Container>
          <div className="grid gap-6 lg:grid-cols-3">
            {TIERS.map((t, i) => (
              <Reveal
                key={t.name}
                delay={i * 80}
                className={cn(
                  "relative flex flex-col rounded-3xl border p-7",
                  t.featured
                    ? "border-primary bg-card shadow-premium lg:-mt-3 lg:mb-0"
                    : "border-border bg-card",
                )}
              >
                {t.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-[11px] font-semibold text-primary-foreground">
                    Most popular
                  </span>
                )}
                <h3 className="text-lg font-semibold text-foreground">
                  {t.name}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{t.desc}</p>
                <div className="mt-5 flex items-end gap-1">
                  <span className="text-3xl font-semibold tracking-tight text-foreground">
                    {t.price}
                  </span>
                  {t.cadence && (
                    <span className="pb-1 text-xs text-muted-foreground">
                      {t.cadence}
                    </span>
                  )}
                </div>
                <Link
                  href={t.href}
                  className={cn(
                    "mt-6 inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all",
                    t.featured
                      ? "bg-primary text-primary-foreground hover:brightness-110"
                      : "border border-border bg-background text-foreground hover:bg-accent",
                  )}
                >
                  {t.cta}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <ul className="mt-7 space-y-3">
                  {t.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <span className="text-foreground">{f}</span>
                    </li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </Container>
      </Section>

      <Section className="border-t border-border bg-muted/30">
        <Container>
          <SectionHeading eyebrow="FAQ" title="Frequently asked questions" />
          <div className="mx-auto mt-12 max-w-3xl divide-y divide-border rounded-2xl border border-border bg-background">
            {FAQ.map((f) => (
              <div key={f.q} className="p-6">
                <p className="font-semibold text-foreground">{f.q}</p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.a}
                </p>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
