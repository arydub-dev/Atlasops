import type { Metadata } from "next";
import {
  Boxes,
  FileCheck2,
  FileText,
  KeyRound,
  Lock,
  Network,
  ScrollText,
  Server,
  Settings2,
  ShieldCheck,
  TerminalSquare,
  UserCog,
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
  title: "Security",
  description:
    "ATLASOPS security overview: role-based access control, JWT authentication, secure password hashing, tenant isolation, audit logging and containerized deployment.",
};

const GROUPS: {
  title: string;
  items: { icon: typeof Lock; title: string; body: string }[];
}[] = [
  {
    title: "Authentication & Access",
    items: [
      {
        icon: KeyRound,
        title: "JWT authentication",
        body: "Access is granted via signed JSON Web Tokens issued through an OAuth2 password flow. Tokens are verified on every request, so the API never trusts an unauthenticated caller.",
      },
      {
        icon: UserCog,
        title: "Role-based access control",
        body: "A dependency-based authorization layer enforces roles (admin, operations manager, analyst, executive) at the endpoint level, following the principle of least privilege.",
      },
      {
        icon: Lock,
        title: "Secure password hashing",
        body: "Passwords are never stored in plaintext. They are hashed with bcrypt via passlib, so credentials remain protected even at rest.",
      },
      {
        icon: ScrollText,
        title: "Session management",
        body: "Token lifecycles are handled on the client with centralized handling for expiry and re-authentication, keeping session state predictable.",
      },
    ],
  },
  {
    title: "Data & Tenancy",
    items: [
      {
        icon: Network,
        title: "Tenant isolation architecture",
        body: "The data model and service layer are structured so that multi-tenant isolation can be enforced consistently, keeping one organization's data separate from another's.",
      },
      {
        icon: FileText,
        title: "Audit logging",
        body: "Sensitive actions are recorded to an audit log, creating a traceable history of who did what and when across the platform.",
      },
      {
        icon: FileCheck2,
        title: "Input validation",
        body: "Every request and ingestion row is validated with Pydantic schemas before it reaches business logic, rejecting malformed or unexpected data early.",
      },
    ],
  },
  {
    title: "API & Network",
    items: [
      {
        icon: ShieldCheck,
        title: "Secure API design",
        body: "Thin controllers delegate to well-defined services. Schemas constrain inputs and outputs, reducing the surface area for injection and over-posting.",
      },
      {
        icon: Server,
        title: "Encrypted communication",
        body: "The platform is designed to run behind TLS so traffic between clients, the API and external systems is encrypted in transit.",
      },
      {
        icon: ShieldCheck,
        title: "Security headers",
        body: "Responses are intended to be served with hardening headers at the edge, reducing common browser-side attack vectors.",
      },
    ],
  },
  {
    title: "Deployment & Operations",
    items: [
      {
        icon: Boxes,
        title: "Containerized deployment",
        body: "The backend and frontend ship as Docker images orchestrated with Docker Compose, giving reproducible, isolated runtime environments.",
      },
      {
        icon: Settings2,
        title: "Configuration management",
        body: "Configuration is driven by environment variables through pydantic-settings, keeping secrets out of source control.",
      },
      {
        icon: TerminalSquare,
        title: "Structured logging",
        body: "Structured logs make operational and security-relevant events observable and easy to ship to a central system.",
      },
    ],
  },
];

export default function SecurityPage() {
  return (
    <>
      <PageHero
        eyebrow="Security"
        title="Security-first architecture, explained"
        description="We describe concrete architectural decisions rather than slogans. Here is what ATLASOPS actually implements — and why each choice matters."
      />

      {/* Honesty note */}
      <Section className="pb-0">
        <Container>
          <Reveal className="mx-auto max-w-3xl rounded-2xl border border-border bg-muted/40 p-5 text-sm leading-relaxed text-muted-foreground">
            We avoid absolute claims like &ldquo;unbreakable&rdquo; or
            &ldquo;bank-grade.&rdquo; No system is perfectly secure. Instead, this
            page documents the specific controls and design decisions in the
            platform so you can evaluate them on technical merit.
          </Reveal>
        </Container>
      </Section>

      <Section>
        <Container>
          <div className="space-y-16">
            {GROUPS.map((g) => (
              <div key={g.title}>
                <SectionHeading align="left" title={g.title} className="max-w-xl" />
                <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {g.items.map((it, i) => (
                    <Reveal
                      key={it.title}
                      delay={(i % 3) * 60}
                      className="rounded-2xl border border-border bg-card p-6"
                    >
                      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <it.icon className="h-5 w-5" />
                      </span>
                      <h3 className="mt-4 text-base font-semibold text-foreground">
                        {it.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                        {it.body}
                      </p>
                    </Reveal>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Container>
      </Section>

      <CTASection />
    </>
  );
}
