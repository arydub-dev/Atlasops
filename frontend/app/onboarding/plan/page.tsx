"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, CreditCard, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { BillingPlanInfo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function OnboardingPlanPage() {
  const { user, currentOrganization } = useAuth();
  const router = useRouter();
  const [plans, setPlans] = useState<BillingPlanInfo[]>([]);
  const [selected, setSelected] = useState<string>("starter");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    if (!currentOrganization) {
      router.replace("/onboarding");
      return;
    }
    api
      .get<BillingPlanInfo[]>("/billing/plans")
      .then((p) => {
        setPlans(p);
        if (p.length && !p.some((x) => x.slug === selected)) {
          setSelected(p[0].slug);
        }
      })
      .catch(() => {
        setPlans([
          {
            slug: "starter",
            name: "Starter",
            description: "For small ops teams connecting their first data sources.",
            seat_limit: 10,
            connector_limit: 3,
            ai_credits_monthly: 5000,
            features: ["mission", "shipments", "inventory", "connectors"],
            trial_days: 0,
          },
          {
            slug: "professional",
            name: "Professional",
            description: "For teams running real operations on connected data.",
            seat_limit: 50,
            connector_limit: 15,
            ai_credits_monthly: 25000,
            features: ["mission", "shipments", "ai_reports", "connectors"],
            trial_days: 0,
          },
        ]);
      });
  }, [user, currentOrganization, router, selected]);

  async function startCheckout() {
    if (!currentOrganization || !user) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.post<{ url?: string; checkout_url?: string }>(
        `/billing/checkout/${currentOrganization.id}`,
        {
          plan: selected,
          interval: "monthly",
          seat_quantity: 1,
          customer_email: user.email,
          success_url: `${window.location.origin}/onboarding/import`,
          cancel_url: `${window.location.origin}/onboarding/plan`,
        }
      );
      const url = result.url ?? result.checkout_url;
      if (url) {
        window.location.href = url;
        return;
      }
      router.push("/onboarding/import");
    } catch (err) {
      // Stripe may be unset — continue on trial
      const msg = err instanceof Error ? err.message : "";
      if (msg.toLowerCase().includes("stripe") || msg.toLowerCase().includes("503")) {
        router.push("/onboarding/import");
        return;
      }
      setError(msg || "Checkout unavailable — you can continue on trial.");
      setBusy(false);
    }
  }

  function skipTrial() {
    router.push("/onboarding/import");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CreditCard className="h-5 w-5 text-primary" />
          Choose a plan
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Start a paid plan when Stripe is configured, or continue on the trial.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {plans.map((plan) => {
            const active = selected === plan.slug;
            return (
              <button
                key={plan.slug}
                type="button"
                onClick={() => setSelected(plan.slug)}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors",
                  active ? "border-primary bg-primary/5 ring-1 ring-primary" : "border-border hover:bg-accent"
                )}
              >
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{plan.name}</p>
                  {active && <Check className="h-4 w-4 text-primary" />}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{plan.description}</p>
                <p className="mt-3 text-xs text-muted-foreground">
                  {plan.seat_limit < 0 ? "Unlimited seats" : `${plan.seat_limit} seats`} ·{" "}
                  {plan.ai_credits_monthly.toLocaleString()} AI credits / mo
                </p>
              </button>
            );
          })}
        </div>
        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button onClick={startCheckout} disabled={busy || !selected}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            Continue to checkout
          </Button>
          <Button variant="ghost" onClick={skipTrial} disabled={busy}>
            Skip — continue on trial
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
