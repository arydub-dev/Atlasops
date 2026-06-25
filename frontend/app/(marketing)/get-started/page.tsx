"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Boxes,
  Building2,
  Check,
  Database,
  Plug,
  Sparkles,
} from "lucide-react";
import { Reveal } from "@/components/marketing/reveal";
import { Container, Eyebrow } from "@/components/marketing/ui";
import { cn } from "@/lib/utils";

const WORKSPACES = [
  {
    id: "demo",
    icon: Boxes,
    title: "Demo Workspace",
    badge: "Recommended",
    desc: "Provision a fully populated operation instantly — no setup required.",
    features: [
      "Suppliers, warehouses & products",
      "Inventory, shipments & alerts",
      "Risk assessments & executive reports",
    ],
  },
  {
    id: "connect",
    icon: Plug,
    title: "Connect Your Organization",
    badge: "Bring your data",
    desc: "Start with empty states and build your operational picture from your systems.",
    features: [
      "Import via CSV & Excel",
      "Configure connector templates",
      "Monitor pipelines & sync status",
    ],
  },
];

export default function GetStartedPage() {
  const router = useRouter();
  const [choice, setChoice] = useState<"demo" | "connect">("demo");

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
              Choose how you want to begin
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-4 max-w-xl text-pretty text-muted-foreground sm:text-lg">
              Explore a complete demo operation, or connect your own data and
              build from the ground up. You can switch modes any time.
            </p>
          </Reveal>
        </div>

        <div className="mx-auto mt-14 grid max-w-4xl gap-5 sm:grid-cols-2">
          {WORKSPACES.map((w, i) => {
            const active = choice === w.id;
            return (
              <Reveal key={w.id} delay={i * 80}>
                <button
                  type="button"
                  onClick={() => setChoice(w.id as "demo" | "connect")}
                  className={cn(
                    "flex h-full w-full flex-col rounded-2xl border p-7 text-left transition-all",
                    active
                      ? "border-primary bg-card shadow-premium ring-1 ring-primary"
                      : "border-border bg-card hover:-translate-y-1 hover:shadow-card",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={cn(
                        "flex h-12 w-12 items-center justify-center rounded-xl",
                        active
                          ? "bg-primary text-primary-foreground"
                          : "bg-primary/10 text-primary",
                      )}
                    >
                      <w.icon className="h-6 w-6" />
                    </span>
                    <span className="rounded-full border border-border bg-background px-2.5 py-1 text-[10px] font-semibold text-muted-foreground">
                      {w.badge}
                    </span>
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-foreground">
                    {w.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {w.desc}
                  </p>
                  <ul className="mt-5 space-y-2.5">
                    {w.features.map((f) => (
                      <li
                        key={f}
                        className="flex items-start gap-2.5 text-sm text-foreground"
                      >
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <span
                    className={cn(
                      "mt-6 flex items-center gap-2 text-sm font-semibold",
                      active ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    {active && <Check className="h-4 w-4" />}
                    {active ? "Selected" : "Select"}
                  </span>
                </button>
              </Reveal>
            );
          })}
        </div>

        <Reveal delay={120} className="mx-auto mt-10 max-w-md">
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="group flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:shadow-md hover:brightness-110"
          >
            {choice === "demo" ? (
              <>
                <Sparkles className="h-4 w-4" />
                Enter demo workspace
              </>
            ) : (
              <>
                <Database className="h-4 w-4" />
                Continue to connect data
              </>
            )}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </button>
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </Reveal>

        <Reveal className="mx-auto mt-10 flex max-w-md items-center justify-center gap-2 text-center text-xs text-muted-foreground">
          <Building2 className="h-3.5 w-3.5" />
          Every dashboard clearly shows whether you&apos;re viewing demo data or
          connected systems.
        </Reveal>
      </Container>
    </section>
  );
}
