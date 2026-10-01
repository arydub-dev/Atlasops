import type { Metadata } from "next";
import Link from "next/link";
export const metadata: Metadata = {title: "Supply Chain Intelligence Features", description: "Explore shipment visibility, inventory intelligence, supplier risk, scenario planning and the ATLASOPS Operations Copilot.", alternates: {canonical: "/features"}};
const features = [
 ["Shipment visibility", "Bring shipment status and operational exceptions into one workspace so teams can investigate delays and coordinate a response."],
 ["Inventory intelligence", "Review stock levels, identify shortages and excess inventory, and focus attention on the products that need action."],
 ["Supplier risk", "Compare supplier performance and risk indicators to support better sourcing and operational decisions."],
 ["Scenario planning", "Explore the potential impact of disruptions before committing to a response. Scenarios support judgment; they do not guarantee outcomes."],
 ["Operations Copilot", "Use AI-assisted explanations to understand available operational data, with human review of recommended actions."],
 ["Connected teams", "Organize company workspaces, invite colleagues, and control access with roles. Connector availability is validated during onboarding."],
];
export default function Features() { return <main className="mx-auto max-w-6xl px-6 py-24"><p className="text-sm font-semibold uppercase tracking-widest text-primary">ATLASOPS features</p><h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">One workspace. A clearer view of your supply chain.</h1><p className="mt-6 max-w-2xl text-lg text-muted-foreground">Connect operational data, understand risk, and help your team make informed decisions.</p><div className="mt-12 grid gap-6 md:grid-cols-2">{features.map(([title,body]) => <section key={title} className="rounded-2xl border border-border bg-card p-7"><h2 className="text-xl font-semibold">{title}</h2><p className="mt-3 leading-relaxed text-muted-foreground">{body}</p></section>)}</div><div className="mt-10 flex flex-wrap gap-4"><Link href="/get-started" className="rounded-lg bg-primary px-6 py-3 font-semibold text-primary-foreground">Try for free</Link><Link href="/contact" className="rounded-lg border border-border px-6 py-3 font-semibold">Connect with us</Link></div></main>; }
