# ATLASOPS Internal Admin Console

Internal operator tool at `/admin`. Not a customer-facing product surface.

## Authorization

* Flag: `users.is_platform_admin` (already on the User model).
* Backend dependency: `require_platform_admin` — **session cookie only**.
* API tokens never inherit platform-admin, even if the creating user is an operator.
* Tenant owners/admins (`Membership.role_slug`) cannot access `/api/v1/admin/*`.
* Frontend nav is UX-only; every console API enforces the flag server-side.

Grant an operator (SQL, as a superuser — not via the customer UI):

```sql
UPDATE users SET is_platform_admin = true WHERE email = 'ops@atlasops.example';
```

## RLS / privileged access

This console **does not** disable RLS, remove FORCE RLS, or use BYPASSRLS.

| Data | How it is read |
| --- | --- |
| Organizations, memberships, users | Identity tables are **not** in `TENANT_TABLES`. Listed the same way connector cron already lists orgs. |
| Connections, jobs, audit logs, DLQ | FORCE RLS remains on. The handler calls `set_session_org(org_id)` **per tenant** and still filters `organization_id` in SQL. |

Tenant GUC is **not** set on the admin dependency itself, so accidental unscoped tenant queries return zero rows on PostgreSQL.

## Endpoints

All under `/api/v1/admin` (existing `POST /admin/seed` is unchanged and still demo-sandbox-only).

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admin/health` | Live Postgres/Redis/ARQ/config checks |
| GET | `/admin/tenants` | Operational tenant table |
| GET | `/admin/tenants/{id}` | Detail; writes `admin.view_tenant` audit |
| GET | `/admin/connectors` | Cross-tenant connector health |
| GET | `/admin/jobs` | Sync + import history |
| GET | `/admin/jobs/{id}?organization_id=` | Single job |
| POST | `/admin/connectors/{id}/retry?organization_id=` | Incremental ARQ enqueue; `admin.retry_sync` audit |
| GET | `/admin/errors` | Grouped redacted errors |

Retry uses the existing HMAC-signed `enqueue_sync_connection` path (incremental). Duplicate ARQ ids are treated as already queued.

## Frontend

* `/admin` dashboard
* `/admin/tenants/[tenantId]`
* `/admin/connectors`
* `/admin/jobs`
* `/admin/errors`

## Live staging still required

Worker heartbeat, Redis queue depth, and retry-against-real-ARQ are only fully proven when Redis + the worker process are running.
