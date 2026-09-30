import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  const origin = process.env.NEXT_PUBLIC_SITE_URL;
  return {
    rules: origin ? { userAgent: "*", allow: ["/", "/platform", "/solutions", "/pricing"], disallow: ["/admin", "/settings", "/onboarding", "/mission-control", "/privacy", "/terms"] } : { userAgent: "*", disallow: "/" },
    ...(origin ? { sitemap: `${origin.replace(/\/$/, "")}/sitemap.xml` } : {}),
  };
}
