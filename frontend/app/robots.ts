import type { MetadataRoute } from "next";
import { SITE_URL, IS_PREVIEW } from "@/lib/site";
export default function robots(): MetadataRoute.Robots {
 return { rules: IS_PREVIEW ? {userAgent: "*", disallow: "/"} : {userAgent: "*", allow: "/", disallow: ["/api/", "/admin", "/settings", "/onboarding", "/mission-control", "/login", "/auth/", "/privacy", "/terms"]}, ...(!IS_PREVIEW ? {sitemap: `${SITE_URL}/sitemap.xml`} : {}) };
}
