"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, Plug, Sparkles } from "lucide-react";
import { Reveal } from "@/components/marketing/reveal";
import { Container, Eyebrow } from "@/components/marketing/ui";

export default function GetStartedPage() {
  const router = useRouter();

  return (
    <section className="relative overflow-hidden">
      <div className="hero-grid pointer-events-none absolute inset-0" />
      <div className="radial-fade pointer-events-none absolute inset-0" />
      <Container className="relative py-20 sm:py-28">
        <div className="mx-auto max-w-2xl text-center">
          <Reveal>
            <div className="flex justify-center">
              <Eyebrow>Get started</Eyebrow>
            </div>
          </Reveal>
          <Reveal delay={80}>
            <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
              Intelligent operations start here
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-4 max-w-xl text-pretty text-muted-foreground sm:text-lg">
              Try ATLASOPS free for 14 days with your company email, or connect with us for enterprise access.
            </p>
          </Reveal>
        </div>

        <div className="mx-auto mt-14 grid max-w-3xl gap-5 sm:grid-cols-2">
          <Reveal>
            <button
              type="button"
              onClick={() => router.push("/login?signup=1")}
              className="flex h-full w-full flex-col rounded-2xl border border-primary bg-card p-7 text-left shadow-premium ring-1 ring-primary transition-all hover:-translate-y-1"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Sparkles className="h-6 w-6" />
              </span>
              <h3 className="mt-5 text-lg font-semibold text-foreground">Try for free</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Enter your work email — ATLASOPS routes you to your organization&apos;s SSO
                automatically, then into Mission Control or onboarding.
              </p>
              <span className="mt-6 flex items-center gap-2 text-sm font-semibold text-primary">
                Start your free trial
                <ArrowRight className="h-4 w-4" />
              </span>
            </button>
          </Reveal>
          <Reveal delay={80}>
            <button
              type="button"
              onClick={() => router.push("/contact")}
              className="flex h-full w-full flex-col rounded-2xl border border-border bg-card p-7 text-left transition-all hover:-translate-y-1 hover:shadow-card"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Building2 className="h-6 w-6" />
              </span>
              <h3 className="mt-5 text-lg font-semibold text-foreground">Enterprise access</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Discuss your company’s integration, security, and rollout requirements with our team.
              </p>
              <span className="mt-6 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                Connect with us
                <ArrowRight className="h-4 w-4" />
              </span>
            </button>
          </Reveal>
        </div>

        <Reveal delay={120} className="mx-auto mt-10 max-w-md text-center text-xs text-muted-foreground">
          <Plug className="mx-auto mb-2 h-3.5 w-3.5" />
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </Reveal>
      </Container>
    </section>
  );
}
