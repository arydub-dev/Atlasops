> Updated pilot audit and provider architecture: [PILOT_READINESS_2026-09-30.md](PILOT_READINESS_2026-09-30.md). The dated report below remains historical evidence.

# ATLASOPS launch hardening report

Assessment date: 2026-09-29 (America/Chicago). Scope: this local source snapshot. There is no Git checkout/release SHA attached to this directory.

**Release decision: NOT YET APPROVED FOR PAYING CUSTOMERS.** The repository has materially improved security, billing correctness, import safety and deployment controls. It has not been deployed or validated with live identity, payment or connector providers. Passing local tests is not evidence of a production launch.

## Implemented

- PostgreSQL tenant isolation: production refuses superuser/BYPASSRLS runtime roles; separate migration credentials and runtime role provisioning. Tests exercise FORCE RLS as a restricted role, including API-token and Stripe customer lookup paths.
- Billing: expired trials/unpaid subscriptions blocked from operations while billing recovery remains accessible. Paid feature gates and row-locked AI quotas. Checkout metadata cannot activate a paid plan; authoritative subscription retrieval verifies the customer. Subscription and invoice reconciliation use current provider state; old subscription events, manual invoices, delayed billing periods and repeated invoice credit resets cannot incorrectly grant access or replenish credits. Provider failures roll back event claims for retry.
- Identity: upgraded WorkOS integration to installed SDK signatures, preserved application-managed opaque sessions, added explicit S256 PKCE and SDK contract tests. Real AuthKit sign-in is still unverified.
- Imports: bounded CSV/XLSX processing; zip expansion/formula protection; strict numeric/mapping/header validation; per-row savepoints retain valid rows while rejecting invalid duplicates/references. Legacy XLS/XLSM is rejected.
- Background work: connector tenant transaction boundaries corrected, signed tenant jobs, enterprise job signatures and rollback recovery. Real Redis/ARQ queue test uses mocked Salesforce HTTP.
- AI: actual retrieved context supplied to the provider, no invented confidence score, request/context/output limits, no automatic retries, bounded timeout, fallback behavior, concurrent quota protection. No paid provider call was made.
- Lead intake: consent/honeypot/rate limits, encrypted storage, platform-admin-only retrieval/deletion, visible success/failure states; disabled by default until privacy/support details are finalized.
- Deployment: nonroot containers, private database/cache/API/frontend ports, Caddy HTTPS configuration, separate migrations, provider URL normalization and percent-encoded credential support. Secret environment files excluded from images. Restore helper refuses nonempty targets.
- Dependencies: upgraded vulnerable frontend/backend dependencies and compatible telemetry; repaired stale nested PostCSS lock entry. Dependency audits fail CI on findings. Added real Redis integration to CI.
- Commercial material: product/architecture overview, onboarding, support, pilot, sales, go-to-market, AI and deployment documentation. Pricing remains quote-based; no fabricated customer outcomes or compliance certifications.

## Validation evidence

See [release checks](reports/2026-09-29-release-checks.md) for commands, outcomes and limitations. Local browser checks cover public pages, unauthenticated route protection and inquiry UI states. They do not prove provider signup, payment, or customer onboarding. The staging workflow now fails when its URL is missing, and its smoke checks are described accurately.

Known harmless test warning: one assertion uses Starlette's deprecated HTTP 413 constant name.

## Required to complete launch

1. **Deployment inputs:** choose hosting and DNS domain; provide access through the appropriate secret manager. Separate staging/production PostgreSQL, Redis, encryption/session secrets and restricted runtime roles. The legacy Render blueprint is marked unapproved; the Compose configuration is the prepared deployment path.
2. **Live journeys:** configure WorkOS callback/domain, Stripe test prices/webhook, verified invitation sender, and a connector sandbox. Record signup → organization → invite → import → dashboard → checkout → upgrade/cancel → failed-payment recovery → logout, with cross-tenant checks. Then configure live billing only after test-mode validation.
3. **Operations:** build/run actual containers, verify HTTPS/cookies/proxy behavior, configure off-host backups and perform full application recovery, deliver test alerts to a staffed responder, measure expected customer load and complete the planned soak. Docker daemon was unavailable locally; image execution was not verified.
4. **Business readiness:** finalize legal entity/contact, privacy/terms and retention policy, support ownership, prices/contracts and pilot scope. Draft legal pages are not final policies. Keep intake disabled until the operating process is staffed.
5. **Pilot acceptance:** reconcile real source totals, measure agreed outcomes, resolve all critical/high defects and obtain the customer's acceptance of the supported scope. Connector and predictive capabilities must not be sold as universally validated.

No hosting purchase, public deployment, external customer contact, live charge or real customer data import occurred. No SOC 2 certification, SLA, throughput target, guaranteed AI accuracy or recovery objective is claimed.

## Suggested first commercial scope

A small, supervised supply-chain visibility pilot for a distributor or manufacturer: one organization, a few users, CSV/XLSX onboarding, shipments/inventory/supplier visibility, alerts and human-reviewed analysis. Enable a connector only after its sandbox and customer-data reconciliation pass. Expand to broader company rollout after operational and customer acceptance evidence exists.

The remaining configuration request is hosting/domain plus availability of WorkOS, Stripe, support/business details and a connector sandbox. Do not paste secrets into chat.
