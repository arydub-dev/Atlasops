# ATLASOPS Production Audit

**Date:** 2026-08-10  
**Scope:** Full repository (frontend, backend, deploy, ops)  
**Goal:** Take the local demo to a deployable multi-tenant B2B SaaS without rebuilding.

---

## 1. Current architecture

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15.5 (App Router), React 19, TypeScript, Tailwind, Recharts, Mapbox optional |
| Backend | FastAPI 0.115, Python 3.12, SQLAlchemy 2.0, Pydantic v2 |
| Database | PostgreSQL 16 (production); SQLite used by local `start.sh` |
| Migrations | Alembic (`0002`–`0009`; legacy `77ea…`) |
| Auth | WorkOS AuthKit (email-first SSO) + opaque httpOnly `supply_session` cookies |
| Authz | RBAC permission strings + `require_permission`; Postgres FORCE RLS |
| Queue | Redis + ARQ worker (`sync_connection`, schedules, workflows, predictions) |
| Billing | Stripe Checkout / Portal / signed webhooks (`stripe_events` idempotency) |
| AI | OpenAI optional + deterministic local engine |
| Connectors | Dynamics BC, Salesforce, UPS (+ CSV/Excel import) |
| Deploy | Docker Compose, Render blueprint, experimental Vercel split |

**Product loop (intended):** Data → Operational Graph → Detection → Impact → Recommendation → Simulation → Operator Decision.

---

## 2. Existing working functionality

Verified against live local stack (seeded Demo Manufacturing Co):

- Dashboard KPIs / trends
- Shipments (80), inventory (120), warehouses (6), suppliers (12)
- Alerts (15 open) + stats
- Risk summary
- Network map nodes
- Analytics (delivery / suppliers / inventory / forecast)
- AI Copilot (local-engine), executive brief
- Timeline + graph stats
- Billing plan listing
- Org members / usage / security-center overview
- Connector Studio catalogue
- Most frontend routes return HTTP 200

Strong existing foundations: session auth, tenant context, Stripe webhook idempotency, SSRF allowlists, connector credential encryption, startup fail-closed for staging/prod, broad pytest suite (~120 tests).

---

## 3. Broken functionality (local / drift)

| Issue | Impact |
| --- | --- |
| SQLite `create_all` does not add new columns to existing tables | `connections.next_sync_at` missing → Mission Control / data / platform-ops **500** |
| Local DB has no `alembic_version` | Cannot safely `upgrade head` without stamp/reconcile path |
| Redis down + `CONNECTOR_SYNC_INLINE=false` | `/health/ready` **503**; connector sync enqueue **503** |
| `./start.sh` uses `.venv/bin/uvicorn` shebang | Points at old machine path → backend fails to start |
| Seed email `demo@supply.local` | Rejected by Pydantic `EmailStr` on `dev-login` |
| Empty datasets | Simulations history, risk assessment rows, PO/SO/events, predictions, workflows |
| Marketing claims vs readiness docs | Copy says production-ready; roadmap says paid pilots No-Go |

---

## 4. Schema / migration problems

- **Authoritative schema:** SQLAlchemy models in `backend/app/models/models.py`.
- **Canonical apply path:** `alembic upgrade head` (Postgres + RLS via `0002` / `0009`).
- **Anti-pattern:** `init-db` / startup `create_all` — creates tables **without RLS**; does not alter existing columns.
- **Drift example:** `next_sync_at` defined in ORM + `0006`, but local SQLite connections table never received the column.
- **`0005`:** adds `device_label` non-idempotently (fails if re-run); `device_trusted` only via `create_all`.
- **`0002`:** rebuild via `create_all` at migrate time — history is not pure DDL; additive revisions 0003–0009 mitigate greenfield.

**Requirement:** Fresh empty DB → migrations → boot. Existing DB → migrations → boot. Seed separate from migrations.

---

## 5. Security risks

| Risk | Severity | Notes |
| --- | --- | --- |
| Using `create_all` on shared Postgres | Critical | No FORCE RLS |
| Cookie CSRF (SameSite=lax only) | Medium | No double-submit token on mutating APIs |
| Org id from frontend (`X-Organization-Id` / localStorage) | Medium | Safe only if backend membership check always runs (it does in `ensure_request_context`) |
| Rate limit memory fallback without Redis | Medium | Weaker under multi-replica |
| `FEATURE_BILLING_ENFORCE` default false | Medium | Limits not enforced until flag + secure boot |
| Incomplete `ROLE_RANK` | Low–Medium | Invite policy gaps for some system roles |
| Legacy deps (`python-jose`, `passlib`) | Low | Supply-chain surface |
| `NEXT_PUBLIC_DEV_LOGIN` in compose defaults | High if mis-deployed | Must be false outside local |

Positive: Fernet credentials, hashed sessions/tokens, Stripe signature verify, SSRF allowlists, secure boot checks, security headers.

---

## 6. Multi-tenancy risks

- App-layer `organization_id` filters + Postgres RLS (when migrated) = defense in depth.
- SQLite local/tests rely on app filters only.
- Tables intentionally outside RLS: `users`, `organizations`, `memberships`, `invitations`, `sessions`, `oauth_login_states`, `stripe_events` — must remain carefully authorized.
- Existing tests: `test_tenant_isolation.py`, `test_auth_guards.py`, `test_rls.py` (Postgres CI).

---

## 7. Missing production configuration

- WorkOS, Stripe, Redis, strong `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`, `SESSION_COOKIE_SECURE`, `FEATURE_BILLING_ENFORCE=true`
- Worker process always running
- Alembic on deploy (already in Dockerfile / compose)
- Cross-origin cookie / CORS if frontend and API on different hosts
- Sentry / JSON logging optional deps not always in requirements
- Frontend Docker ARG bake for all `NEXT_PUBLIC_*`

---

## 8. Missing tests

Present: auth guards, RBAC, tenant isolation, Stripe, connectors/SSRF, startup checks, phase B/C APIs.  
Gaps: migration apply from empty DB in CI, Mission Control integration after schema, full disruption workflow E2E, Redis-down degraded behavior, frontend page error/retry consistency, live WorkOS SSO.

---

## 9. Deployment blockers

1. Schema must come from Alembic (never `create_all` in prod).
2. Redis + worker required for connectors (unless emergency inline — blocked in secure boot).
3. Secrets and WorkOS must be set or process refuses boot.
4. Do not ship with `NEXT_PUBLIC_DEV_LOGIN=true` or `FEATURE_DEMO_SANDBOX=true`.
5. Prove cookie sessions across split domains or reverse-proxy same-origin.
6. Fix local `start.sh` so engineers do not invent one-off broken setups.

---

## 10. Recommended implementation order

1. **Migrations + schema reconcile + start.sh** (unblock 500s)
2. **Health / Redis degraded semantics for local**
3. **Auth/tenant isolation verification + ROLE_RANK fix**
4. **Mission Control + disruption → impact → recommendation**
5. **Graph relationships from real seed data**
6. **AI provider abstraction + grounded Copilot**
7. **Simulations + connectors/import polish**
8. **Billing enforce paths / plan limits**
9. **Frontend loading/error/empty consistency**
10. **Tests, Docker prod compose, docs, QA**

---

## Live probe snapshot (pre-fix)

- `/health` 200; `/health/ready` 503 (`not_ready:redis`) with default config
- Authenticated GETs: **44/54 OK**, **10 × 500** (Mission Control, data summary/sources/integrations, data-quality, platform-ops, observability, CS health/onboarding, connector diagnostics) — root cause: missing `connections.next_sync_at`
- Frontend routes: all sampled pages 200
