"use client";

import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth";

const STEPS = [
  { href: "/onboarding", label: "Organization" },
  { href: "/onboarding/plan", label: "Plan" },
  { href: "/onboarding/import", label: "Import" },
  { href: "/onboarding/connect", label: "Connect" },
  { href: "/onboarding/invite", label: "Invite" },
  { href: "/onboarding/done", label: "Done" },
];

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-b from-background via-background to-muted/30">
      <header className="border-b border-border/60 bg-background/80 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <Logo />
          <button
            type="button"
            onClick={() => void logout()}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="mx-auto max-w-3xl px-6 py-10">
        <nav className="mb-8 flex flex-wrap gap-2">
          {STEPS.map((s, i) => (
            <span
              key={s.href}
              className="rounded-md border border-border/60 bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground"
            >
              {i + 1}. {s.label}
            </span>
          ))}
        </nav>
        {children}
      </div>
    </div>
  );
}
