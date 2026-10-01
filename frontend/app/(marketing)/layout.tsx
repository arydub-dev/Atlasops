import { SITE_URL, SITE_DESCRIPTION } from "@/lib/site";
import type { ReactNode } from "react";
import { MarketingNav } from "@/components/marketing/nav";
import { MarketingFooter } from "@/components/marketing/footer";
import { MarketingThemeLock } from "@/components/marketing/theme-lock";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <MarketingThemeLock />
      <MarketingNav />
      <main className="flex-1 pt-16"><script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify({"@context":"https://schema.org", "@graph":[{"@type":"Organization", "@id":`${SITE_URL}/#organization`, name:"ATLASOPS", url:SITE_URL, logo:`${SITE_URL}/brand-logo.png`},{"@type":"WebSite", name:"ATLASOPS", url:SITE_URL, description:SITE_DESCRIPTION, publisher:{"@id":`${SITE_URL}/#organization`}}]}).replace(/</g, "\\u003c")}} />{children}</main>
      <MarketingFooter />
    </div>
  );
}
