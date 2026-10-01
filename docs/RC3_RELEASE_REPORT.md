# ATLASOPS RC3 Release Validation Report

**Validation date:** 2026-08-12 (UTC)  
**Validator:** automated evidence run on engineer workstation  
**Method:** live proofs where possible; **PASS / FAIL / NOT TESTED** only  

**Environment facts at validation time:**

| Fact | Evidence |
| --- | --- |
| Docker Desktop daemon | **Unavailable** — `docker.sock` missing; `/Applications/Docker.app` failed to open (`kLSNoExecutableErr`) |
| `.env` / WorkOS / Stripe / Sentry secrets | **Absent** — no `.env`; `WORKOS_API_KEY`, `STRIPE_SECRET_KEY`, `SENTRY_DSN` unset |
| `docker-compose.prod.yml` | **Cannot interpolate** without secrets (`NEXT_PUBLIC_API_URL` / WorkOS / `SESSION_SECRET` required) |
| Homebrew PostgreSQL 16 | **Available** — `localhost:5432` accepting connections |
| Redis | **Unavailable** — `redis-cli` not installed; no Redis process used |
| Local API/frontend | **Down** — `localhost:8000` / `:3000` returned connection failure |

**Decision up front:** **LOCAL DEMO READY** (unchanged). Not design-partner ready.

---

## Gate results (PASS / FAIL / NOT TESTED)

### GATE 1 — Staging infrastructure — **NOT TESTED**

| Check | Result |
| --- | --- |
| Postgres + Redis + API + worker + frontend via `docker-compose.prod.yml` | **NOT TESTED** |
| `/health/live` + `/health/ready` on staging | **NOT TESTED** |
| Worker processing jobs | **NOT TESTED** |

**Why:** Docker daemon not running/broken; required secrets not supplied; compose config fails interpolation:

```text
error while interpolating services.frontend.build.args.NEXT_PUBLIC_API_URL:
required variable NEXT_PUBLIC_API_URL is missing
```

**Severity:** Release-blocking for design partner.  
**Next action:** Repair/start Docker Desktop (or use Render/`render.yaml`), create gitignored `.env` with real secrets, then:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
curl -fsS https://<host>/health/live
curl -fsS https://<host>/health/ready
```

---

### GATE 2 — Database (Alembic + RLS) — **PASS**

| Check | Result | Evidence |
| --- | --- | --- |
| Empty Postgres → `alembic upgrade head` | **PASS** | DB `atlasops_rc3_empty`; started `2026-08-12T05:16:22Z`; head `0011_alert_sim_enums` |
| No `create_all()` for prod schema | **PASS** | `ALLOW_CREATE_ALL_ON_STARTUP=false`; Alembic-only path used |
| RLS enabled where expected | **PASS** | `rls_on=36` |
| FORCE RLS where expected | **PASS** | `force_on=36` |
| `tenant_isolation` policies | **PASS** | `policies=36` |
| Functional: no GUC → 0 rows | **PASS** | `pytest tests/test_rls.py` → **2 passed** (`2026-08-12T05:16:48Z` window) |

Commands:

```bash
DATABASE_URL=postgresql+psycopg://atlasops_rc3:***@localhost:5432/atlasops_rc3_empty \
  alembic upgrade head
# → 0011_alert_sim_enums (head)

SUPPLY_CI_POSTGRES=1 DATABASE_URL=... pytest -q tests/test_rls.py
# → 2 passed
```

**Product fix applied during validation (required for Postgres):**  
`create_organization()` now calls `set_session_org(db, org.id)` before inserting `billing_accounts` (FORCE RLS otherwise blocks org creation).

---

### GATE 3 — WorkOS — **NOT TESTED**

No WorkOS API key / client ID / HTTPS callback host. Browser AuthKit flow not executed. Dev-login production denial not exercised on a production boot.

**Severity:** Release-blocking for design partner.  
**Next action:** Configure WorkOS test project + public HTTPS redirect; capture screenshot of landing → AuthKit → session cookie (`HttpOnly`, `Secure`, `SameSite`).

---

### GATE 4 — Tenant isolation — **PASS** (fixed 2026-08-12)

| Check | Result | Evidence |
| --- | --- | --- |
| API isolation (SQLite TestClient) | **PASS** | `pytest tests/test_tenant_isolation.py` |
| Spoofed `X-Organization-Id` | **PASS** | Covered in tenant + postgres API suites |
| Postgres RLS policy presence / FORCE | **PASS** | Gate 2 |
| Postgres RLS blocks unscoped reads | **PASS** | `test_rls_blocks_without_guc` |
| Postgres API list under FORCE RLS | **PASS** | Auth `commit()` cleared `SET LOCAL`; fixed via `session.info` + `after_begin` rebind. `SUPPLY_CI_POSTGRES=1 pytest tests/test_tenant_isolation.py tests/test_rls.py tests/test_postgres_api_rls.py` → **12 passed** |

**Root cause:** `set_session_org` used transaction-local GUC; `_persist_auth_activity` committed mid-request and cleared it before the ORM query.

**Fix:** store org on `session.info`; re-apply GUC on SQLAlchemy `after_begin`; re-bind in `get_db_with_tenant`.

---

### GATE 5 — Stripe test mode — **NOT TESTED** (live); FORCE RLS architecture **PASS**

No live `STRIPE_SECRET_KEY` / webhook endpoint in this environment.

**Architecture fix (2026-08-12):**

| Check | Result | Evidence |
| --- | --- | --- |
| App role has no BYPASSRLS | **PASS** | `test_app_role_cannot_disable_row_security` |
| Customer lookup with empty GUC | **PASS** | `app_lookup_org_by_stripe_customer` → `stripe_customer_index` (no RLS) |
| `invoice.paid` entitlement update | **PASS** | `tests/test_stripe_force_rls.py` |
| Duplicate webhook idempotent | **PASS** | same |
| Unknown customer no mutation | **PASS** | same |
| Signature verification | **PASS** | `construct_event` rejects missing/invalid sig |
| Suite under FORCE RLS | **PASS** | `SUPPLY_CI_POSTGRES=1 pytest tests/test_stripe_force_rls.py tests/test_stripe_webhooks.py tests/test_billing_authz.py` → **30 passed** |

**Privileged boundary:** non-RLS `stripe_customer_index` + narrow SECURITY DEFINER lookup (customer_id → organization_id only). No `SET LOCAL row_security = off`. No app-role BYPASSRLS.

Live Checkout/Portal/webhook delivery against Stripe test mode remains **NOT TESTED**.

---

### GATE 6 — Connector E2E — **NOT TESTED**

No connector sandbox credentials; Redis/worker stack not running.

---

### GATE 7 — Core business workflow — **NOT TESTED**

`force-disruption` / Mission Control / Copilot / simulation not executed against a running staging API (services down).

---

### GATE 8 — Sentry — **NOT TESTED**

`SENTRY_DSN` unset; no controlled error events observed in a Sentry project.

---

### GATE 9 — Backup / restore — **PASS** (with required ops constraint)

| Check | Result | Evidence |
| --- | --- | --- |
| `pg_dump` as **app role** (`atlasops_rc3`) | **FAIL** | `query would be affected by row-level security policy for table "ai_reports"` |
| `pg_dump` as **postgres superuser** | **PASS** | dump `docs`-adjacent path `.run/rc3_backup_superuser_20260812T051625Z.sql` (**112270** bytes) |
| Restore into empty DB | **PASS** | `RESTORE_START=2026-08-12T05:16:26Z` / `RESTORE_END=2026-08-12T05:16:26Z` |
| `alembic upgrade head` on restore DB | **PASS** | still `0011_alert_sim_enums` |
| Tenant rows intact | **PASS** | org `RC3 Backup Org`, user `rc3-backup@example.com`, warehouse `WH-RC3`, supplier `Supplier RC3`, shipment `SHP-RC3-1` |

**RPO assumption (this drill):** logical dump at backup timestamp; no WAL continuous archive tested.  
**RTO result (this drill):** restore + grants + alembic ≈ **1 second** on local Homebrew Postgres (not representative of managed cloud RTO).

**Ops requirement:** backups **must** use a `BYPASSRLS` or superuser role. App-role dumps are incompatible with FORCE RLS.

---

### GATE 10 — Soak / load — **NOT TESTED**

No 100 / 1k / 10k seed on staging; k6 scripts under `load/k6/` not executed against a live stack.

---

### GATE 11 — Security (automated) — **PASS** (staging live hardening **NOT TESTED**)

| Check | Result | Evidence |
| --- | --- | --- |
| CSRF Origin allowlist | **PASS** | `tests/test_csrf.py` in SQLite suite |
| SSRF URL rejection | **PASS** | `tests/test_ssrf.py` |
| Startup fail-closed | **PASS** | `tests/test_startup_checks.py` |
| Credential encryption helpers | **PASS** | `tests/test_connector_credentials.py` |
| Billing authz / RBAC / auth guards | **PASS** | included in **74 passed** SQLite evidence run |
| Live staging headers / HTTPS cookies / no stack traces on prod errors | **NOT TESTED** | no staging host |

---

### GATE 12 — Release report — **PASS**

This document + `docs/RELEASE_CHECKLIST.md` updated with explicit statuses and evidence.

---

## RC3 PASS RATE

| Status | Gates | Count |
| --- | --- | --- |
| **PASS** | 2, 4, 9, 11, 12 | **5** |
| **FAIL** | — | **0** |
| **NOT TESTED** | 1, 3, 5, 6, 7, 8, 10 | **7** |
| **Total gates** | 1–12 | **12** |

**RC3 PASS RATE = 5 / 12 = 42%**

(Gate 4 Postgres API isolation fixed 2026-08-12. Design partner still blocked by Gates 1 + 3 NOT TESTED.)

---

## Final decision

# LOCAL DEMO READY

| Stage | Classification | Reason |
| --- | --- | --- |
| Local demo | **LOCAL DEMO READY** | Prior demo path + SQLite suites green |
| Design partner | **NOT READY** | Gates 1 + 3 **NOT TESTED** (WorkOS + staging stack) |
| Paid pilot | **NOT READY** | Stripe/connector/Sentry/soak/live billing unproven |
| General production | **NOT READY** | Requires paid-pilot evidence |

---

## Exact remaining blockers (ordered)

1. Start a working container runtime + supply gitignored production secrets  
2. Boot `docker-compose.prod.yml` and prove `/health/live` + `/health/ready` + ARQ worker  
3. Complete real WorkOS AuthKit browser login on HTTPS  
4. Fix Postgres API tenant list under FORCE RLS; re-run isolation suite green  
5. Stripe test-mode checkout + signed webhooks (FORCE RLS lookup architecture fixed)  
6. One connector sandbox sync via Redis/ARQ  
7. `force-disruption` workflow on staging data  
8. Real Sentry DSN events from API + worker  
9. Document backup role as BYPASSRLS/superuser in runbooks (proven necessary)  
10. Soak/load against staging volumes  

---

## Code changes made during this validation (minimal, evidence-driven)

| Change | Why |
| --- | --- |
| `create_organization` → `set_session_org` before billing insert | Org creation violated FORCE RLS on Postgres |
| Postgres test fixtures set GUC / refresh after commit | Enable RLS pytest execution |
| Stripe unit tests set GUC when reading billing rows | FORCE RLS visibility |

No product redesign. No mocked WorkOS/Stripe/Sentry “success.”
