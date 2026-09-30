> Current target architecture: see [HOSTED_DEPLOYMENT.md](HOSTED_DEPLOYMENT.md) for Vercel + Render + Upstash. The Compose instructions below remain a self-hosted alternative.

# Production deployment

Status: NOT DEPLOYED. See LAUNCH_REPORT.md for current evidence. Hosting provider, domain, WorkOS project and Stripe configuration are pending. Use a simple API + frontend + worker + PostgreSQL + Redis architecture.

## Credential separation

1. Create an isolated staging database and a separate production database. Use independent credentials and encryption keys.
2. Supply MIGRATION_DATABASE_URL only to the migration job. It must own migrations and narrow SECURITY DEFINER lookup functions. Never give that URL to API/worker.
3. From `backend/`, run `DATABASE_URL="$MIGRATION_DATABASE_URL" .venv/bin/alembic upgrade head`.
4. Set RUNTIME_DATABASE_ROLE and RUNTIME_DATABASE_PASSWORD in a secret manager. Run `backend/.venv/bin/python scripts/provision_runtime_role.py` from the repository root after migrations. The script grants DML, not schema ownership or RLS bypass. Existing passwords are left unchanged.
5. Set DATABASE_URL to that runtime role for API and worker. Confirm `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user` returns false/false.

## Compose

Requires a Compose version supporting `!reset`. The production overlay removes inherited public database/cache/API/frontend ports. The overlay includes Caddy on the private Compose network and exposes only proxy ports 80/443. Set PUBLIC_HOST to your DNS hostname and point DNS at the server. Caddy routes `/api/*` and `/health/*` to the API and other requests to the frontend. Domain/certificate issuance has NOT been verified.

Set POSTGRES_PASSWORD, REDIS_PASSWORD, DATABASE_URL, MIGRATION_DATABASE_URL, SESSION_SECRET, CREDENTIALS_ENCRYPTION_KEY, WORKOS_API_KEY, WORKOS_CLIENT_ID, WORKOS_COOKIE_PASSWORD, WORKOS_REDIRECT_URI, FRONTEND_URL, CORS_ORIGINS, METRICS_TOKEN and NEXT_PUBLIC_API_URL. Configure WorkOS callback to the actual HTTPS `/api/v1/auth/callback`. Prefer app/API on the same site for SameSite=Lax cookies.

`docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet`

`docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d`

Migrations complete before API/worker start. For first boot, provision the runtime role after the migration job and before starting the API/worker. See the role procedure above. Roll forward with an additive migration when possible; do not blindly downgrade a database containing customer data.

## Provider wiring

Stripe: set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET and configured STRIPE_PRICE_* IDs. The Compose overlay forwards Stripe price IDs, inquiry settings and AI limits; inspect rendered configuration before launch. Register `/api/v1/billing/webhooks/stripe`; verify duplicate delivery and failed-payment recovery in test mode before live mode.

Sentry: configure DSN for API and worker, generate controlled errors and confirm receipt. Redis: enable authentication, private networking and persistence. Database: enable encrypted off-host backups and execute DISASTER_RECOVERY.md. Configure verified sender identity and support staff before sending invitations commercially.

Set LEAD_CAPTURE_ENABLED only after publishing final privacy/operator details and staffing `/api/v1/admin/leads`. NEXT_PUBLIC_SITE_URL is the public canonical domain; all NEXT_PUBLIC variables are public build inputs.

## Release gate

Run CI, restricted-role Postgres tests, browser onboarding, actual WorkOS/Stripe/connector tests, load/soak, alert delivery and restore verification. Collect timestamped evidence with release identifier, environment and result. A healthy container alone is insufficient. See GO_LIVE_CHECKLIST.md.
