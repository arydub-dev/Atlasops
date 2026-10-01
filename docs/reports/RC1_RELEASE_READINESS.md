# Release Candidate Readiness Report — Supply v2 RC1

**Date:** 2026-07-24  
**Scope:** Production validation audit + Critical/High readiness fixes (no new product features)  
**Evidence:** Static review, 61 pytest (2 skipped RLS-only), docs rewrite, Playwright smoke added to CI  

Phase 1 audit detail: [`RC1_PHASE1_AUDIT.md`](./RC1_PHASE1_AUDIT.md)  
Staging checklist: [`../STAGING_CHECKLIST.md`](../STAGING_CHECKLIST.md)

---

## Scores (0–10)

| Dimension | Score | Rationale |
| --- | --- | --- |
| Architecture | 8 | Clear multi-tenant + WorkOS + Stripe + Connector SDK; worker/Redis present in Compose |
| Security | 7.5 | Fail-closed prod, RLS, org-bound tokens, webhook idempotency+tenant GUC fixed this cycle |
| Performance | 6.5 | P2 SQL improvements; no formal P95 bench in this environment |
| Reliability | 6.5 | Idempotent Stripe events; webhook RLS fixed; connector sync still often inline |
| Maintainability | 7.5 | Docs aligned to v2; Alembic chain clear |
| Scalability | 6 | Shared Postgres+RLS OK for pilots; Render missing Redis/worker historically |
| Developer Experience | 7 | Compose + CI matrix; Playwright smoke; staging secrets still manual |
| Operational Readiness | 6 | OTel optional; staging soak not executed here |
| Commercial Readiness | 6 | Billing authz strong; live Stripe/WorkOS E2E not proven in this env |

---

## Fixes landed in this validation cycle

| ID | Severity | Fix |
| --- | --- | --- |
| C1 | Critical | Stripe webhooks `set_session_org` + controlled customer lookup under RLS |
| H1 | High | `stripe_events` table + claim-before-process idempotency (`0004`) |
| H2 | High | API tokens reject `X-Organization-Id` ≠ `token.organization_id` |
| M1 | Medium | Logout `delete_cookie` matches Secure/HttpOnly flags |
| H3 | High | README / ARCHITECTURE / DATABASE / INTEGRATIONS rewritten for v2 |
| H4 | High | API workflow E2E tests + Playwright smoke in CI |
| — | Medium | CSV commit writes audit log |

Tests: `tests/test_stripe_webhooks.py`, `tests/test_workflows_e2e.py` (invite, CSV+audit, token rotate/binding, isolation, logout).

---

## Remaining issues

### Critical
*None open in code after this cycle.* (Live staging not yet proven — see High.)

### High

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| No completed staging soak with WorkOS + Stripe test + one connector sandbox | Cannot prove end-to-end commercial path | Complete `docs/STAGING_CHECKLIST.md` | 3–5 days |
| Connector sync may still run inline on API request | Timeouts / poor UX under load | Enqueue ARQ jobs from API by default | 1–2 days |
| Render blueprint historically API+web only | Connectors broken on that deploy path | Add Redis + worker services | 0.5 day |
| Playwright does not drive live Checkout/OAuth | Browser regression gaps for workflows 1,3,7 | Add secret-gated Playwright against staging | 2–3 days |
| Configurable connector URLs → SSRF risk | Credentialed server may fetch attacker URLs | Allowlist hostnames per connector | 1 day |

### Medium

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| Audit coverage incomplete on some mutation paths | Investigation gaps | Expand `write_audit` usage | 1–2 days |
| `FEATURE_BILLING_ENFORCE` default false | Soft limits in pilots | Enable for paid pilots intentionally | config |
| No formal latency benchmarks (P95/P99) recorded | Perf unknown under load | Run k6/locust against staging | 1–2 days |
| Settings UI incomplete for tokens/billing | Operator friction | UI polish (not a platform blocker) | 2–3 days |

### Low

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| pip-audit non-blocking in CI | Dependency CVEs may slip | Gate on critical vulns | 0.5 day |
| Optional OpenTelemetry | Weaker distributed tracing | Wire exporter in staging | 1 day |

---

## Workflow validation status

| # | Workflow | Status |
| --- | --- | --- |
| 1 | Signup → checkout → dashboard | Partial (needs WorkOS+Stripe staging) |
| 2 | Invite → accept → permissions | **Pass (API CI)** |
| 3 | Salesforce connect → sync | Blocked (sandbox) |
| 4 | CSV import → audit | **Pass (API CI)** |
| 5 | API token rotate | **Pass (API CI)** |
| 6 | Tenant isolation | **Pass (API CI)** |
| 7 | Billing webhook → plan | **Pass (unit/idempotency)**; live Stripe pending |
| 8 | Logout → revoke | **Pass (API CI)** + UI redirect smoke |

---

## Final decision

⚠ **Suitable for closed beta.**

**Not** General Availability. **Not** unpaid mass commercial rollout.

### Why not lower (❌ / internal-only)?
Critical webhook/RLS and idempotency gaps that blocked commercial billing are closed in code with tests. Authz, tenancy isolation, fail-closed boot, and org-bound tokens are in place.

### Why not higher (design partners / paid pilots / GA)?
High issues remain: **no live staging proof** with WorkOS + Stripe + a real connector; connector SSRF/inline sync risks; incomplete browser E2E for money and OAuth paths. Per release rules, any High issue requires clear risk disclosure — paid pilots should wait until staging checklist is green.

### Exit criteria to upgrade recommendation

1. Staging checklist fully checked  
2. One connector sandbox E2E recorded  
3. Stripe test-mode checkout + webhook duplicate delivery verified in staging  
4. Redis+worker on the chosen host platform  
5. SSRF allowlist merged  

Then re-audit for: **Suitable for enterprise design partners** → **paid commercial pilots**.
