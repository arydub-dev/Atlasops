import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
  title: {
    default: "ATLASOPS — Operational Intelligence for Modern Supply Chains",
    template: "%s · ATLASOPS",
  },
  description:
    "ATLASOPS is a cloud-based operational intelligence platform that unifies operational data, monitors risk, coordinates decisions, and turns fragmented supply chain information into actionable intelligence.",
  keywords: [
    "supply chain",
    "operational intelligence",
    "risk monitoring",
    "ERP integration",
    "control tower",
    "enterprise SaaS",
  ],
  openGraph: {
    title: "ATLASOPS — Operational Intelligence for Modern Supply Chains",
    description:
      "Unify operational data, monitor risk, coordinate decisions, and transform fragmented supply chain information into actionable intelligence.",
    type: "website",
    siteName: "ATLASOPS",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
