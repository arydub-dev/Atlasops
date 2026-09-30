# Release Candidate 2 (RC2) — Commercial Pilot Readiness

**Date:** 2026-07-24  
**Prior:** RC1 (closed beta) — [`RC1_RELEASE_READINESS.md`](./RC1_RELEASE_READINESS.md)  
**Evidence:** Code audit + fixes + **73 pytest passed** (2 skipped) + Playwright smoke CI + staging tooling  

---

## Scores (0–10)

| Dimension | Score | Notes |
| --- | --- | --- |
| Architecture | 8.5 | Worker/Redis path wired end-to-end; Render includes worker |
| Security | 8.5 | SSRF allowlist; staging/prod fail-closed; org-bound tokens; Stripe idempotency |
| Performance | 6.5 | Benchmark harness shipped; live P95 not measured without staging |
| Reliability | 7 | Queue-based sync; soak **not** executed (template only) |
| Scalability | 7 | Horizontal workers documented |
| Maintainability | 8 | Docs match implementation |
| Developer Experience | 7.5 | Staging compose + secret-gated E2E workflow |
| Operational Readiness | 7 | OPERATIONS + DR docs; restore drill unproven |
| Commercial Readiness | 7 | Design-partner ready in code; paid pilots need soak + live journey proof |

---

## Issues closed in RC2 (verified → fixed)

| ID | Was | Fix |
| --- | --- | --- |
| C-SSRF | Critical | `app.connectors.ssrf` allowlist; reject private IPs / non-HTTPS / unknown hosts; enforced on configure + outbound |
| H-INLINE | High | Sync enqueues ARQ; `CONNECTOR_SYNC_INLINE` forbidden in staging/prod |
| H-RENDER | High | `render.yaml` Redis + worker; `FEATURE_BILLING_ENFORCE=true` |
| H-STAGING-BOOT | High/Med | `ENVIRONMENT=staging` uses same fail-closed family as production |
| H-STAGING-DOCS | High | `docs/STAGING.md`, compose overlay, checklist, ops runbook |
| H-E2E-SECRETS | High | `.github/workflows/staging-e2e.yml` + `e2e/staging/` (skips without secrets) |

---

## Remaining issues

### Critical
*None in code.*

### High (block **paid** pilots; mitigated for design partners)

| Description | Business impact | Technical impact | Fix | Effort |
| --- | --- | --- | --- | --- |
| Staging checklist not executed with live WorkOS/Stripe/connector sandboxes in this environment | Cannot prove full commercial journey | Unknown vendor quirks | Complete `docs/STAGING_CHECKLIST.md`; record results | 3–5 days |
| 7–14 day soak not run | Unknown memory/queue failure modes | Reliability unproven under duration | Run soak; fill `RC2_SOAK_LOG.md` | 7–14 days |
| Full browser journey (signup→checkout→OAuth) not automated against live staging | Regression risk on money path | Partial Playwright only | Extend `e2e/staging` with provisioned test users | 2–3 days |

### Medium

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| Connector retry/429 handling still thin (60s timeout, 401 re-auth only) | Flaky vendor APIs | Shared `request_with_retry` | 1 day |
| No connector-specific Prometheus metrics | Weaker ops signal | Counters around sync | 0.5 day |
| DR restore drill undocumented as executed | RTO unproven | Run restore on staging backup | 1 day |
| Benchmark report empty until operators run script | No P95 baseline | `scripts/benchmark_api.py --auth --write-report` | 1 hour |

### Low

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| OTel exporter optional | Weaker distributed traces | Set OTLP endpoint on staging | 0.5 day |

---

## Commercial journey matrix

| Step | Status |
| --- | --- |
| Signup / email verify (WorkOS) | Staging required |
| Org + Stripe checkout + webhook activate | Code ready (idempotent webhooks); live test pending |
| Invite → accept → permissions | **Pass (API CI)** |
| Salesforce sandbox OAuth → queued sync | Code ready (SSRF + queue); sandbox pending |
| CSV import → audit | **Pass (API CI)** |
| Plan upgrade / usage enforce | Flag on for Render/staging overlay; live pending |
| API token rotate | **Pass (API CI)** |
| Logout | **Pass (API CI)** |

---

## Final decision

✅ **Suitable for enterprise design partners.**

**Not** Suitable for paid commercial pilots yet.  
**Not** GA.

### Why design partners (upgrade from RC1 closed beta)?
- Critical SSRF closed with tests  
- Sync no longer blocks HTTP; Redis/worker on Compose **and** Render  
- Staging/production fail closed (WorkOS, Redis, no demo flags, no inline sync)  
- Billing webhook idempotency + tenant RLS already in place from RC1  
- Documented staging path, ops runbook, secret-gated E2E hook, benchmark harness  

### Why not paid commercial pilots?
Per release gates: complete live commercial journey, connector sandbox success, Stripe live validation, and **soak completion** are required. Those produce evidence operators must collect (`STAGING_CHECKLIST.md`, `RC2_SOAK_LOG.md`, `RC2_BENCHMARK.md`). Until that evidence exists, High residual risk remains on duration reliability and vendor integration.

### Exit criteria → paid commercial pilots
1. Staging checklist 100% checked with artifacts  
2. Soak ≥7 days with no open Critical/High incidents  
3. Stripe test-mode duplicate webhook + upgrade/cancel proven on staging  
4. One connector sandbox E2E (OAuth → queued sync → Mission Control data)  
5. Auth authenticated API P95 within advisory SLO (benchmark report attached)
