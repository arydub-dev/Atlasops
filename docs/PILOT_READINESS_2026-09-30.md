# Supervised pilot readiness audit — 2026-09-30

Decision: BLOCKED pending external launch gates. This report supersedes earlier readiness claims, but retains dated evidence without presenting it as newly verified.

## Audit-first checklist

Reviewed current repository structure, API/dependency/migration configuration, AI context and permission gates, request telemetry/readiness, Vercel and Compose configurations, prior auth/tenant/billing/import/job regressions, CI and operational documentation. Full endpoint-by-endpoint manual security review and external integration testing are NOT VERIFIED.

Prioritize P0/P1; retain deterministic risk and simulation logic and the current stack.

| Finding | Severity | Location | Impact | Planned fix / verification |
| --- | --- | --- | --- | --- |
| Copilot graph/timeline allows network.read although corresponding APIs require mission.read | P1 | services/ai_orchestration.py | Role can obtain otherwise forbidden operational context | Match API gate; negative permission regression |
| Empty AI completions accepted as success | P1 | services/ai_providers.py | Blank persisted recommendations and consumed credits | Reject malformed/empty output; exercise deterministic fallback |
| Unhandled failures bypass request counters; arbitrary request IDs reflected | P1 | core/telemetry.py | Missing error-rate evidence and unbounded correlation values | Count exception as 500; bounded safe request IDs; middleware regression |
| Hosting instructions do not match frontend-only Vercel intent | P1 | vercel.json / deployment docs | Wrong deployment topology; no persistent ARQ worker | Document frontend root, API subdomain and persistent backend/worker; hosted verification pending |
| Hosted auth/billing/connector/alerts/backup/load unavailable | P1 | External environments | Customer pilot acceptance unsupported | BLOCKED pending accounts/configuration and actual verification |

This checklist is updated with actual outcomes below. No production load test or live payment is authorized by implication.

Audit correction: zero-capacity warehouse concern was dismissed after confirming the existing database `capacity > 0` constraint. No schema validation was weakened.

## Additional security findings and resolutions

| Finding | Severity | Location | Impact | Fix | Verification |
| --- | --- | --- | --- | --- | --- |
| Legacy migration unconditionally drops tables | P0 | alembic/versions/0002_supply_v2_multitenant.py | Existing data loss on upgrade | Refuse any populated or RLS-protected schema before first DROP; no bypass flag | SQLite guard regression, clean PostgreSQL upgrade, populated legacy PostgreSQL refusal |
| Provider error bodies echoed | P1 | connectors/dynamics_bc.py, connectors/ups.py | Provider/customer secrets could reach errors/logs | Status-only error messages, no raw body | Mocked secret-bearing provider response tests |
| Final connector URLs not consistently validated | P1 | Dynamics _request, UPS _track | Unsafe outbound request/token disclosure if a malicious URL reaches execution | Validate final URL; encode tracking path segment | Private/metadata URL rejection before HTTP |
| Dynamics sync ignores additional collection pages | P1 | connectors/dynamics_bc.py | Silent truncation and cursor advancement | Follow bounded pages; reject cycles/malformed collections/limit overflow | Two-page and cycle regressions; real sandbox NOT VERIFIED |
| UPS sync loads an unbounded shipment list | P1 | connectors/ups.py | Resource exhaustion and worker timeout | Apply tracking filter in SQL; cap 1000, fail with narrowing guidance | Full regression suite; hosted throughput NOT VERIFIED |
| Document upload can acknowledge lost bytes | P1 | services/documents.py, api/routers/enterprise.py | Customer believes unpersisted file was saved | Fail 503 when storage fails in hardened env or configured storage fails | No metadata/commit on failed storage regression |
| Monitoring can capture request credentials/local values | P1 | integrations/sentry_setup.py | Sensitive data sent to monitoring | Strip bodies, headers, cookies, query, user, extras, breadcrumbs, raw exception/log values and local variables | Synthetic secret scrub regression; hosted Sentry receipt NOT VERIFIED |
| Worker inherits API HTTP healthcheck | P1 | docker-compose.prod.yml | Healthy worker reported unhealthy | ARQ --check worker healthcheck | CLI option verified; container execution NOT VERIFIED |
| New high-severity brace-expansion advisory | P1 | frontend/package-lock.json | Dependency denial-of-service exposure | Compatible transitive updates, no audit suppression | Fresh npm audit/build/lint/type/browser checks |

The initial Copilot permission, empty output and telemetry findings above are fixed with regression tests. Residual risk: automated tests cover selected boundaries, not a complete independent security assessment.

## Target and access

Vercel frontend (atlasops.online), Render API/PostgreSQL/worker, Upstash Redis, WorkOS, Stripe test mode, Salesforce Developer Edition and Sentry email/Slack are user-selected. Render sign-in/verification succeeded. The new-service screen has no connected Git provider. Repository URL and publishing destination for the local source snapshot are still missing. No cloud resources were created, purchased, or modified; no customer messages or alerts were sent.

## Readiness matrix

PASS is scoped to the stated local evidence; it is not approval for customer production use.

| Area | Status | Evidence | Remaining work |
| --- | --- | --- | --- |
| Security | NOT VERIFIED | New P0/P1 fixes; regression/dependency/source scans | Complete manual endpoint review, image/system scans and hosted protections |
| Authentication | NOT VERIFIED | Local session/role/API token tests; SDK contracts | Actual WorkOS sign-in/invite/logout and disabled-user scenarios |
| Tenant isolation | PASS | Restricted-role PostgreSQL automated tests | Repeat with deployed roles and customer journey |
| Database | PASS | Fresh migration, existing 0015 upgrade, legacy preservation guard, local app restore | Managed backups, migration runner and production credentials |
| Background jobs | PASS | Local real Redis connector test and retry/result probe | Upstash TLS/limits, reconnect/crash and Render heartbeat validation |
| AI | NOT VERIFIED | Context permission/fallback/output/timeout/quota tests | Live provider failure cases, cost controls, adversarial output evaluation |
| Stripe | NOT VERIFIED | Mocked provider billing regression tests | Actual test checkout/webhook/portal/cancel/recovery |
| WorkOS | NOT VERIFIED | SDK contract and local auth tests | Hosted configuration and organization mapping |
| Connectors | NOT VERIFIED | Salesforce mocked HTTP + real ARQ; Dynamics/UPS security tests | Salesforce Developer Edition end-to-end reconciliation; later BC/UPS sandboxes |
| Monitoring | NOT VERIFIED | Failure counters/request IDs/scrub tests; alert configuration | Actual Sentry/metrics collection and delivered notification |
| Backups | NOT VERIFIED | Local dump/restore with app readiness/dashboard and row checks | Managed backup schedule, encryption/retention, off-host application recovery |
| Performance | NOT VERIFIED | Bounded local synthetic baseline | Staging concurrent load/soak, browser dashboard, connector/AI timing |
| Deployment | BLOCKED | Provider-specific files/docs prepared; Render signed in | Git provider/repository, resource provisioning, secrets and DNS |
| Documentation | PASS | Deployment, findings, operations, connector and evidence documents | Final customer-specific contacts, terms, retention and signed pilot scope |

## Launch blockers

1. Connect the deployment repository and publish the hardened source to an identifiable release commit; run remote CI including container builds/scans.
2. Provision independent staging resources, restricted database role and dedicated migration runner; configure provider secrets through platform mechanisms.
3. Verify WorkOS, Stripe test mode, Salesforce sandbox and Upstash/ARQ end-to-end with the deployed application.
4. Verify Sentry notifications, authenticated metrics, worker monitoring and managed backup restoration.
5. Complete representative staging load/soak and full desktop/mobile authenticated customer journeys.
6. Finalize pricing, support contact/ownership, legal/privacy/pilot agreement and actual retention/purge behavior. Object attachments need verified storage/scanning or explicit exclusion from the pilot scope.

See HOSTED_DEPLOYMENT.md for release/rollback, PILOT_OPERATIONS_RUNBOOK.md for first-customer operation, CONNECTOR_VALIDATION.md for sandbox evidence, and reports/2026-09-30-pilot-validation.md for measured results. No paying customer should be admitted on local tests alone.

Final local totals: PostgreSQL 292 passed/1 Redis skip; SQLite 274 passed/19 platform skips; browser 10 passed/6 hosted skips. AI fallback counters and an alert rule were added and regression-tested; notification delivery remains NOT VERIFIED. Canonical public frontend observed at https://www.atlasops.online/ (apex redirects).
