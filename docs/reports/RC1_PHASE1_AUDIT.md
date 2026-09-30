# Release Readiness Audit — Phase 1 (Evidence-Based)

**Date:** 2026-07-24  
**Goal:** Supply v2 → Release Candidate (RC1) assessment  
**Method:** Static code + test suite inspection. Live WorkOS/Stripe/Salesforce/Dynamics/UPS sandboxes were **not** available in this environment.

---

## Category scorecards

### Backend
| | |
|---|---|
| **Current State** | FastAPI multi-tenant API; session + API token auth; permission-gated routers; Alembic + RLS |
| **Strengths** | Org-scoped domain queries; billing authz tests; fail-closed production boot |
| **Weaknesses** | Stripe webhook does not set RLS GUC; sync inline; some docs drift in code comments only |
| **Risk** | Critical (webhook/RLS) |
| **Production Recommendation** | Fix webhook tenant context before paid Stripe |

### Frontend
| | |
|---|---|
| **Current State** | Next.js app + onboarding; cookie credentials; no Playwright |
| **Strengths** | No JWT localStorage; CSV import UI complete; logout/org switcher |
| **Weaknesses** | Settings lacks tokens/billing/invite accept UI; connector form is API-key oriented |
| **Risk** | Medium |
| **Production Recommendation** | Ship Playwright for Ready workflows; Settings polish can wait for beta |

### Database
| | |
|---|---|
| **Current State** | UUID multi-tenant schema; RLS on TENANT_TABLES; indexes 0003 |
| **Strengths** | Forced RLS policies; reversible index migration |
| **Weaknesses** | Superuser compose role bypasses RLS; DATABASE.md still v1 |
| **Risk** | High if app role is superuser |
| **Production Recommendation** | Non-superuser app role + webhook GUC/bypass policy |

### CI/CD
| | |
|---|---|
| **Current State** | Lint/typecheck/build + SQLite pytest + Postgres Alembic/RLS |
| **Strengths** | Dual DB matrix |
| **Weaknesses** | pip-audit non-blocking; no Playwright; no image publish |
| **Risk** | Medium |
| **Production Recommendation** | Add Playwright; keep Postgres job required |

### Docker / Infrastructure
| | |
|---|---|
| **Current State** | Compose: Postgres+Redis+API+worker+frontend; Render: API+web only |
| **Strengths** | Secure prod env defaults in render.yaml |
| **Weaknesses** | Render missing Redis/worker; Redis open locally |
| **Risk** | High for async connectors on Render as-is |
| **Production Recommendation** | Add Redis+worker for any connector-heavy pilot |

### Authentication / Authorization / Multi-tenancy
| | |
|---|---|
| **Current State** | WorkOS + sessions; RBAC catalog; app + RLS isolation |
| **Strengths** | Strong billing/RBAC/isolation tests |
| **Weaknesses** | API token can switch orgs via header if user is multi-member; logout cookie missing `secure` |
| **Risk** | Medium |
| **Production Recommendation** | Bind tokens to org; fix cookie clear |

### Billing
| | |
|---|---|
| **Current State** | Stripe checkout/portal/cancel + signed webhooks; authz solid |
| **Strengths** | Path/org match; FRONTEND_URL allowlist; tests |
| **Weaknesses** | **No event idempotency**; webhook RLS gap; enforce flag default false |
| **Risk** | Critical (RLS) / High (idempotency) |
| **Production Recommendation** | Block live Stripe until both fixed |

### Connectors
| | |
|---|---|
| **Current State** | Real SDK + BC/SF/UPS; encrypted credentials |
| **Strengths** | No simulated sync in code path |
| **Weaknesses** | Inline sync; SSRF via custom URLs; no live E2E without credentials |
| **Risk** | High |
| **Production Recommendation** | Market as Beta; staging E2E required |

### Security / Observability / Performance / Audit / Docs
Summarized: fail-closed boot **good**; metrics/docs gated **good**; OTel optional **medium**; metrics SQL improved **good**; audit chain incomplete **medium**; README/ARCHITECTURE/DATABASE/INTEGRATIONS **High** doc drift.

---

## Staging validation (Phase 2) — blocked without secrets

Cannot complete live validation of WorkOS, Stripe test mode, SF/Dynamics/UPS sandboxes in this environment.

**What was validated statically:** env schema (`.env.example`), production fail-closed checks, CORS credentials mode, session cookie flags, CSP headers middleware, webhook signature requirement.

---

## Critical / High issues to fix for RC1 (implementation follows)

| ID | Severity | Issue | Fix |
|---|---|---|---|
| C1 | Critical | Webhook DB session has no tenant GUC under FORCE RLS | Resolve org + `set_session_org` / controlled `row_security` for lookup |
| H1 | High | No Stripe `event.id` idempotency | `stripe_events` table + short-circuit |
| H2 | High | API token org binding soft | Require `token.organization_id ==` active org |
| H3 | High | Legacy docs (README/ARCHITECTURE/DATABASE/INTEGRATIONS) | Rewrite to v2 |
| H4 | Medium→High | No browser E2E | Playwright for Ready workflows |
| M1 | Medium | Logout cookie omit secure | Match set_cookie flags |
