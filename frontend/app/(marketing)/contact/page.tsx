"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

export default function ContactPage() {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setStatus("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${API_BASE}/api/v1/leads`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...Object.fromEntries(data), consent: data.get("consent") === "on" }),
      });
      if (!response.ok) throw new Error(response.status === 503 ? "Demo requests are not open yet. Please try again later." : "We couldn’t save your request. Check the fields and try again.");
      setStatus("Your demo request has been saved. Our team will review it and contact you.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Please try again."); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-2xl px-6 py-20">
    <h1 className="text-4xl font-semibold">See ATLASOPS with your team</h1>
    <p className="mt-4 text-muted-foreground">Tell us where visibility breaks down. We’ll discuss a focused pilot using your shipment, inventory, or supplier data.</p>
    <form onSubmit={submit} className="mt-8 space-y-5">
      {[["name", "Your name", 120], ["email", "Work email", 254], ["company", "Company", 160], ["role", "Role", 100], ["company_size", "Company size", 50], ["phone", "Phone (optional)", 40]].map(([name, label, max]) =>
        <label key={name} className="block text-sm font-medium">{label}<input name={String(name)} type={name === "email" ? "email" : "text"} maxLength={Number(max)} required={name !== "phone"} className="mt-2 block w-full rounded-lg border border-border bg-background p-3" /></label>)}
      <label className="block text-sm font-medium">What is your main operational challenge?<textarea name="problem" required minLength={10} maxLength={2000} rows={4} className="mt-2 block w-full rounded-lg border border-border bg-background p-3" /></label>
      <div hidden aria-hidden="true"><label>Website<input name="website" tabIndex={-1} autoComplete="off" /></label></div>
      <p className="text-sm text-muted-foreground">Please don’t include customer records, credentials, or sensitive shipment details.</p>
      <label className="flex gap-3 text-sm"><input type="checkbox" name="consent" required />I agree to be contacted about this request. My details will be stored for this inquiry. <Link href="/privacy" className="underline">Data handling</Link></label>
      <button disabled={busy} className="rounded-lg bg-primary px-5 py-3 font-medium text-primary-foreground disabled:opacity-50">{busy ? "Saving…" : "Request a demo"}</button>
      <p role="status" aria-live="polite">{status}</p>
    </form>
  </main>;
}
