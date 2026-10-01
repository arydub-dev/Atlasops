export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.atlasops.online").replace(/\/$/, "");
export const IS_PREVIEW = process.env.VERCEL_ENV === "preview" || process.env.VERCEL_ENV === "development";
export const SITE_DESCRIPTION = "AI-assisted supply chain intelligence for shipment visibility, inventory planning, supplier risk, and better operational decisions. Explore ATLASOPS or connect with our enterprise team.";
