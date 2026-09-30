# ATLASOPS Threat Model

## Assets

| Asset | Sensitivity |
| --- | --- |
| Tenant operational data (shipments, inventory, suppliers, orders) | High |
| Connector credentials (encrypted at rest) | Critical |
| Session cookies / API tokens | Critical |
| Billing / Stripe customer mapping | High |
| AI prompts + report history | Medium–High |
| Audit logs | High (integrity) |
| Redis job queue | High (tenant job execution) |

## Trust boundaries

1. **Internet → Frontend** — untrusted browser content; XSS surface.
2. **Frontend → API** — cookie session; CSRF; never trust client org IDs alone.
3. **API → Postgres** — application role under FORCE RLS; GUC `app.current_org_id`.
4. **API → Redis/ARQ** — jobs must carry HMAC signatures; Redis must not be public.
5. **Stripe → Webhooks** — signature-verified only; customer→org via index.
6. **Connectors → External SaaS** — allowlisted HTTPS hosts only.
7. **IdP (WorkOS)** — authoritative identity; ATLASOPS stores memberships/roles.

## Attack surfaces

- Auth/session endpoints, invitations, org switching
- REST APIs (CRUD, search, export, analytics, simulations)
- File uploads (CSV/Excel/documents)
- Connector config URLs and sync workers
- AI chat / orchestrate tools
- Stripe webhooks
- Redis enqueue (lateral movement)
- Admin / security settings

## Threat actors

| Actor | Intent |
| --- | --- |
| External anonymous | Account takeover, DoS, SSRF, webhook forge |
| Malicious tenant user | Cross-tenant read/write (IDOR/BOLA), privilege escalation |
| Compromised session | Persistence, export abuse, connector theft |
| Insider with Redis access | Forge jobs as another org (mitigated by HMAC + network isolation) |
| Supply-chain / dependency | CVE in Python/Node packages |

## Key scenarios & mitigations

| Scenario | Mitigation |
| --- | --- |
| Spoof `X-Organization-Id` | Membership check before tenant context |
| Guess another org's UUID | Tenant filters + FORCE RLS → 404 |
| CSRF from evil origin | CSRF Origin middleware in hardened envs |
| SSRF to metadata/private IP | Connector SSRF allowlist + private IP reject |
| Prompt injection → tool escalation | Tools re-check RBAC; AI not an auth boundary |
| Unsigned ARQ job as Org B | HMAC job signing; Redis AUTH required in prod |
| Stripe metadata remaps org | Customer index wins over metadata |
| Dev-login in production | Hard reject unless `ENVIRONMENT=development` |
| Redis AUTH missing in prod | Fail-closed startup check |

## Residual risks (accepted / open)

- Incomplete audit hash chain under some failure modes
- Virus scan status remains `pending` without an external scanner
- Redis lateral access still dangerous if signing key is also compromised
- Live WorkOS / Stripe / production hosting not fully evidenced in this repo alone
- Dependency CVEs may appear between audit scans

## Architecture (text)

```
                    +------------------+
                    |   WorkOS IdP     |
                    +--------+---------+
                             |
+----------+   cookies   +---v---+   SQL+GUC   +------------------+
| Next.js  | ----------->| FastAPI|---------->| Postgres FORCE RLS|
+----------+             +---+---+            +------------------+
                             |
              +--------------+--------------+
              |              |              |
         +----v----+   +-----v-----+   +----v-----+
         | Redis   |   | Stripe    |   | Outbound |
         | ARQ+HMAC|   | webhooks  |   | SSRF gate|
         +---------+   +-----------+   +----------+
```
