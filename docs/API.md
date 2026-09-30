# API Reference (Supply v2)

Base URL: `http://localhost:8000`  
Business endpoints: `/api/v1/...`

Interactive docs: `/docs` and `/redoc` (disabled when `ENVIRONMENT=production` unless `ENABLE_API_DOCS=true`).

## Authentication model

Supply v2 does **not** use JWT-in-`localStorage` password login.

| Mechanism | How |
| --- | --- |
| Browser sessions | httpOnly cookie `supply_session` (WorkOS AuthKit / SSO callback, or `POST /auth/dev-login` in development only) |
| Active organization | Header `X-Organization-Id: <uuid>` (or session’s current org) |
| Machine access | `Authorization: Bearer <api_token>` created under `/orgs/current/tokens` |

All tenant data endpoints require authentication **and** an organization context. Permissions are enforced with `require_permission("resource.action")`.

### Auth endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/auth/login` | public (rate-limited) | Returns WorkOS `authorization_url` |
| GET | `/auth/callback` | public (rate-limited) | OAuth code exchange; sets session cookie |
| POST | `/auth/logout` | session | Revokes session; clears cookie |
| GET | `/auth/me` | session/token | User, memberships, current org |
| POST | `/auth/switch-org` | session | Switch active organization |
| POST | `/auth/dev-login` | public, **dev only** | Local bypass when WorkOS unset |

```bash
# Development login (WorkOS not configured)
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","full_name":"You"}'

# Authenticated call
curl -b cookies.txt http://localhost:8000/api/v1/mission-control \
  -H "X-Organization-Id: <org-uuid>"
```

## Organizations

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| POST | `/orgs` | authenticated | Create organization (caller becomes owner) |
| GET | `/orgs` | authenticated | List my organizations |
| GET/PATCH | `/orgs/current` | `org.read` / `org.update` | Current org |
| POST | `/orgs/current/invitations` | `org.members.invite` | Invite member |
| POST | `/orgs/invitations/accept` | authenticated | Accept invite (email must match) |
| GET/PATCH/DELETE | `/orgs/current/members...` | member manage | Members |
| POST | `/orgs/current/tokens` | `org.tokens.manage` | Create API token (raw token shown once) |
| GET | `/orgs/current/audit-logs` | `org.audit.read` | Audit trail |
| GET | `/orgs/current/usage` | `org.usage.read` | Usage snapshot |

## Billing

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/billing/plans` | public | Plan catalog |
| GET | `/billing/account` | `org.billing.manage` | Current org billing account |
| POST | `/billing/checkout` | `org.billing.manage` | Stripe Checkout (FRONTEND_URL allowlisted return URLs) |
| POST | `/billing/portal` | `org.billing.manage` | Stripe Customer Portal |
| POST | `/billing/cancel` | `org.billing.manage` | Cancel subscription |
| POST | `/billing/webhooks/stripe` | Stripe signature | Webhooks (idempotent via `stripe_events`) |

Path variants `/billing/.../{organization_id}` remain for compatibility but **must** match the active org or return 403.

## Data / connectors

| Method | Path | Permission | Description |
| --- | --- | --- | --- |
| GET/POST | `/data/sources` | connectors.* | List/create connections |
| PUT | `/data/sources/{id}/config` | `connectors.update` | Config + `credentials` dict (or legacy `api_key`) |
| POST | `/data/sources/{id}/test` | `connectors.sync` | Live connection test |
| POST | `/data/sources/{id}/sync` | `connectors.sync` | Live sync (Dynamics BC / Salesforce / UPS) |
| POST | `/data/import/...` | imports.* | CSV/Excel import |

Credential storage format: Fernet-encrypted JSON object. Legacy single-string blobs are accepted and migrated forward.

## Core operational APIs

Shipments, inventory, suppliers, risks, simulations, alerts, analytics, network, mission-control, and AI advisor remain under `/api/v1/...` with UUID identifiers and organization-scoped queries. Prefer OpenAPI `/docs` for the live schema.

## Health & metrics

| Path | Notes |
| --- | --- |
| `/health`, `/health/live`, `/health/ready` | Liveness / readiness |
| `/metrics` | Prometheus; in production requires `Authorization: Bearer $METRICS_TOKEN` |
