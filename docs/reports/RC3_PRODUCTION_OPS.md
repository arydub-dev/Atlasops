# Production Operations Report — Supply v2 RC3

**Date:** 2026-07-25  
**Role:** SRE / DevOps / Release Manager validation  
**Prior:** RC2 design-partner ready — [`RC2_RELEASE_READINESS.md`](./RC2_RELEASE_READINESS.md)

---

## Evidence gathered this cycle

| Check | Result |
| --- | --- |
| Code/config audit (compose, staging overlay, Render, startup checks) | Done |
| Docker Compose staging bring-up | **Blocked** — Docker daemon unavailable in validation host (`DOCKER_UNAVAILABLE`) |
| Live WorkOS / Stripe test / connector sandboxes | **Blocked** — no credentials in environment |
| 7–14 day soak | **Not started** — tooling ready (`scripts/soak_snapshot.py`) |
| DB restore drill | **Not executed** — script ready (`scripts/restore_drill.sh`); log open |
| Automated tests after ops fixes | **76 passed**, 2 skipped |

---

## Scores (0–10)

| Dimension | Score | Evidence |
| --- | --- | --- |
| Architecture | 8.5 | Unchanged multi-tenant + worker; Render migrate command fixed |
| Infrastructure | 6.5 | Blueprints sound; **live deploy not proven here** |
| Security | 8.5 | Staging metrics gated; billing enforce required in prod; Redis in readiness |
| Reliability | 6 | Queue path hardened; soak/DR unproven |
| Performance | 6 | Harness exists; no staging P95 captured this cycle |
| Observability | 7 | HTTP + connector + Stripe metrics; Grafana/alerts operator-owned |
| Operations | 7 | ENV matrix, monitoring, incident, restore script documented |
| Developer Experience | 7.5 | Staging overlay requires `METRICS_TOKEN` |
| Commercial Readiness | 6.5 | Design partners OK; paid pilots blocked on live gates |
| Operational Readiness | 6 | Procedures exist; execution evidence missing |

---

## Ops fixes landed in RC3 (verified risks only)

| ID | Severity | Fix |
| --- | --- | --- |
| H-RENDER-MIGRATE | High | Render API `dockerCommand`: `alembic upgrade head && uvicorn …` |
| H-REDIS-READY | High | `/health/ready` PINGs Redis when queue sync required |
| H-METRICS-STAGING | High | `METRICS_TOKEN` required for staging+prod; `/metrics` gated on `requires_secure_boot` |
| H-BILLING-ENFORCE | High | Production boot refuses `FEATURE_BILLING_ENFORCE=false` |
| M-TRUST-PROXY | Medium | `TRUST_PROXY=true` on Render API |
| M-WORKER-BOOT | Medium | Worker runs `assert_safe_to_boot(role=worker)` |
| M-HEALTHCHECK | Medium | Dockerfile HEALTHCHECK → `/health/ready` |
| M-METRICS-DOMAIN | Medium | Connector enqueue/sync + Stripe webhook Prometheus counters |
| M-CRYPTO | Medium | Encryption key refuse uses `requires_secure_boot` |
| M-UNKNOWN-ENV | Medium | Non-dev/test environments fail closed (typos included) |

---

## Remaining issues

### Critical
*None identified in code after RC3 fixes.*

### High — **block paid commercial pilots**

| Description | Business impact | Technical impact | Recommended fix | Effort |
| --- | --- | --- | --- | --- |
| Staging not deployed/proven in this validation (Docker unavailable) | Cannot certify production-like runtime | Startup/restart/queue unproven live | Deploy via `docker-compose.staging.yml` or Render; attach evidence | 1–2 days |
| WorkOS + Stripe test + connector sandbox journey not executed | Revenue/auth/integration risk unknown | Commercial path unproven | Complete `docs/STAGING_CHECKLIST.md` with screenshots/logs | 3–5 days |
| 7–14 day soak not run | Duration failures unknown | Memory/queue/leak risk | Cron `soak_snapshot.py`; fill soak log | 7–14 days |
| Restore drill not executed | RPO/RTO contractual risk | DR unproven | Run `scripts/restore_drill.sh`; record `RC3_RESTORE_DRILL.md` | 0.5–1 day |
| Alerting not wired to a live scraper/pager | Incidents may go unseen | No paging path in-repo | Apply `docs/MONITORING.md` rules to Prometheus/Grafana | 1 day |

### Medium

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| Worker does not expose its own `/metrics` | Sync duration only via API process if shared; worker-local jobs need log correlation | Sidecar or pushgateway optional | 1 day |
| OTel exporter optional / unset | Weaker distributed traces | Set OTLP on staging | 0.5 day |
| Object storage not implemented | N/A today (uploads in-process) | Do not claim S3 until built | — |

### Low

| Description | Impact | Fix | Effort |
| --- | --- | --- | --- |
| Compose default still uses insecure session for local | Dev only | Keep; never use base compose alone for prod | — |

---

## Commercial journey gates (explicit)

| Workflow | Status this cycle |
| --- | --- |
| Registration / email verify (WorkOS) | **Gate: credentials** |
| Checkout + webhook + plan activate | **Gate: Stripe test + staging URL** |
| Invite / RBAC / CSV / tokens / logout | Proven in API CI (prior RC) |
| Salesforce OAuth + queued sync | **Gate: sandbox + worker live** |
| Billing upgrade/downgrade/cancel | **Gate: Stripe test** |
| Soak / DR restore | **Gate: execution** |

---

## Final decision

⚠ **Suitable for enterprise design partners.**

**Not** Suitable for paid commercial pilots.  
**Not** GA.

### Why not paid pilots (required honesty)

Paid-pilot criteria demand **proven** staging deployment, commercial journey, soak, and DR. This RC3 cycle:

- Closed verifiable High **code/config** operational risks (migrate, Redis readiness, metrics gating, billing enforce).  
- Could **not** prove live infrastructure (Docker unavailable; no WorkOS/Stripe/connector secrets).  
- Therefore operational validation remains **incomplete**, not successful.

### Exit criteria → ✅ paid commercial pilots

1. Staging deploy evidence (ready checks green; worker consuming jobs)  
2. Checklist 100% with WorkOS + Stripe test + one connector  
3. Soak ≥7 days with `soak_samples.jsonl` and no open High incidents  
4. Restore drill **Pass** in `RC3_RESTORE_DRILL.md`  
5. Live Prometheus alerts firing to an on-call channel  

---

## Operator quick links

- [`docs/ENV_MATRIX.md`](../ENV_MATRIX.md)  
- [`docs/STAGING.md`](../STAGING.md) / [`docs/STAGING_CHECKLIST.md`](../STAGING_CHECKLIST.md)  
- [`docs/MONITORING.md`](../MONITORING.md)  
- [`docs/INCIDENT_RESPONSE.md`](../INCIDENT_RESPONSE.md)  
- [`docs/OPERATIONS.md`](../OPERATIONS.md)  
- [`docs/DISASTER_RECOVERY.md`](../DISASTER_RECOVERY.md)  
