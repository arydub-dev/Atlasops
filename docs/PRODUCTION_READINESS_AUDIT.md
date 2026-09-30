# Production readiness audit

Date: 2026-09-22. Decision: **NOT READY**. This evidence supersedes the unsupported certification in LAUNCH_READINESS.md. Source snapshot has no `.git` directory. No live customer deployment has been inspected.

## Architecture

Next.js 15 / React 19 frontend; FastAPI / SQLAlchemy backend; PostgreSQL with tenant RLS; Redis / ARQ workers; WorkOS sessions; Stripe subscriptions; optional OpenAI, Sentry, PostHog, email and object storage. CSV/XLSX ingestion writes domain entities. Compose and Render deployment definitions exist. SQLite tests do not prove PostgreSQL isolation. Runtime database credentials must not be superuser or BYPASSRLS. External service configuration and hosted environment are not supplied.

## Baseline evidence

- Backend: 205 passed, 18 skipped, 5.85s on local SQLite.
- Frontend: lint and typecheck passed; production build FAILED because Google Fonts could not resolve in this environment.
- Docker daemon unavailable; local PostgreSQL did not respond. Live auth, billing, connector, worker, backup recovery and hosted smoke tests NOT TESTED.
- Existing release documents disagree. A passing build does not certify a deployment.

## Findings before changes

| Priority | Finding | Root cause / consequence |
|---|---|---|
| P0 | Compose uses bootstrap database account for API/worker | Official Postgres bootstrap account is superuser; RLS can be bypassed. Separate runtime role and enforce at boot. |
| P1 | PostgreSQL API token fallback references undefined `text` | Exception swallowed; legitimate token authentication fails under RLS. |
| P1 | Import parsing accepts fractional integer truncation and nonfinite floats | Bad inventory/cost data; malformed mapping can cause 500; duplicate commit can roll back unrelated valid rows and disclose SQL errors. |
| P1 | Excel compressed expansion and row count unbounded | Small upload can exhaust parser memory. Legacy XLS is incorrectly parsed as CSV. |
| P1 | HTTPS checks only inspect localhost substrings | HTTP external origins and SQLite accepted by secure boot. |
| P1 | CI Postgres runs as bootstrap superuser | Isolation tests do not represent least-privilege runtime. |
| P1 | Dependency audits nonblocking | Known vulnerable dependencies do not stop release. |
| P1 | No live launch evidence | WorkOS, Stripe, connector, monitoring, load/soak and recovery require real infrastructure. |
| P2 | Build fetches fonts at compilation | Build requires Google availability. |
| P2 | Marketing, support and commercial evidence incomplete | No verified pricing approval, support identity, pilot or legal entity supplied. |

## Scorecard

PASS means the stated check was executed successfully, not merely implemented.

| Area | Baseline | Evidence / next gate |
|---|---|---|
| Authentication | PARTIAL | Local session tests pass; WorkOS HTTPS NOT TESTED |
| Authorization | PARTIAL | Local RBAC tests pass; full production roles NOT TESTED |
| Tenant isolation | PARTIAL | SQLite tests pass; 18 external tests skipped |
| Database | PARTIAL | Models/migrations exist; fresh Postgres migration required |
| API security | PARTIAL | Attack matrix passes locally; token fallback defect |
| Frontend security | PARTIAL | Headers present; deployed browser NOT TESTED |
| Secrets management | PARTIAL | Secure boot exists; provider secrets not provisioned |
| Encryption | PARTIAL | Credential tests pass; production key management NOT TESTED |
| File uploads | FAIL | Unbounded Excel expansion |
| Data validation | FAIL | Nonfinite/fractional values accepted |
| Background workers | NOT TESTED | No live Redis worker in baseline |
| Job retries | PARTIAL | Code/tests exist; worker interruption NOT TESTED |
| Idempotency | PARTIAL | Webhook tests pass; live retries NOT TESTED |
| Billing | PARTIAL | Local billing tests pass; checkout NOT TESTED |
| Subscription handling | PARTIAL | Lifecycle implementation exists; expiry and recovery require review |
| Webhooks | PARTIAL | Signature/idempotency tests; real delivery NOT TESTED |
| Logging | PARTIAL | Structured logging present; deployment NOT TESTED |
| Monitoring | NOT TESTED | No deployed telemetry evidence |
| Alerting | NOT TESTED | No delivered alert evidence |
| Error handling | PARTIAL | Import error disclosure identified |
| Backups | NOT TESTED | Historical local claim; current environment unverified |
| Disaster recovery | NOT TESTED | Current restore drill required |
| CI/CD | FAIL | Superuser test role; dependency scans optional |
| Infrastructure | NOT TESTED | Docker daemon unavailable; hosting unresolved |
| Performance | NOT TESTED | No current measured workload |
| Load testing | NOT TESTED | Harness exists; no current results |
| Security testing | PARTIAL | Local suite passed; external isolation skipped |
| Accessibility | NOT TESTED | Lint passed; browser/assistive review pending |
| UX | PARTIAL | Pages exist; commercial browser journey pending |
| Documentation | FAIL | Contradictory launch certification |
| Customer onboarding | NOT TESTED | Real signup/import journey pending |
| Support readiness | PARTIAL | Runbooks exist; staffed channel not configured |

Change evidence and unresolved gates are recorded in LAUNCH_REPORT.md. Do not promote this release based on this baseline alone.
