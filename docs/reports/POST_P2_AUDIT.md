# Post–P0–P2 Engineering Re-Audit

**Date:** 2026-07-24  
**Scope:** Re-audit after approved P0–P2 hardening. **No further feature work started.**

## Verdict

Critical blockers from the prior audit are **mitigated in code + tests**. The platform is substantially safer for enterprise pilots, but several High/Medium items remain before calling it procurement-ready without staging validation.

| Area | Prior | Now |
| --- | --- | --- |
| Billing authz | Critical (open) | Fixed + regression tests |
| Connector credential shape | Critical (broken) | Fixed + legacy compat + tests |
| Prod insecure boot | High | Fail-closed checks + tests |
| Auth/isolation tests | Thin | Expanded (53 passed, 2 RLS skipped on SQLite) |
| Rate limiting | Dead code | Wired on auth; TRUST_PROXY |
| Metrics tenant scope | High leak risk | Org-scoped + SQL aggregates |
| Docs/deploy drift | High | API/DEPLOYMENT/SECURITY/render updated |
| Ranking N+1 | High | Batched ranking |
| CI Postgres/RLS | Missing | Job present (RLS tests skip on SQLite) |

## Remaining issues (prioritized)

### High
1. **WorkOS/Stripe/connector live E2E not proven in this environment** — needs staging credentials.
2. **`docs/DATABASE.md` still legacy** — operators could mis-model schema.
3. **ARCHITECTURE.md** still mostly v1 narrative (only auth label patched).
4. **Webhook idempotency** for Stripe events still missing.
5. **Frontend has no Playwright** — onboarding/auth regressions possible.

### Medium
6. Connector sync still primarily inline on request (worker available, not always enqueued).
7. SSRF allowlists for connector `base_url` / custom token URLs not fully hardened.
8. Coverage far from 90%/80% targets (workflow tests preferred over padding).
9. Mission/dashboard still duplicate overlapping work (perf polish).
10. Compose Redis open without AUTH (ok local; document for shared networks).

### Low
11. Legacy JWT helpers remain unused in `security.py`.
12. Synthetic inventory/supplier “trend” endpoints now honest/flat — charts may look sparse until history tables exist.

## Test posture

- Backend: **53 passed**, **2 skipped** (RLS requires Postgres CI job)
- Frontend: **typecheck clean**; lint/build gated in CI
- Do **not** treat SQLite-only green as full RLS proof — rely on `backend-postgres` CI job

## Recommendation

**Stop feature work.** Next engineering cycle should be:

1. Staging soak with real WorkOS + Stripe test mode + one live connector  
2. Rewrite `docs/DATABASE.md` + finish ARCHITECTURE v2 diagrams  
3. Stripe webhook idempotency + Playwright onboarding  
4. Optional: enqueue connector sync via ARQ by default  

No P3 / new product features until the High items above are accepted or closed.
