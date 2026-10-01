"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { Invitation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function OnboardingInvitePage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function invite(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const inv = await api.post<Invitation & { invite_url?: string; token?: string }>(
        "/orgs/current/invitations",
        {
          email: email.trim(),
          role_slug: role,
        }
      );
      const link = inv.invite_url || (inv.token ? `${window.location.origin}/invite/${inv.token}` : "");
      setMessage(
        link
          ? `Invitation ready for ${email}. Share link: ${link}`
          : `Invitation created for ${email}`
      );
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send invitation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Users className="h-5 w-5 text-primary" />
          Invite teammates
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Add colleagues now, or skip and invite them later from Settings.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <form onSubmit={invite} className="grid gap-3 sm:grid-cols-[1fr_140px_auto]">
          <div className="space-y-1.5">
            <Label htmlFor="invite-email">Email</Label>
            <Input
              id="invite-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@company.com"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="viewer">Viewer</SelectItem>
                <SelectItem value="analyst">Analyst</SelectItem>
                <SelectItem value="operations_manager">Operations Manager</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={busy || !email.trim()}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Invite
            </Button>
          </div>
        </form>
        {message && <p className="text-sm text-success">{message}</p>}
        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}
        <Button variant="ghost" onClick={() => router.push("/onboarding/done")}>
          Skip for now
        </Button>
      </CardContent>
    </Card>
  );
}
