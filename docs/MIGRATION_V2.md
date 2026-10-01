# Supply v2 — Commercial SaaS Migration Plan

**Status:** Foundation + P0–P2 hardening complete — configure WorkOS + Stripe + connector credentials for production go-live  
**Target:** Production-grade multi-tenant B2B SaaS foundation  
**Architecture locks:** Shared PostgreSQL + RLS · WorkOS Auth · Stripe Billing · Connector SDK (Dynamics 365 BC, Salesforce, UPS)

Hardening reports: [`docs/reports/P0_COMPLETION.md`](reports/P0_COMPLETION.md), [`P1_COMPLETION.md`](reports/P1_COMPLETION.md), [`P2_COMPLETION.md`](reports/P2_COMPLETION.md).

---

## 1. Architectural conflicts (current → target)

| Area | Current state | Conflict | Resolution |
| --- | --- | --- | --- |
| Tenancy | Global tables, no `organization_id` | Cross-tenant data leak by design | Add `organization_id` to all tenant-owned rows; enforce via app filters **and** PostgreSQL RLS |
| Users | Single global `role` on `User`; email unique | Cannot belong to multiple orgs; no org-scoped roles | Global `User` (WorkOS identity) + `Membership(org, user, role)` |
| Auth | JWT in `localStorage`; password OAuth2 | XSS-exposed tokens; no SSO/SAML/OIDC/MFA | WorkOS AuthKit; httpOnly secure session cookie; remove password JWT flow |
| RBAC | 4 coarse roles; admin bypass | Not enterprise-auditable | Permission catalog + role→permission map + custom roles; enforce on every endpoint |
| Settings | Global `app_settings` PK=`key` | Shared across tenants | Per-org settings |
| Uniqueness | `products.sku`, `shipments.reference` global unique | Collides across tenants | Unique `(organization_id, sku)` / `(organization_id, reference)` |
| Connectors | Simulated `sync_connector` / fake test | Cannot sell integrations | Delete simulation; Connector SDK + real Dynamics BC, Salesforce, UPS |
| Seeding | `SEED_ON_STARTUP=true` default in compose/render | Production ships demo data | Default `false`; optional `supply seed-demo` CLI only |
| Demo mode | Client flag regenerates alerts/risks | Demo assumptions in product path | Remove from production UX; optional feature-flagged sandbox orgs only |
| Billing | Marketing-only pricing | No commercial layer | Stripe Customer + Subscription + meters + webhooks + plan gates |
| Jobs | Sync request-path work | No retries/isolation | ARQ + Redis; every job carries `organization_id` |
| Observability | `logging.basicConfig` + `/health` | Not operable | OpenTelemetry + structured JSON logs + Prometheus metrics |
| CI | None | Unsafe to ship | GitHub Actions: lint, typecheck, pytest, frontend tests, security scan, build |
| Marketing | Claims multi-tenant / SSO / Available connectors | Procurement risk | Status badges: Available / Beta / Coming Soon / Enterprise |

---

## 2. Target domain model

```
Organization (tenant)
  ├── Membership ── User (WorkOS)
  ├── Role / Permission / CustomRole
  ├── Invitation
  ├── ApiToken
  ├── WebhookEndpoint
  ├── BillingAccount (Stripe customer/subscription)
  ├── UsageRecord (seats, AI credits, API, storage)
  ├── Site / Facility / Department / Team  (org hierarchy)
  └── Domain data (Supplier, Warehouse, Product, Inventory,
      Shipment, Alert, Risk, Simulation, AIReport,
      Connection, ImportJob, AuditLog, FileObject, …)
      all with organization_id NOT NULL
```

**Request context (required on every authenticated call):**

```
organization_id · user_id · membership_id · permissions[] · request_id
```

Injected via middleware + `contextvars`; DB session runs:

```sql
SELECT set_config('app.current_org_id', :org_id, true);
```

RLS policies: `USING (organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)`

---

## 3. Phase execution order

Each phase must leave the app **deployable** with **passing tests** before the next.

| Phase | Deliverable | Done when |
| --- | --- | --- |
| **1** Multi-tenancy | Models, RLS, tenant context, scoped repos/routers | Isolation tests pass; no unscoped domain query |
| **2** WorkOS auth | AuthKit, sessions, SSO hooks, invitations | Login/logout/SSO callback work; JWT localStorage gone |
| **3** RBAC | Permission catalog, custom roles, enforcement | Permission matrix tests; every write endpoint gated |
| **4** Stripe | Plans, checkout, portal, webhooks, enforcement | Trial→paid lifecycle works against Stripe test mode |
| **5** Onboarding | Signup → org → plan → import → connect → invite | &lt;15 min happy path E2E |
| **6** Connector SDK | Base protocol, registry, encryption, jobs | Framework + health/sync/retry real |
| **6b** Integrations | Dynamics 365 BC, Salesforce, UPS | Live API calls; no random/fake sync |
| **7** Import | Mapping wizard, preview, rollback, history | Production-safe CSV/Excel/JSON import |
| **8** Security | Headers, rate limit, secrets, cookies, scans | Hardening checklist green |
| **9** Observability | OTel, metrics, structured logs, readiness | Traces visible; `/ready` / `/live` |
| **10** CI/CD | GitHub Actions | PR gates + deploy workflow |
| **11** Testing | Isolation, auth, billing, connector, E2E | Backend ≥90% / Frontend ≥80% targets pursued |
| **12** Ops | Prod images, backups/DR docs, graceful shutdown | Runbooks published |
| **13** Marketing | Honest copy + status badges | No false Available claims |

**Explicitly out of scope (later):** SAP, Oracle, NetSuite, multi-agent AI, workflow builder, K8s/multi-region.

---

## 4. Package layout (backend)

```
backend/app/
  core/           # config, database, logging, telemetry, security headers
  tenancy/        # context, mixin, middleware, rls helpers
  identity/       # WorkOS client, sessions, invitations
  rbac/           # permissions, roles, enforce
  billing/        # Stripe service, webhooks, plans
  orgs/           # organization lifecycle services + routers
  connectors/     # SDK + dynamics_bc, salesforce, ups
  domain/         # existing operational models (tenant-scoped)
  workers/        # ARQ jobs
  api/            # routers (thin)
```

Frontend adds: `/onboarding/*`, `/org/*` admin, WorkOS AuthKit, httpOnly session via BFF callbacks, remove demo credentials.

---

## 5. Cutover strategy

1. **Greenfield migration:** Alembic revision rebuilds tenant-aware schema (dev/demo DBs reset; no production customer data exists yet).
2. **Feature flags:** `FEATURE_DEMO_SANDBOX`, `FEATURE_BILLING_ENFORCE` for staged rollout.
3. **Default production:** empty org data; `SEED_ON_STARTUP=false`.
4. **Marketing:** ship Phase 13 copy as soon as Phase 1–2 land so claims never lead implementation.

---

## 6. Success criteria (v2 complete)

- [x] Cross-tenant isolation proven by automated tests (app-level + Postgres RLS CI job)
- [x] WorkOS AuthKit path implemented (configure keys for live SSO); dev-login for local
- [x] Org admin: invite/accept, suspend, transfer ownership, delete, audit, tokens, webhooks
- [x] Stripe checkout/portal/cancel/webhooks + authz; plan gates when `FEATURE_BILLING_ENFORCE`
- [x] Self-serve onboarding UI (org → plan → import → connect → invite)
- [x] Three live connectors (Dynamics BC, Salesforce, UPS) via Connector SDK
- [x] CI: lint/typecheck/build + SQLite pytest + Postgres Alembic/RLS pytest
- [x] Marketing status badges accurate; production defaults secure
- [x] No demo seed/default credentials in production config (fail-closed boot checks)
