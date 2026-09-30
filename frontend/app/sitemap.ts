import type { MetadataRoute } from "next";
export default function sitemap(): MetadataRoute.Sitemap {
  const origin = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  return origin ? ["", "/platform", "/solutions", "/integrations", "/security", "/pricing", "/contact"].map(path => ({ url: `${origin}${path}` })) : [];
}
