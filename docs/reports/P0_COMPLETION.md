# P0 Completion Report — Critical hardening

## Files changed
- `backend/app/api/routers/billing.py` — authn + `org.billing.manage` + path/org match; preferred `/billing/*` without path id
- `backend/app/billing/stripe_service.py` — `validate_frontend_url` (open-redirect protection)
- `backend/app/connectors/credentials.py` — JSON dict credentials + legacy string compat
- `backend/app/api/routers/data.py` — `credentials` dict + legacy `api_key`; encrypt via SDK helper
- `backend/app/core/startup_checks.py` — production fail-closed validation
- `backend/app/core/config.py` — `ALLOW_CREATE_ALL_ON_STARTUP`, `METRICS_TOKEN`, docs flag
- `backend/app/main.py` — lifespan checks; no create_all in prod; docs/metrics gated
- `backend/app/api/deps.py` — Postgres RLS GUC failure → 503; API token no identity fallback
- `docker-compose.yml` — `alembic upgrade head` required (no silent init-db fallback)

## Migrations
- None (no schema change in P0)

## Tests added
- `backend/tests/test_billing_authz.py` — unauth 401, viewer 403, cross-org 403, spoof header, owner OK, URL allowlist
- `backend/tests/test_connector_credentials.py` — round-trip, legacy blob, merge, configure API, cross-org 404
- `backend/tests/test_startup_checks.py` — prod rejects weak secrets; dev still boots

## Risks mitigated
- Unauthenticated billing money APIs (Critical)
- Credential encrypt/decrypt mismatch breaking connectors (Critical)
- Prod boot with default secrets / create_all without RLS
- API token impersonation via orphaned-token fallback
- Open redirect via Stripe return URLs

## Remaining known issues (deferred to P1/P2)
- Rate limiter still unwired
- Plan `enforce_*` still unwired
- Isolation tests still shipment-centric
- No Postgres RLS CI job yet
- Docs (API/DEPLOYMENT/etc.) not yet fully rewritten
