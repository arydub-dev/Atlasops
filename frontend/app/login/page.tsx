"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, Loader2, ShieldCheck, Sparkles } from "lucide-react";
import { isBusinessEmail } from "@/lib/business-email";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const IS_DEV =
  process.env.NODE_ENV === "development" && process.env.NEXT_PUBLIC_DEV_LOGIN === "true";

type Phase = "idle" | "checking" | "redirecting" | "authenticating";

const PHASE_COPY: Record<Exclude<Phase, "idle">, string> = {
  checking: "Checking your organization…",
  redirecting: "Redirecting to your identity provider…",
  authenticating: "Authenticating…",
};

function LoginForm() {
  const { continueWithEmail, devLogin, user, currentOrganization, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isSignup = searchParams.get("signup") === "1";
  const inviteToken = searchParams.get("invite") || searchParams.get("token");

  const [error, setError] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [email, setEmail] = useState("");
  const [remember, setRemember] = useState(true);
  const [devEmail, setDevEmail] = useState("");
  const [fullName, setFullName] = useState("");

  useEffect(() => {
    if (loading || !user) return;
    router.replace(currentOrganization ? "/mission-control" : "/onboarding");
  }, [loading, user, currentOrganization, router]);

  async function handleContinue(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (isSignup && !isBusinessEmail(email)) { setError("Use your company email, such as you@company.com. Personal email addresses are not accepted for signup."); return; }
    setPhase("checking");
    try {
      await continueWithEmail({
        email,
        remember_device: remember,
        invite_token: inviteToken,
        return_path: "/auth/callback",
      });
      setPhase("redirecting");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setPhase("idle");
    }
  }

  async function handleDevLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setPhase("authenticating");
    try {
      await devLogin(devEmail, fullName || devEmail.split("@")[0] || "Dev User");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dev login failed");
      setPhase("idle");
    }
  }

  const busy = phase !== "idle";

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary/15 via-background to-background p-12 lg:flex">
        <div className="absolute inset-0 grid-bg opacity-40" />
        <Logo className="relative" />

        <div className="relative space-y-6">
          <h1 className="max-w-md text-4xl font-semibold leading-tight tracking-tight">
            Operational intelligence for modern supply chains.
          </h1>
          <p className="max-w-md text-muted-foreground">
            Real-time shipment visibility, inventory intelligence, supplier scorecards, risk
            scoring, disruption simulation and an Operations Copilot — in one platform.
          </p>
          <div className="grid max-w-md gap-3 pt-2">
            {[
              { icon: Activity, text: "Live KPIs across shipments, inventory & suppliers" },
              { icon: ShieldCheck, text: "Automated risk scoring & alerting engine" },
              { icon: Sparkles, text: "Operations Copilot grounded in live data" },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 text-sm">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-4 w-4" />
                </span>
                {text}
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-muted-foreground">
          © {new Date().getFullYear()} ATLASOPS — Operational Intelligence Platform
        </p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm space-y-6">
          <div className="space-y-2 lg:hidden">
            <Logo />
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">{isSignup ? "Start your free trial" : "Welcome back"}</h2>
            <p className="text-sm text-muted-foreground">{isSignup ? "Use your company email for a 14-day trial. Personal email addresses are not accepted." : "Enter your work email to continue."}</p>
          </div>

          <form onSubmit={handleContinue} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="work-email">Work email</Label>
              <Input
                id="work-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@company.com"
                required
                disabled={busy}
              />
            </div>

            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                disabled={busy}
              />
              Remember this device
            </label>

            <Button type="submit" className="w-full" disabled={busy || !email}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Continue
            </Button>
          </form>

          {phase !== "idle" && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {PHASE_COPY[phase]}
            </p>
          )}

          {error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}

          <div className="relative py-1">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase tracking-wide">
              <span className="bg-background px-2 text-muted-foreground">or</span>
            </div>
          </div>

          <p className="text-center text-sm text-muted-foreground">
            Use your organization&apos;s SSO — we route you automatically from your work email.
          </p>

          <p className="text-center text-sm text-muted-foreground">
            Need an account?{" "}
            <Link href="/get-started" className="font-medium text-primary hover:underline">
              Request Access
            </Link>
          </p>

          {IS_DEV && (
            <Card className="space-y-3 border-dashed p-4">
              <p className="text-xs font-medium text-muted-foreground">Local development only</p>
              <form onSubmit={handleDevLogin} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="dev-email">Email</Label>
                  <Input
                    id="dev-email"
                    type="email"
                    value={devEmail}
                    onChange={(e) => setDevEmail(e.target.value)}
                    placeholder="demo@supply.local"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="dev-name">Full name</Label>
                  <Input
                    id="dev-name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Alex Operator"
                  />
                </div>
                <Button type="submit" className="w-full" variant="secondary" disabled={busy}>
                  Dev sign-in
                </Button>
              </form>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
