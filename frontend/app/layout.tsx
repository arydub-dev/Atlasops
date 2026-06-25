import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://atlasops.io"),
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
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
