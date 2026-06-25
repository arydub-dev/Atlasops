import Link from "next/link";
import { Logo } from "@/components/brand/logo";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Platform", href: "/platform" },
      { label: "Solutions", href: "/solutions" },
      { label: "Integrations", href: "/integrations" },
      { label: "Pricing", href: "/pricing" },
      { label: "Security", href: "/security" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "How it works", href: "/platform#how-it-works" },
      { label: "Architecture", href: "/platform#architecture" },
      { label: "Operations Copilot", href: "/platform#copilot" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Login", href: "/login" },
      { label: "Get Started", href: "/get-started" },
      { label: "Book a Demo", href: "/get-started" },
    ],
  },
];

export function MarketingFooter() {
  return (
    <footer className="border-t border-border bg-muted/30">
      <div className="mx-auto max-w-7xl px-5 py-16 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Operational intelligence for modern supply chains. Unify data,
              monitor risk, and coordinate decisions across your operation.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {["Cloud-native", "API-first", "Multi-tenant ready"].map((b) => (
                <span
                  key={b}
                  className="rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground"
                >
                  {b}
                </span>
              ))}
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <p className="text-sm font-semibold text-foreground">
                {col.title}
              </p>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col items-start justify-between gap-4 border-t border-border pt-6 text-sm text-muted-foreground sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} ATLASOPS, Inc. All rights reserved.</p>
          <div className="flex items-center gap-5">
            <Link href="/security" className="hover:text-foreground">
              Security
            </Link>
            <span className="hover:text-foreground">Privacy</span>
            <span className="hover:text-foreground">Terms</span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-success" />
              All systems operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
