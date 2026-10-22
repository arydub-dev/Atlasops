# Authenticated application restoration — 2026-10-18

## Baseline and preservation

Selected baseline: codex/yc-recovery-preview at 364187b8d0d2a7d8c0de1e248a80a5be8e2df338, following Recovery Engine implementation 3095148. This is the fuller locally verified implementation, not a claim of hosted readiness.

The public release a76173c43a620d599601bf1cddab1a3231e86931 was based on main 40e0696. Its diff adds a separate /demo route and skips auth providers only for that public route. It did not delete the authenticated application. It also does not include the newer backend Recovery Engine. Replacing /demo cannot by itself restore hosted functionality.

Retain the existing authenticated application routes, WorkOS flow, restricted /demo-login server credential verification, opaque sessions, organization membership checks, demo_operator permissions, PostgreSQL RLS, and backend Recovery Engine. The restricted reviewer endpoint is not a WorkOS password form; it is an existing server-side hashed-password mechanism with membership checks and normal sessions. WorkOS remains the email-first organization login architecture. No alternative auth system or bypass is introduced.

## Reviewed UI changes

- Persistent viewport-height navigation with Data Sources in the core navigation; existing role filtering preserved.
- Compact linked operational counts; absent counts remain Unknown.
- Work-order/SKU search, readiness status filter and stable sorting on the existing backend response.
- Accessible navigation labels and expansion state.
- Optional walkthrough collapsed initially.
- Data mode no longer implies a verified external connection; connector evidence must be checked separately.

Existing readiness evidence, donor impact, proposal/approval, audited corrections, incident and outcome flows remain intact. No new calculator, fake metrics or client-only workspace introduced.

## Current hosting evidence and blocker

Read-only Vercel CLI inspection on 2026-10-18 confirmed project acmea9/atlasops and branch-specific Preview settings for WorkOS, restricted reviewer access, isolated DATABASE_URL and secure staging flags. Variable names only were inspected; presence does not verify values or execution. REDIS_URL is absent. Upstash and Render showed sign-in pages. The user explicitly confirmed no Redis or worker is available.

Required next resources: an authenticated native TLS Redis endpoint (rediss://, not an HTTPS REST endpoint) configured as Preview REDIS_URL for codex/yc-recovery-preview, plus a persistent authorized host running the existing backend ARQ worker against the same isolated database/Redis. Secrets must be injected through provider secret management. No paid resources have been authorized or purchased.

API secure boot requires Redis configuration; login rate limiting fails closed when Redis is unavailable. Readiness also validates the ARQ heartbeat. Direct synchronous recovery calculations do not themselves require a worker, but this does not make the existing hosted application gate optional. WorkOS settings exist but lifecycle verification remains outstanding. Do not weaken those checks or use development mode for hosted access.

Before deployment: verify actual branch-specific variable values privately, isolated database runtime role, migration revision, frontend origin and callback alignment. Revalidate synthetic dates through audited corrections. Do not recreate the existing fixture or release pending credentials. Deploy Preview only; preserve current public domain until hosted acceptance supports replacement.

## Release status

HOST-001 BLOCKED: no Redis/worker and no fresh hosted full-workflow verification.
SSO-001 BLOCKED: hosted WorkOS lifecycle and reviewer login unverified.
AI-LIVE-001 BLOCKED: external provider execution/safety evidence absent.
VISUAL-REVIEW-001 BLOCKED: human desktop/mobile approval of hosted revision absent.

Not a finished enterprise redesign or hosted release. No credentials delivered, no customer data changed, no production deployment performed as part of this restoration checkpoint.

## Verification history

Focused backend run: 56 passed, 2 skipped (PostgreSQL-only cases). Frontend TypeScript, lint and build passed initially against the shared installed Next.js 15.5.26; this was subsequently identified as different from locked Next.js 15.5.27. An isolated npm ci installation of the exact lockfile is used for final validation. No dependency version was changed in source.

Intermediate full run 20261018T065453Z-a60f1c: 902 entries, 861 passed, 11 failed, 4 blocked, 26 skipped. Ten failures were old dashboard heading selectors; one correctly detected source editing during verification. Retained without alteration.

Intermediate full run 20261018T122626Z-29afb9: 901 entries, 870 passed, 1 failed, 4 blocked, 26 skipped. The new readiness filter test used an exact label-text lookup that did not resolve the select. The recorded accessibility snapshot exposes a combobox named Readiness status; the test now uses that role/name, preserving filter assertions and all downstream workflow assertions. Retained without alteration.

Vercel production settings inspected read-only confirm main is the production branch. This checkpoint remains on codex/yc-recovery-preview. No --prod deployment is authorized by this checkpoint.

## Additional unfinished review

The existing Data Sources page still uses legacy labels such as Available Integrations and Connected Mode; these need a separate evidence-based review before presenting the entire restored application as enterprise-ready. This checkpoint does not certify those labels or actual live integrations. The broader information-density redesign, mobile navigation accessibility audit and exact hosted screenshot/human acceptance remain unfinished. Existing fixed-date staging records have not been refreshed in this task; that must use audited corrections against the verified staging target before reviewer access.

Intermediate exact-lockfile full run 20261018T123824Z-95cb6e: 901 entries, 870 passed, 1 failed, 4 blocked, 26 skipped. Recovery completed calculation, approval and outcome but its rapid refresh hit HTTP 429 (120 requests/minute). The screenshot showed that error alongside an incorrect empty-history state. The recovery page now distinguishes failed initial loading from an empty result and offers an explicit retry. Recovery browser traffic is paced at 850ms per request, matching the existing browser suite approach; its timeout accommodates pacing. API limits, assertions and release gates remain unchanged. This run is retained as a genuine failure, not reclassified as a pass.

Attempt 20261019T000939Z-30ac29 did not produce a complete report: local disk exhaustion prevented PostgreSQL initialization, interrupted browser execution and prevented writing source-after.json. It is not a completed QA run. Generated Next.js caches from completed runs were removed; reports, screenshots, logs, source and databases were retained. No release gate was changed to accommodate the environment failure.

## October 19 continuation

Run 20261019T001134Z-804c79 finished with 901 entries: 862 passed, 9 failed, 4 blocked, 26 skipped. The local Next.js development server aborted in Node 25/V8 ("Lazy deopt after a fast API call with return value is unsupported"); subsequent browser failures were connection refusals. The apparent system node@24 symlink also resolved to Node 25; its rerun 20261019T001723Z-3bc53a was interrupted, not completed.

An isolated Node 24.22.0 runtime was installed without changing system Node. TypeScript, lint and build passed with Node 24 and locked Next.js 15.5.27. Run 20261019T001857Z-2d6df0 retained 410 passed / 26 skipped in SQLite, 436 PostgreSQL passes and 13 browser passes, including Recovery Engine filters, donor shortage, approval, correction, outcome, incident resolution and refresh. The process ended during API reconciliation before final report generation; these component results are NOT a complete release pass. Desktop/mobile screenshots exist under that run directory. Human approval remains absent.

All original acceptance blockers remain. No reviewer credentials released and no production domain changed. Remaining work includes the wider design-system/connector-label review, staging Redis/worker provisioning, hosted reviewer acceptance, external AI validation and human visual review.
