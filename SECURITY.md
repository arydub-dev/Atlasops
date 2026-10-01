# Security Policy — Supply v2

## Supported versions

| Version | Supported |
| --- | --- |
| `main` (v2) | Yes |
| Pre-v2 single-tenant | No — upgrade required |

## Implemented controls

### Authentication & access
- Email-first enterprise SSO via WorkOS (domain discovery; SAML/OIDC/IdPs configured in WorkOS — not exposed in UI)
- OAuth `state` + PKCE (S256) on authorize/callback; open-redirect allowlist on return paths
- Opaque httpOnly session cookies (not JWT); idle timeout, sliding expiry, remember-device TTL, concurrent session limits, revoke / logout-everywhere
- Session metadata + admin Security dashboard (login history, org session revoke, allowed email domains)
- API tokens (hashed) bound to organization (`token.organization_id`); header cannot switch orgs; no orphaned-user fallback
- Enterprise RBAC via `require_permission(...)` on endpoints
- Auth route rate limiting (`AUTH_RATE_LIMIT_PER_MINUTE`); `X-Forwarded-For` trusted only when `TRUST_PROXY=true`
- Details: [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)

### Multi-tenancy
- `organization_id` on tenant-owned rows
- Request sets `app.current_org_id` for PostgreSQL RLS (hard-fail on Postgres if GUC cannot be set)
- Cross-org path IDs on billing must match active tenant
- Automated isolation + billing authz + API token tests in CI; Postgres RLS job in GitHub Actions

### Billing
- All non-public billing routes require auth + `org.billing.manage`
- Stripe return URLs restricted to `FRONTEND_URL` origin
- Webhooks: signature required; tenant RLS context set; `stripe_events` idempotency
- Plan enforcement helpers run when `FEATURE_BILLING_ENFORCE=true`

### Data & secrets
- Pydantic validation; Fernet credential encryption (JSON dict; legacy string blobs accepted)
- Production boot refuses default `SESSION_SECRET`, missing encryption key, insecure cookie/CORS/seed flags
- Append-oriented audit logs with integrity hash chaining (`app.services.audit.write_audit`)

### Transport & observability
- TLS at proxy; CORS allow-list with credentials
- Security headers middleware
- `/metrics` token-gated in production; OpenAPI disabled in production by default

## Deployment hardening checklist

- [ ] Unique `SESSION_SECRET` (≥32) and `CREDENTIALS_ENCRYPTION_KEY`
- [ ] WorkOS + Stripe production keys; webhook secrets verified
- [ ] `SEED_ON_STARTUP=false`, `FEATURE_DEMO_SANDBOX=false`, `NEXT_PUBLIC_DEV_LOGIN=false`
- [ ] `SESSION_COOKIE_SECURE=true`, `ALLOW_CREATE_ALL_ON_STARTUP=false`
- [ ] `alembic upgrade head` (includes RLS + index migrations)
- [ ] Restrict `CORS_ORIGINS`; set `FRONTEND_URL`
- [ ] Set `METRICS_TOKEN`; set `TRUST_PROXY=true` only behind a trusted proxy
- [ ] Managed Postgres backups ([DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md))

## Reporting

Email security issues privately to the maintainers. Do not file public issues for exploitable vulnerabilities.
