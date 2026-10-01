import { SITE_URL, SITE_DESCRIPTION, IS_PREVIEW } from "@/lib/site";
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "ATLASOPS — Intelligent Supply Chains. Confident Decisions.", template: "%s | ATLASOPS" },
  description: SITE_DESCRIPTION,
  robots: IS_PREVIEW ? { index: false, follow: false } : { index: true, follow: true },
  icons: { icon: [{ url: "/favicon.png", sizes: "96x96", type: "image/png" }], apple: "/apple-touch-icon.png" },
  openGraph: { title: "ATLASOPS — Intelligent Supply Chains. Confident Decisions.", description: SITE_DESCRIPTION, type: "website", siteName: "ATLASOPS", images: [{ url: "/brand-logo.png", width: 512, height: 512, alt: "ATLASOPS" }] },
  twitter: { card: "summary", title: "ATLASOPS — Supply Chain Intelligence", description: SITE_DESCRIPTION, images: ["/brand-logo.png"] },
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
