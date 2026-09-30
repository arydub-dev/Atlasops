# Staging setup (RC2/RC3)

**Canonical runbook:** [`OPERATIONS_MANUAL.md`](./OPERATIONS_MANUAL.md)  
(step-by-step deploy, integrations, soak, load, DR, Go/No-Go)

Production-like staging for WorkOS, Stripe test mode, and connector sandboxes.

## Architecture

Same topology as production Compose:

- PostgreSQL 16 (non-superuser preferred)
- Redis 7
- API (`alembic upgrade head` then uvicorn)
- ARQ worker (`arq app.worker.WorkerSettings`)
- Frontend (HTTPS via reverse proxy)

## Quick start (Compose)

```bash
cp .env.staging.example .env.staging
# fill WorkOS, Stripe test, SESSION_SECRET, CREDENTIALS_ENCRYPTION_KEY, …
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up --build
```

Put TLS in front (Caddy/Nginx/Traefik). Set `SESSION_COOKIE_SECURE=true` (staging overlay).

## Fail-closed boot

`ENVIRONMENT=staging` and `ENVIRONMENT=production` both run
`assert_safe_to_boot()`. Staging/production refuse to start when:

| Check | Required |
| --- | --- |
| SESSION_SECRET | unique, ≥32 chars |
| CREDENTIALS_ENCRYPTION_KEY | set |
| SESSION_COOKIE_SECURE | true |
| WORKOS_API_KEY + WORKOS_CLIENT_ID | set |
| WORKOS_COOKIE_PASSWORD | non-default |
| REDIS_URL | set |
| SEED_ON_STARTUP / FEATURE_DEMO_SANDBOX | false |
| ALLOW_CREATE_ALL_ON_STARTUP | false |
| CONNECTOR_SYNC_INLINE | false |
| CORS `*` | forbidden |
| STRIPE_WEBHOOK_SECRET | required if Stripe key set |
| METRICS_TOKEN | required in **production** |

## Webhooks

Stripe test webhook → `https://<api>/api/v1/billing/webhooks/stripe`  
WorkOS redirect → `/api/v1/auth/callback`

## Connector sandboxes

| Vendor | Notes |
| --- | --- |
| Salesforce | `config.sandbox=true` → `test.salesforce.com`; instance hosts must be `*.salesforce.com` |
| Dynamics BC | Azure AD app + BC sandbox; `api.businesscentral.dynamics.com` |
| UPS | CIE `wwwcie.ups.com` / `onlinetools.ups.com` |

Arbitrary `base_url` / `token_url` values outside the allowlist are rejected (SSRF protection).

Sync is **queued** to Redis/ARQ — the worker must be running.

## Checklist

See [`STAGING_CHECKLIST.md`](./STAGING_CHECKLIST.md). Complete every item before design-partner traffic.

## Soak (7–14 days)

Run staging under realistic traffic. Track memory, queue depth, worker failures, webhook duplicates, and session errors. Record incidents in the RC2 soak log (`docs/reports/RC2_SOAK_LOG.md`).
