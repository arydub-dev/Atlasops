# Deploying Supply v2

Three-part system: **PostgreSQL**, **FastAPI**, **Next.js**, plus **Redis** for ARQ connector workers.

## Local development (straightforward)

```bash
cp .env.example .env
# Leave WorkOS/Stripe empty for local; NEXT_PUBLIC_DEV_LOGIN=true
docker compose up --build
# or: backend uvicorn + frontend npm run dev against local Postgres/Redis
```

- `ENVIRONMENT=development` allows default session secrets and `create_all` for empty DBs.
- Prefer `alembic upgrade head` so RLS policies exist when using Postgres.
- Dev login: `POST /api/v1/auth/dev-login` (disabled when WorkOS is configured or env ≠ development).

## Production defaults (secure)

Required:

| Variable | Notes |
| --- | --- |
| `ENVIRONMENT=production` | Enables fail-closed startup checks |
| `SESSION_SECRET` | ≥32 chars, unique |
| `CREDENTIALS_ENCRYPTION_KEY` | Required |
| `SESSION_COOKIE_SECURE=true` | HTTPS only cookies |
| `SEED_ON_STARTUP=false` | Never seed demo data |
| `FEATURE_DEMO_SANDBOX=false` | |
| `NEXT_PUBLIC_DEV_LOGIN=false` | |
| `ALLOW_CREATE_ALL_ON_STARTUP=false` | Schema via Alembic only |
| `WORKOS_*` | AuthKit / SSO |
| `STRIPE_*` | Billing |
| `CORS_ORIGINS` | Exact frontend origins (no `*`) |
| `FRONTEND_URL` | Used to allowlist billing return URLs |
| `REDIS_URL` | Workers (must include credentials in production) |
| `REDIS_PASSWORD` | Required when using the bundled Compose Redis service |
| `METRICS_TOKEN` | Gates `/metrics` |

Boot refuses insecure production settings (`app.core.startup_checks`).

Migration path:

```bash
alembic upgrade head
# reversible index migration: 0003_shipment_fk_indexes
# alembic downgrade -1
```

## Option A — Docker Compose

See root [`docker-compose.yml`](../docker-compose.yml): Postgres, Redis, API (`alembic upgrade head` then uvicorn), worker, frontend.

## Option B — Render Blueprint

[`render.yaml`](../render.yaml) provisions Postgres + Redis + API + **ARQ worker** + web. Set:

- `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`, WorkOS, Stripe, `CORS_ORIGINS`, `FRONTEND_URL`, `METRICS_TOKEN`
- `SEED_ON_STARTUP=false`, `CONNECTOR_SYNC_INLINE=false`
- `FEATURE_BILLING_ENFORCE=true` (default in blueprint)

Health check: `/health/ready` preferred over `/health`.

Staging overlay: [`docs/STAGING.md`](./STAGING.md) / `docker-compose.staging.yml`.

## Option C — Vercel services

[`vercel.json`](../vercel.json) can host frontend + API. Attach managed Postgres. Set the same production env vars. Redis/worker may need a separate host for connector sync.

## Disaster recovery

See [`docs/DISASTER_RECOVERY.md`](./DISASTER_RECOVERY.md).
