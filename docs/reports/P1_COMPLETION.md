# P1 Completion Report — Auth, isolation, rate limits, CI

## Files changed
- `backend/app/core/rate_limit.py` — `TRUST_PROXY` gate for X-Forwarded-For
- `backend/app/core/config.py` — `TRUST_PROXY`
- `backend/app/api/routers/auth.py` — rate limit on login/callback/dev-login
- `backend/app/api/routers/orgs.py` — invite accept HTTP; seat enforce; block owner escalation via PATCH
- `backend/app/api/routers/data.py` — connector limit enforce
- `backend/app/api/routers/ai.py` — AI credit enforce + usage increment
- `backend/app/api/deps.py` — `get_current_user_optional_org`
- `backend/app/identity/orgs.py` — timezone-safe invite expiry
- `backend/tests/conftest.py` — Postgres CI mode
- `.github/workflows/ci.yml` — frontend build; Postgres+Alembic+RLS job

## Migrations
- None

## Tests added
- `test_auth_guards.py` — 401s, org header spoof, logout, alert/connection isolation, invite accept, owner escalation, rate limit
- `test_api_tokens.py` — create/use/revoke/orphaned creator
- `test_rls.py` — Postgres-only RLS policy presence + GUC isolation

## Risks mitigated
- Auth rate-limit bypass via spoofed XFF (unless TRUST_PROXY)
- Privilege escalation to owner via member PATCH
- Missing invite-accept HTTP surface
- Plan limits never applied (now gated by FEATURE_BILLING_ENFORCE)
- CI never exercised Postgres RLS

## Remaining known issues
- Docs still partially v1 (P2)
- Performance N+1 / full scans (P2)
- Audit helper shared module (P2)
- Webhook idempotency still open
