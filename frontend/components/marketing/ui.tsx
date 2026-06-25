import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";
import { Reveal } from "@/components/marketing/reveal";
import { cn } from "@/lib/utils";

export function Container({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto max-w-7xl px-5 lg:px-8", className)}>
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
      {children}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  align?: "center" | "left";
  className?: string;
}) {
  return (
    <Reveal
      className={cn(
        "max-w-2xl",
        align === "center" ? "mx-auto text-center" : "text-left",
        className,
      )}
    >
      {eyebrow && (
        <div className={cn("mb-4", align === "center" && "flex justify-center")}>
          <Eyebrow>{eyebrow}</Eyebrow>
        </div>
      )}
      <h2 className="text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
          {description}
        </p>
      )}
    </Reveal>
  );
}

export function Section({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={cn("py-20 sm:py-28", className)}>
      {children}
    </section>
  );
}

export function PrimaryButton({
  href,
  children,
  className,
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:shadow-md hover:brightness-110",
        className,
      )}
    >
      {children}
      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export function SecondaryButton({
  href,
  children,
  className,
}: {
  href: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-background px-5 py-3 text-sm font-semibold text-foreground transition-colors hover:bg-accent",
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function PageHero({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="hero-grid pointer-events-none absolute inset-0" />
      <div className="radial-fade pointer-events-none absolute inset-0" />
      <Container className="relative py-20 text-center sm:py-28">
        <Reveal>
          <div className="flex justify-center">
            <Eyebrow>{eyebrow}</Eyebrow>
          </div>
        </Reveal>
        <Reveal delay={80}>
          <h1 className="mx-auto mt-5 max-w-3xl text-balance text-4xl font-semibold leading-[1.08] tracking-tight text-foreground sm:text-5xl">
            {title}
          </h1>
        </Reveal>
        {description && (
          <Reveal delay={160}>
            <p className="mx-auto mt-5 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
              {description}
            </p>
          </Reveal>
        )}
        {children && (
          <Reveal delay={240}>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              {children}
            </div>
          </Reveal>
        )}
      </Container>
    </section>
  );
}

export function CTASection() {
  return (
    <Section>
      <Container>
        <Reveal className="relative overflow-hidden rounded-3xl border border-border bg-foreground px-6 py-16 text-center sm:px-16">
          <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:radial-gradient(circle_at_50%_0%,#fff,transparent_60%)]" />
          <div className="dotgrid pointer-events-none absolute inset-0 opacity-10" />
          <div className="relative">
            <h2 className="mx-auto max-w-2xl text-balance text-3xl font-semibold tracking-tight text-background sm:text-4xl">
              See your entire operation in one place
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-pretty text-base text-background/70">
              Provision a fully populated demo workspace in seconds, or connect
              your own systems and start building your operational picture.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                href="/get-started"
                className="group inline-flex items-center justify-center gap-2 rounded-lg bg-background px-5 py-3 text-sm font-semibold text-foreground transition-all hover:brightness-95"
              >
                Start Free Demo
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="/get-started"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-background/25 px-5 py-3 text-sm font-semibold text-background transition-colors hover:bg-background/10"
              >
                Book a Demo
              </Link>
            </div>
          </div>
        </Reveal>
      </Container>
    </Section>
  );
}
