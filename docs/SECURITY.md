# ATLASOPS Security Overview

Defense-in-depth for a multi-tenant B2B SaaS. Compromising one layer must not
automatically compromise the entire platform.

## Trust boundaries

```
[Browser / SPA] --HTTPS+cookies--> [Next.js] --same-origin API--> [FastAPI]
                                                              |
                         WorkOS AuthKit (IdP) <--- OAuth/OIDC ---+
                                                              |
                    [Postgres FORCE RLS]  [Redis+ARQ]  [Stripe webhooks]
                              ^                ^              ^
                         app role           signed jobs    signature +
                         no BYPASSRLS       HMAC tenant     customer index
```

## Core controls

| Layer | Control |
| --- | --- |
| Auth | WorkOS AuthKit; httpOnly / Secure / SameSite session cookies; no JWT in localStorage |
| Dev login | Disabled unless `ENVIRONMENT=development` |
| CSRF | Origin/Referer check required in staging + production |
| Tenancy | Membership-verified org context; FORCE RLS; GUC rebound after commit |
| RBAC | `require_permission(...)` on sensitive routes |
| IDOR | Explicit `organization_id` filters + RLS |
| Connectors | HTTPS allowlists + private IP rejection (SSRF) |
| Uploads | Size / extension / content-type allowlists; sanitized names |
| AI | Tools enforce RBAC independently of the model; prompts capped |
| Workers | HMAC-signed tenant job payloads |
| Billing | Stripe signature + idempotency + `stripe_customer_index` |
| Rate limits | Redis-backed; auth fails closed in hardened envs when Redis is down |
| Secrets | Env/secret manager only; `.env` gitignored; CI gitleaks |

## Related docs

- [THREAT_MODEL.md](./THREAT_MODEL.md)
- [SECURITY_RUNBOOK.md](./SECURITY_RUNBOOK.md)
- [SECURITY_AUDIT.md](./SECURITY_AUDIT.md)
- Root [SECURITY.md](../SECURITY.md) (policy + checklist)
