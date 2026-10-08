"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/brand/logo";

export default function DemoLoginPage() {
  const { refresh } = useAuth();
  const router = useRouter();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      await api.post("/auth/demo-login", { login_id: loginId, password });
      setPassword("");
      const me = await refresh();
      if (!me?.current_organization) throw new Error("Could not open the demo workspace.");
      router.push("/mission-control");
    } catch (e) { setError(e instanceof Error ? e.message : "Sign-in failed"); }
    finally { setBusy(false); }
  }
  return <main className="flex min-h-screen items-center justify-center px-6 py-12">
    <div className="w-full max-w-sm space-y-6">
      <Logo />
      <div><h1 className="text-2xl font-semibold">Private product demo</h1>
        <p className="mt-2 text-sm text-muted-foreground">Use the credentials shared with you by the AtlasOps team. Explore a fictional company; the account’s role determines which actions you can take.</p></div>
      <form onSubmit={submit} className="space-y-4">
        <div className="space-y-2"><Label htmlFor="demo-id">Login ID</Label><Input id="demo-id" autoComplete="username" value={loginId} onChange={e=>setLoginId(e.target.value)} required maxLength={100} /></div>
        <div className="space-y-2"><Label htmlFor="demo-password">Password</Label><Input id="demo-password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required maxLength={72} /></div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button className="w-full" disabled={busy}>{busy ? "Signing in…" : "Open demo"}</Button>
      </form>
    </div>
  </main>;
}
