# Supply v2.0.5 — Operations manual for human staging

## Ops
- Complete `docs/OPERATIONS_MANUAL.md` (deploy, integrations, design-partner onboarding, soak, DR, Go/No-Go)
- k6 load scripts under `load/k6/`
- README / STAGING / OPERATIONS link to the manual as canonical runbook

## Prior
See v2.0.4 (RC3 ops hardening).

---

# Supply v2.0.4 — RC3 production operations hardening

## Ops / security
- `/health/ready` verifies Redis when queue-backed sync is required
- Staging + production require `METRICS_TOKEN`; `/metrics` gated on hardened envs
- Production boot requires `FEATURE_BILLING_ENFORCE=true`
- Render API runs Alembic before uvicorn; `TRUST_PROXY=true`
- Worker fail-closed boot (`role=worker`); Docker HEALTHCHECK uses `/health/ready`
- Connector + Stripe Prometheus counters; monitoring/incident/env-matrix docs
- Restore drill + soak snapshot scripts (execution still an operator gate)

## Prior
See v2.0.3 (RC2), v2.0.2 (RC1).

---

# Supply v2.0.3 — RC2 commercial pilot readiness

## Security / connectors
- SSRF allowlist for Salesforce / Dynamics BC / UPS outbound URLs
- Connector sync enqueued to ARQ (no inline HTTP in staging/production)
- Staging + production fail-closed boot (WorkOS, Redis, no inline sync, no create_all)
- Render blueprint includes Redis + worker; `FEATURE_BILLING_ENFORCE=true` by default on Render

## Ops / QA
- `docker-compose.staging.yml` + `.env.staging.example` + `docs/STAGING.md` / `OPERATIONS.md`
- Benchmark harness `scripts/benchmark_api.py`
- Secret-gated staging Playwright workflow
- Soak log template `docs/reports/RC2_SOAK_LOG.md`

## Prior
See v2.0.2 (RC1) and v2.0.1 (P0–P2).

---

# Supply v2.0.2 — RC1 production validation

## Security / billing
- Stripe webhooks set tenant RLS context; customer-id lookup uses controlled RLS bypass
- `stripe_events` idempotency (claim-before-process); migration `0004`
- API tokens bound to `token.organization_id` (header cannot switch orgs)
- Logout cookie clear matches Secure/HttpOnly flags
- CSV import commit writes audit log

## Docs / CI
- README, ARCHITECTURE, DATABASE, INTEGRATIONS aligned to Supply v2
- Staging checklist + RC1 release readiness report
- Playwright smoke job; API workflow E2E tests in pytest

## Prior (v2.0.1)
P0–P2 hardening — see previous entry.

---

# Supply v2.0.1 — P0–P2 hardening

## Security
- Billing routes require authentication + `org.billing.manage` + org path match
- Stripe return URLs restricted to `FRONTEND_URL`
- Connector credentials stored as encrypted JSON dicts (legacy string blobs still decrypt)
- Production boot rejects insecure secrets / seed flags
- Auth rate limiting; `TRUST_PROXY` for X-Forwarded-For
- API tokens reject orphaned creators (no membership fallback)
- Postgres RLS GUC failure hard-fails; Alembic required in production

## Performance
- Metrics functions are organization-scoped and use SQL aggregates
- Supplier ranking uses one grouped shipment aggregate (not 4×N queries)
- Reversible migration `0003_shipment_fk_indexes` for shipment FK filters
- Shipment detail eager-loads events

## Ops / docs
- CI Postgres + Alembic + RLS; frontend `next build`
- `/metrics` token-gated in production; OpenAPI off by default in production
- Audit helper with integrity hash chaining
- API.md, DEPLOYMENT.md, SECURITY.md, render.yaml rewritten for sessions/WorkOS/Stripe
