# ATLASOPS Release Checklist — RC3 Validation

Mark only with **PASS**, **FAIL**, or **NOT TESTED**. Evidence in [`RC3_RELEASE_REPORT.md`](./RC3_RELEASE_REPORT.md).  
**Validated:** 2026-08-12 UTC

## Infrastructure

- [ ] **NOT TESTED** — Production PostgreSQL migration on hosted staging (`docker-compose.prod.yml`)
- [x] **PASS** — Empty local Postgres 16 → `alembic upgrade head` → `0011_alert_sim_enums`
- [x] **PASS** — RLS + FORCE RLS (36 tables, 36 policies) + `tests/test_rls.py` (2 passed)
- [ ] **NOT TESTED** — Redis reachable; `/health/ready` ready (queued mode)
- [ ] **NOT TESTED** — ARQ worker consuming jobs
- [ ] **NOT TESTED** — `CONNECTOR_SYNC_INLINE=false` on running production boot
- [ ] **NOT TESTED** — Frontend with `NEXT_PUBLIC_DEV_LOGIN=false` on staging

## Auth & sessions

- [ ] **NOT TESTED** — WorkOS login E2E
- [ ] **NOT TESTED** — Secure session cookies on HTTPS
- [ ] **NOT TESTED** — Logout + revocation on staging
- [ ] **NOT TESTED** — Dev-login 404 in production boot
- [x] **PASS** — CSRF Origin check (automated `tests/test_csrf.py`)

## Multi-tenancy

- [x] **PASS** — Tenant isolation tests (SQLite API)
- [x] **PASS** — Spoofed `X-Organization-Id` rejected (SQLite)
- [x] **PASS** — Postgres RLS policy / FORCE / unscoped block tests
- [x] **PASS** — Postgres API org-scoped list under FORCE RLS (fixed: GUC rebind after auth commit)

## Billing

- [ ] **NOT TESTED** — Stripe Checkout (test mode)
- [ ] **NOT TESTED** — Stripe webhook signature (live)
- [x] **PASS** — Webhook idempotency + FORCE RLS customer lookup (`stripe_customer_index` / 0013)
- [x] **PASS** — `invoice.paid` under FORCE RLS with app role (no BYPASSRLS)
- [ ] **NOT TESTED** — `FEATURE_BILLING_ENFORCE=true` live entitlement enforcement

## Data plane

- [ ] **NOT TESTED** — Connector sandbox connect → ARQ sync → records
- [ ] **NOT TESTED** — CSV/Excel production import on staging
- [x] **PASS** — Credential encryption unit tests

## Product workflow

- [ ] **NOT TESTED** — Mission Control on staging data
- [ ] **NOT TESTED** — Disruption → Copilot → simulation on staging
- [ ] **NOT TESTED** — Frontend error/retry on staging (code present; not proven live)

## Ops

- [ ] **NOT TESTED** — `/health/live` + `/health/ready` on staging stack
- [ ] **NOT TESTED** — Sentry receiving API + worker errors
- [x] **PASS** — Backup → restore (superuser `pg_dump`; app-role dump fails under FORCE RLS)
- [ ] **NOT TESTED** — Load/soak 100/1k/10k
- [x] **PASS** — No secrets committed in this validation (no `.env` present)

## Decision

| Gate stage | Classification |
| --- | --- |
| Local demo | **LOCAL DEMO READY** |
| Private design partner | **NOT READY** |
| Paid pilot | **NOT READY** |
| General production SaaS | **NOT READY** |

**RC3 PASS RATE:** 5/12 = **42%** (Gates 2, 4, 9, 11, 12 PASS; Gates 1,3,5,6,7,8,10 NOT TESTED)

Sign-off: RC3 automated validation — 2026-08-12
