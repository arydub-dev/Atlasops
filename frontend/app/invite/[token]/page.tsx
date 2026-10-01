"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface InvitePreview {
  email: string;
  organization_name: string;
  role_slug: string;
  expires_at: string;
  status: string;
}

export default function InviteAcceptPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const router = useRouter();
  const { user, loading, acceptInvitation, continueWithEmail } = useAuth();
  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const acceptedRef = useRef(false);

  useEffect(() => {
    if (!token) return;
    sessionStorage.setItem("atlasops_invite_token", token);
    api
      .get<InvitePreview>(`/orgs/invitations/preview?token=${encodeURIComponent(token)}`)
      .then(setPreview)
      .catch(() => setError("This invitation link is invalid or has expired."));
  }, [token]);

  useEffect(() => {
    if (loading || !user || !token || !preview) return;
    if (preview.status !== "pending" || acceptedRef.current) return;
    acceptedRef.current = true;
    setBusy(true);
    acceptInvitation(token).catch((err) => {
      acceptedRef.current = false;
      setError(err instanceof Error ? err.message : "Could not accept invitation");
      setBusy(false);
    });
  }, [loading, user, token, preview, acceptInvitation]);

  async function handleSignIn() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      await continueWithEmail({
        email: preview.email,
        invite_token: token,
        remember_device: true,
        return_path: "/auth/callback",
      });
    } catch {
      router.push(`/login?invite=${encodeURIComponent(token)}`);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6">
      <Logo />
      <Card className="w-full max-w-md space-y-4 p-6">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold tracking-tight">You&apos;re invited</h1>
          <p className="text-sm text-muted-foreground">
            {preview
              ? `Join ${preview.organization_name} on ATLASOPS.`
              : "Loading invitation…"}
          </p>
        </div>

        {preview && (
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium">{preview.email}</dd>
            </div>
            <div className="flex flex-wrap justify-between gap-4">
              <dt className="text-muted-foreground">Role</dt>
              <dd className="font-medium capitalize">{preview.role_slug.replaceAll("_", " ")}</dd>
            </div>
          </dl>
        )}

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}

        {!user && preview?.status === "pending" && (
          <Button className="w-full" disabled={busy || !preview} onClick={handleSignIn}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            Continue to sign in
          </Button>
        )}

        {user && busy && (
          <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Joining organization…
          </p>
        )}
      </Card>
    </div>
  );
}
