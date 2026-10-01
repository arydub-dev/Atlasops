# Search and customer acquisition — 2026-10-01

Implemented: company-email signup checks in the email entry flow and new-user identity callback; enterprise enquiry validation and encrypted existing lead storage; free-trial/enterprise paths; Features page; page metadata, canonicals, sitemap, production robots, preview noindex, Organization/WebSite structured data, brand PNG favicon and logo.

The email policy denies common consumer/disposable providers and subdomains, case-insensitively. It is not proof that a domain is a company, and does not exhaust every disposable provider. Existing users can still sign in. Retain identity-provider email verification and organization domain verification; a domain name alone must never grant membership.

## Deployment gates

- Deploy and test the backend and frontend together. WorkOS must be configured and email verification enforced. Confirm new organizations receive the existing 14-day trial and billing limits.
- Set LEAD_CAPTURE_ENABLED=true only with migration 0016 applied and encryption configured. Verify a real enterprise enquiry is stored and visible through the platform-admin leads API; ensure an operator checks these requests. Email/Slack lead notifications are not implemented. Do not promise immediate notification.
- Set NEXT_PUBLIC_SITE_URL=https://www.atlasops.online. Vercel previews are noindex. The production fallback uses the observed canonical www hostname; if the domain changes, update this setting.
- Verify production /robots.txt, /sitemap.xml, /favicon.png, /features and /contact return valid public responses with no accidental noindex or deployment protection.
- Verify domain ownership in Google Search Console, submit /sitemap.xml and request home-page indexing. The account owner must complete DNS/site verification if not already configured.
- Google controls crawling, rankings, logo display and sitelinks. Structured data and clear navigation provide eligibility, not guarantees. No fabricated ratings, customers, certifications or offers were added.

Official references: https://developers.google.com/search/docs/appearance/favicon-in-search and https://developers.google.com/search/docs/appearance/sitelinks
