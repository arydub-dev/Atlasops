import type { MetadataRoute } from "next";
import { SITE_URL, IS_PREVIEW } from "@/lib/site";
export default function sitemap(): MetadataRoute.Sitemap {
 return IS_PREVIEW ? [] : ["", "/features", "/platform", "/solutions", "/integrations", "/security", "/pricing", "/contact", "/get-started", "/about"].map(path => ({url: `${SITE_URL}${path}`}));
}
