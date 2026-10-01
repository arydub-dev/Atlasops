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
    "ATLASOPS plans for a focused operational pilot, growing teams, and enterprise requirements. Final pricing is agreed before purchase.",
};

const TIERS = [
  {
    name: "Starter",
    price: "Pilot quote",
    cadence: "",
    desc: "For small teams validating shipment, inventory and supplier visibility.",
    cta: "Discuss a pilot",
    href: "/contact",
    featured: false,
    features: [
      "10 users and up to 3 connectors",
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
    href: "/contact",
    featured: true,
    features: [
      "50 users and up to 15 connectors",
      "Connect your own data sources",
      "Self-serve CSV & Excel ingestion",
      "Salesforce, Dynamics BC and UPS connectors (beta)",
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
    href: "/contact",
    featured: false,
    features: [
      "Everything in Professional",
      "Multi-tenant orgs with PostgreSQL RLS (Available)",
      "Audit logging & advanced governance",
      "Enterprise SSO (email-first, Available)",
      "Dynamics BC, Salesforce & UPS connectors (Beta)",
      "Deployment & onboarding assistance",
    ],
  },
];

const FAQ = [
  {
    q: "Can I try ATLASOPS without connecting any systems?",
    a: "A guided demonstration uses clearly synthetic data. Production organizations begin with their own data; a demo does not prove your integration works.",
  },
  {
    q: "What data sources can I connect?",
    a: "CSV and Excel import are self-serve. Dynamics 365 Business Central, Salesforce, and UPS Tracking are available in Beta. Additional ERPs (SAP, Oracle, etc.) are Coming Soon.",
  },
  {
    q: "How is access controlled?",
    a: "Authentication is email-first enterprise SSO: enter your work email and ATLASOPS routes you to your organization's identity provider. Sessions use httpOnly cookies. Role-based permissions enforce least privilege per endpoint.",
  },
  {
    q: "How is ATLASOPS deployed?",
    a: "The platform is cloud-native and containerized with Docker, configured through environment variables, with shared PostgreSQL and row-level security for tenant isolation.",
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHero
        eyebrow="Pricing"
        title="Start with a focused pilot."
        description="Agree on a scope, data source and success criteria before expanding. Pricing and service commitments are confirmed in your quote."
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
