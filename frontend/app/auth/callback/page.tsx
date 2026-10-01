"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

function AuthCallbackInner() {
  const { refresh, switchOrg } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function finish() {
      try {
        const me = await refresh();
        if (cancelled) return;
        if (!me?.user) {
          setError("Authentication did not complete. Please try signing in again.");
          return;
        }

        // If invite was part of OAuth state, membership may already exist.
        // Also support post-callback accept via query token.
        const inviteToken = params.get("token") || sessionStorage.getItem("atlasops_invite_token");
        if (inviteToken) {
          try {
            await api.post("/orgs/invitations/accept", { token: inviteToken });
            sessionStorage.removeItem("atlasops_invite_token");
            const updated = await refresh();
            if (updated?.memberships?.length && !updated.current_organization) {
              await switchOrg(updated.memberships[0].organization_id);
            }
          } catch {
            /* already accepted or mismatched — continue */
          }
        }

        const finalMe = await refresh();
        if (cancelled) return;
        if (finalMe?.current_organization) {
          router.replace("/mission-control");
        } else if (finalMe?.memberships?.length) {
          await switchOrg(finalMe.memberships[0].organization_id);
          router.replace("/onboarding/plan");
        } else {
          router.replace("/onboarding");
        }
      } catch {
        if (!cancelled) {
          setError("Something went wrong while finishing sign-in.");
        }
      }
    }

    finish();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <Logo />
      {error ? (
        <div className="max-w-sm space-y-3 text-center">
          <p className="text-sm text-destructive">{error}</p>
          <a href="/login" className="text-sm font-medium text-primary hover:underline">
            Back to sign in
          </a>
        </div>
      ) : (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Authenticating…
        </p>
      )}
    </div>
  );
}

function AuthCallbackFallback() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <Logo />
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Authenticating…
      </p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<AuthCallbackFallback />}>
      <AuthCallbackInner />
    </Suspense>
  );
}
