# ATLASOPS Production Readiness Roadmap

**Status:** Active hardening program  
**Audience:** Engineering leadership, design partners, investor diligence  
**Commercial bar today:** Design partners allowed (code/CI). **Paid pilots / GA: No-Go** until RC3 Part 9 evidence is green.

This document is the living prioritization plan after a full-stack audit. It does **not** authorize claiming production or GA readiness.

---

## Executive verdict

ATLASOPS has real enterprise foundations: WorkOS opaque sessions, RBAC, Fernet-encrypted credentials, connector SSRF guards, Stripe webhook hygiene, Mission Control on live APIs, fail-closed staging boot, and solid ops documentation.

It is **not** yet production-equivalent. FORCE RLS has schedule/migration gaps, several “enterprise” screens still dump JSON, UI RBAC is incomplete, and staging soak/DR/alerting evidence is missing.

**Rule for this program:** Fix trust, isolation, and demo integrity before adding features.

---

## Waves

| Wave | Theme | Outcome |
| --- | --- | --- |
| **0** | Trust foundation | ✅ Connector cron works under FORCE RLS; `0009` RLS backfill; greenfield-safe 0006–0008 |
| **1** | Demo integrity | ✅ Dashboards + Platform Ops productized; search deep-links fixed; Admin/nav role-gated |
| **2** | Session + API hardening | ✅ Sliding sessions persist; ✅ Redis-backed API rate limits (CSRF Origin check still open) |
| **3** | Commercial enforcement | Plan feature gates; invite email; document permissions |
| **4** | Enterprise UX | Copilot stream+history; Connector Studio mapping UI; consistent skeletons/empty/error |
| **5** | Investor demo pack | Believable seeded scenario; Mission Control polish; rehearsed happy path |
| **6** | Deploy maturity | Worker health, Docker CI, hard staging E2E, non-root backend |
| **7** | Ops evidence | Live staging, ≥7d soak, restore drill, on-call → Part 9 Go |

---

## P0 findings (must fix before diligence demos)

| ID | Area | Issue |
| --- | --- | --- |
| B1 | Jobs / RLS | `enqueue_due_connector_syncs` selects `Connection` before `set_session_org` → empty under FORCE RLS |
| B2 | Migrations | Additive 0006–0008 tables may lack RLS; 0002 `create_all` conflicts with later `create_table` on greenfield |
| B3 | Sessions | Sliding expiry / `last_used_at` often rolled back (no commit on read paths) |
| F1 | UI | Exec Dashboards render raw JSON |
| F2 | UI | Platform Ops dumps unstyled JSON |
| F3 | UX | Global search → `/suppliers/[id]` / `/warehouses/[id]` 404 |
| F4 | Security UX | Enterprise Admin / emergency lockout visible without UI role gate |
| O1 | Ops | No proven staging + soak/DR/alerting (RC3 blocks paid pilots) |

---

## P1 backlog (enterprise pilot)

- Redis-backed rate limiting; apply general limiter to mutating API routes
- Wire `enforce_feature()` for plan-gated surfaces when `FEATURE_BILLING_ENFORCE=true`
- Send org invites via Resend (not invite URL in JSON only)
- Use `documents.read` / `documents.manage` (not `org.read` / `org.update`)
- Sanitize `/health/ready` error detail (no exception strings)
- AI Copilot: SSE streaming + persisted conversation history
- Connector Studio: table-based field mapping (retire JSON textarea as primary UX)
- Filter sidebar by role; gate mutations (incidents, workflows, predictions)
- Analytics `ErrorState` + adopt unused `TableSkeleton` patterns
- Sidebar “Live data feed” must reflect real connectivity

---

## P2 / P3 (maturity)

Workflow cron precision, virus-scan honesty, soft deletes, unique `token_hash`, dead JWT helpers, hierarchy models without APIs, Docker CI builds, backend non-root image, `npm ci` in frontend Dockerfile, docs drift (S3, `SEED_ON_STARTUP`, METRICS_TOKEN).

---

## Explicit non-goals

- No Celery migration (ARQ stays)
- No JWT auth rewrite (opaque httpOnly cookies stay)
- No Next.js major upgrade mid-hardening
- No new ERP connectors until Wave 0–1 are green
- No paid-pilot / GA claims until Wave 7 evidence exists

---

## Investor demo path (until Wave 1)

**Show:** Mission Control → Alerts → Risk → Shipments → Network → Advisor (short) → Data Sources / Connectors  

**Hide or skip:** Exec Dashboards, Platform Ops, Connector Studio JSON detail, Enterprise Admin lockout (unless admin role + rehearsed)

Enable `NEXT_PUBLIC_DEMO_SANDBOX=true` only on a dedicated demo environment — never on shared staging with real tenant data.

---

## Working method

1. Explain why the change is necessary and trade-offs.
2. Implement production quality (no TODOs, no placeholders, no hardcoded fake success).
3. Test the change.
4. Refactor only what the wave requires.
5. Never break existing tenant isolation or auth.

Companion certification: [`docs/reports/RC3_COMMERCIAL_PILOT_CERTIFICATION.md`](reports/RC3_COMMERCIAL_PILOT_CERTIFICATION.md)  
Ops Go/No-Go: [`docs/OPERATIONS_MANUAL.md`](OPERATIONS_MANUAL.md) Part 9
