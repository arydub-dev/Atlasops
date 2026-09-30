# ATLASOPS Security Audit Report

**Role:** Principal Application Security Engineer  
**Date:** 2026-08-12  
**Scope:** Full-repository production hardening pass (auth, tenancy, RBAC, IDOR, SSRF, uploads, AI, Stripe, workers, secrets, HTTP, rate limits, CI, docs)  
**Honesty rule:** This report does **not** claim ATLASOPS is unhackable or “100% secure.”

---

## Security score

| Dimension | Score (0–10) | Notes |
| --- | --- | --- |
| Authentication / sessions | 8.5 | WorkOS + httpOnly cookies; prod blocks dev-login |
| Multi-tenant isolation | 9.0 | FORCE RLS + GUC rebind + API org filters |
| Authorization / RBAC | 8.0 | Server-side `require_permission`; matrix residual gaps possible on niche routes |
| SSRF / connectors | 8.5 | Allowlists + private IP rejection |
| Billing / webhooks | 8.5 | Signature + idempotency + customer index preferred over metadata |
| Worker / Redis trust | 8.0 | HMAC job signing + Redis AUTH boot checks |
| Upload / DoS bounds | 8.0 | Size/extension allowlists; pagination caps exist |
| Frontend / XSS surface | 7.0 | Cookie auth good; npm high CVEs in Next/postcss/sharp |
| Ops evidence (live WorkOS/Stripe/Docker) | 4.0 | Not proven in this environment |
| **Overall (engineering controls)** | **8.2** | Strong defense-in-depth in code |
| **Overall (production readiness)** | **5.5** | Blocked by live evidence + dependency CVEs + staging gates |

---

## Readiness verdict (evidence-based)

**DESIGN-PARTNER READY (CLOSE) — not yet** for unpaid design partners on shared staging until live WorkOS + hosted stack gates pass.

**PAID-PILOT READY — NO**  
**PRODUCTION READY — NO**

Closest accurate label for *codebase security controls*: **strong design-partner candidate after live auth/billing soak**.  
Closest accurate label for *commercial release*: **NOT READY**.

---

## Critical issues

| ID | Status | Finding |
| --- | --- | --- |
| — | None open in code review of this pass | No unfixed Critical that allows unauthenticated cross-tenant data access under intended deployment assumptions |

---

## High issues

| ID | Status | Finding |
| --- | --- | --- |
| H1 | **Fixed** | Unsigned ARQ jobs could run as arbitrary org if Redis was reachable → HMAC signing + verify in hardened envs |
| H2 | **Fixed** | CSRF only enforced in production boot → required for all hardened envs |
| H3 | **Fixed** | AI orchestrate loaded timeline/graph without same RBAC gates as chat context → gated on `mission.read`/`network.read` |
| H4 | **Open (deps)** | `npm audit` reports **4 high** issues (Next→postcss, sharp/libvips). Not blindly major-upgraded in this pass |
| H5 | **Open (ops)** | Live WorkOS SSO, Stripe webhooks, Docker production compose not evidenced here |
| H6 | **Partial** | `pip-audit`: patched `python-jose` 3.4.0, `python-multipart` 0.0.31, `cryptography` 44.0.1. Remaining: starlette/FastAPI-bound CVEs and further cryptography majors — schedule coordinated upgrade |

---

## Medium issues

| ID | Status | Finding |
| --- | --- | --- |
| M1 | **Fixed** | Simulation engine relied on RLS alone → explicit `organization_id` filters |
| M2 | **Fixed** | Stripe metadata could win over customer mapping → customer index preferred; mismatch logs + uses index |
| M3 | **Fixed** | Upload MIME/extension allowlists incomplete → `assert_safe_upload` on imports + documents |
| M4 | **Fixed** | Auth rate-limit Redis fail-open in hardened envs → fail-closed for auth when Redis down |
| M5 | **Accepted** | Virus scan remains `pending` without an external scanner |
| M6 | **Accepted** | Invite tokens may appear in URLs (short-lived; prefer POST body where possible) |
| M7 | **Open** | Incomplete audit hash chain under some failure modes (prior AppSec note) |

---

## Low issues

| ID | Status | Finding |
| --- | --- | --- |
| L1 | **Fixed** | Frontend `/auth/callback` missing Suspense boundary (build break / CSR bailout) |
| L2 | **Fixed** | Alembic head assertions lagged at `0011` → updated to `0013` |
| L3 | **Info** | In-memory rate-limit fallback remains for non-auth routes in multi-replica (Redis preferred) |
| L4 | **Info** | gitleaks not installed locally; CI job added |

---

## Fixed in this pass (summary)

1. HMAC-signed tenant ARQ jobs (`job_security.py`, queue/worker)  
2. CSRF + Redis AUTH required in hardened boot  
3. AI orchestrate RBAC parity for timeline/graph  
4. Simulation org-scoped queries  
5. Stripe resolve prefers `stripe_customer_index`  
6. Upload allowlists + upload/AI rate limits  
7. Auth rate-limit fail-closed in hardened envs  
8. Attack-matrix regression tests  
9. CI `security` job (gitleaks + focused pytest + pip-audit + FE secret hygiene)  
10. Docs: `SECURITY.md`, `THREAT_MODEL.md`, `SECURITY_RUNBOOK.md`, this audit  
11. `rolbypassrls` assertion for app DB role  
12. Auth callback Suspense fix for production frontend build  

---

## Remaining risks

- Dependency CVEs (frontend high; Python audit must be re-run in CI)  
- Redis + signing-key compromise still allows forged jobs  
- No external penetration test completed  
- Staging/production live path (WorkOS, Stripe, private network Redis/Postgres) unproven in this workspace  
- Prompt injection residual (AI never authorization boundary, but social-engineering of operators remains)  
- Emergency lockout does not revoke IdP sessions (prior accepted risk)

---

## Tests executed

| Suite | Result |
| --- | --- |
| Backend SQLite full pytest | **162 passed**, 15 skipped |
| Postgres RLS (`test_rls` + `test_postgres_api_rls`) | **8 passed** (includes `rolbypassrls=false`) |
| Postgres security subset (API RLS, Stripe FORCE RLS, tenant isolation, attack matrix, SSRF) | **45 passed** |
| Frontend `npm run build` | **PASS** (after Suspense fix) |
| `npm audit --omit=dev` | **4 high** reported (documented) |
| `pip-audit -r requirements.txt` | **30 findings** before patch; applied jose/multipart/cryptography pins; residual starlette/cryptography majors remain |
| Local gitleaks | Not installed; **wired in CI** `security` job |

### Attack matrix coverage

| ID | Case | Covered by |
| --- | --- | --- |
| A | Cross-tenant UUID | `test_security_attack_matrix` + tenant isolation |
| B | Spoofed `X-Organization-Id` | attack matrix + auth guards |
| C–G | Missing/stale GUC, commit/rollback, pool | Postgres RLS / API RLS suites |
| H | Unauthorized RBAC | attack matrix (viewer simulation/AI) |
| I–K | SSRF localhost/private/metadata | SSRF + attack matrix |
| L–M | Path/exe / oversized upload | attack matrix |
| N–O | Forged/duplicate Stripe | stripe webhook + FORCE RLS suites |
| P–Q | AI escalation | attack matrix + AI RBAC |
| R–S | Export/unauth | unauth sensitive API tests |
| T | Prod dev-login | attack matrix + enterprise auth |
| U | Job signature / secrets | job signing tests + CI gitleaks |
| V–W | CORS / CSRF | startup checks + CSRF tests |

---

## Security controls implemented (defense in depth)

- WorkOS AuthKit sessions (httpOnly / Secure / SameSite)  
- Dev-login impossible outside development  
- Membership-verified tenant context; FORCE RLS; GUC rebound after commit  
- RBAC on sensitive endpoints  
- Explicit org filters on simulations + resource lookups  
- Connector SSRF allowlists  
- Upload size/type validation  
- AI context permission gating; prompt size cap  
- Stripe signature, idempotency, customer→org index  
- Signed ARQ jobs; Redis AUTH boot checks  
- Redis-backed rate limits; auth fail-closed when Redis down (hardened)  
- Security headers / CSRF Origin middleware  
- Secret scanning + security pytest job in CI  

---

## Production deployment requirements

1. Unique `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`, WorkOS cookie password  
2. WorkOS + Stripe production credentials; webhook secret verified  
3. `ENVIRONMENT=production`, `CSRF_ORIGIN_CHECK=true`, `SESSION_COOKIE_SECURE=true`  
4. Authenticated `REDIS_URL` (TLS preferred); private network only  
5. Postgres managed TLS; app role **without** `BYPASSRLS` / superuser  
6. Alembic `upgrade head` only (no `create_all`)  
7. `NEXT_PUBLIC_DEV_LOGIN=false`; no secrets in `NEXT_PUBLIC_*`  
8. Pass CI security job (gitleaks + tenant/RLS/SSRF/CSRF/Stripe tests)  
9. Schedule external penetration test before paid GA  
10. Remediate or risk-accept frontend dependency highs with patch cadence  

---

## Recommended external penetration testing

Focus areas: multi-tenant IDOR across all resources, connector SSRF/DNS rebinding, session/CSRF, Stripe webhook abuse, Redis/worker trust, AI tool abuse, export/DoS.

---

*See also: [SECURITY.md](./SECURITY.md) · [THREAT_MODEL.md](./THREAT_MODEL.md) · [SECURITY_RUNBOOK.md](./SECURITY_RUNBOOK.md) · [SECURITY_AUDIT_APPSEC.md](./SECURITY_AUDIT_APPSEC.md)*
