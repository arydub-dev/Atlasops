# ATLASOPS Security Runbook

## Incident triage (first 30 minutes)

1. Preserve logs (API, audit_logs, Stripe events, worker logs) with request/correlation IDs.
2. If session compromise suspected: revoke org sessions via Security Center / admin APIs; force IdP re-auth.
3. If tenant isolation suspected: freeze affected orgs if tooling exists; capture DB evidence **as superuser** (app role cannot dump under FORCE RLS).
4. If Redis exposure suspected: rotate `CREDENTIALS_ENCRYPTION_KEY` / session secrets only with a planned rollout; rotate Redis AUTH; drain forged jobs.
5. If Stripe webhook abuse: rotate webhook secret; verify `stripe_events` idempotency table.

## Production boot gates (fail-closed)

Hardened environments (`staging` / `production` / unknown names) refuse to start when:

- Default `SESSION_SECRET` or missing `CREDENTIALS_ENCRYPTION_KEY`
- `SESSION_COOKIE_SECURE=false` (API)
- WorkOS not configured (API)
- CSRF Origin check disabled
- Unauthenticated Redis URL (always in production; remote hosts in staging)
- `CONNECTOR_SYNC_INLINE=true`
- `SEED_ON_STARTUP` / demo sandbox flags unsafe for prod
- CORS `*` with credentials

## RLS / tenant isolation checklist

```sql
-- App role must never bypass RLS
SELECT rolbypassrls FROM pg_roles WHERE rolname = '<app-role>';
-- expect: f

-- Tenant tables should have FORCE RLS
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class WHERE relname IN (...);
```

After deploy: run Postgres suite with `SUPPLY_CI_POSTGRES=1`.

## Rotation procedures

| Secret | Notes |
| --- | --- |
| `SESSION_SECRET` | Invalidates sessions; coordinate with users |
| `WORKOS_COOKIE_PASSWORD` | WorkOS sealed cookie; follow WorkOS guidance |
| `CREDENTIALS_ENCRYPTION_KEY` | Re-encrypt connector secrets before discarding old key |
| `STRIPE_WEBHOOK_SECRET` | Update Stripe dashboard + env atomically |
| Redis password | Update `REDIS_URL` on API + workers together |

## Suspicious authz failures

Investigate repeated 403s on org header spoofing, cross-tenant UUID probes, connector SSRF rejections, and forged Stripe signatures. These should appear in structured logs without secrets.

## External testing

Schedule periodic external penetration tests focused on:

- Multi-tenant IDOR across all resource classes
- SSRF / connector sync
- Session fixation / CSRF
- Webhook and worker trust boundaries
