# Recovery Engine verification

Release verdict remains **FAIL / NOT READY**. This document covers isolated synthetic local verification, not hosted acceptance. No deployment or production migration was performed.

## Final complete run — October 11, 2026

Run **20261011T100228Z-f5c7b7**, completed **2026-10-11 10:10:42 UTC** (05:10:42 America/Chicago).
Command: `backend/.venv/bin/python tools/qa/health.py --postgres`.

| Total | PASS | FAIL | BLOCKED | SKIPPED |
| --- | --- | --- | --- | --- |
| 893 | 864 | 0 | 4 | 25 |

- SQLite backend: 407 passed, 25 skipped.
- Disposable PostgreSQL backend: 432 passed, including fresh migration 0018 and Recovery RLS.
- Browser: 13 passed; AI-001, AI-003, AI-004 and RECOVERY-001 all PASS.
- All 25 SQLite-only skips have matching passing PostgreSQL cases, confirmed by XML comparison.
- Baseline `20261010T143131Z-f4fb01` had 822 entries / 794 passed / 0 failed / 4 blocked / 24 skipped. Every baseline ID remains present; no previously passing result regressed. Additions: 70 backend entries (35 per database) and one browser case; 70 additional passes and one SQLite-only skip.
- Runner exit 1 is expected: four unresolved prerequisites keep **FAIL / NOT READY**. No release assertion was weakened.

Complete retained evidence: `.local/qa/runs/20261011T100228Z-f5c7b7/report.json`, `report.md`, `regression.xml`, `postgres.xml`, `browser.json`, `scenarios.json`, `RECOVERY-desktop.png` and `RECOVERY-mobile.png`. Private fixture credentials are excluded from reports and must not be shared.

## Changes

New files:
- `backend/app/models/recovery.py`
- `backend/alembic/versions/0018_recovery_engine.py`
- `backend/app/services/recovery/contracts.py`
- `backend/app/services/recovery/engine.py`
- `backend/app/services/recovery/store.py`
- `backend/app/services/recovery/copilot.py`
- `backend/app/api/routers/recovery.py`
- `backend/tests/test_recovery_engine.py`
- `frontend/app/(app)/recovery/page.tsx`
- `frontend/qa/recovery.spec.ts`
- `tools/recovery/demo.py`
- `frontend/public/recovery-demo/{products,warehouses,inventory,stock,requirement,inbound,rule}.csv`
- `frontend/public/recovery-demo/README.txt`
- `docs/recovery/IMPLEMENTATION.md`
- This verification document.

Modified files:
- `backend/app/models/__init__.py`, `backend/app/models/models.py`: register tenant-owned tables.
- `backend/app/rbac/permissions.py`: scoped read/manage/approve permissions.
- `backend/app/api/router.py`: register routes.
- `backend/app/services/ai_advisor.py`, `backend/app/services/ai_orchestration.py`: shared deterministic recovery answers.
- `frontend/lib/constants.ts`, `frontend/components/layout/sidebar.tsx`: visible module navigation.
- `frontend/qa/playwright.config.ts`: additive browser test discovery.
- `tools/qa/scenarios.py`: wait for the real shared upload-rate window before the subsequent API phase. Limits and assertions remain unchanged; no 429 is treated as success.

## Evidence scope

Recovery regression coverage includes CSV/XLSX imports, transaction rejection/retry, missing versus zero quantities, stale/conflicting/duplicate data, quarantine/reservations, dated and unconfirmed inbound, shared allocation, donor shortage, authorized substitutions and repair rules, stale approval rejection, audit corrections, existing incident linkage, permission denial, tenant isolation and direct PostgreSQL RLS. Original advisor SKU/delivery regressions remain intact.

Focused recovery plus original advisor regression run: **64 passed, 1 skipped**. The skipped direct RLS test requires PostgreSQL and must pass in the full PostgreSQL phase.

Frontend TypeScript, ESLint and optimized production build: **PASS**. QA gate self-tests: **12 passed, 3 subtests passed**; missing evidence still fails closed.

The additive browser case imports synthetic data through existing and new import paths, compares donor transfer versus expedite, proposes/approves an action, corrects source evidence with an audit reason, records an outcome, advances the linked incident lifecycle and checks refresh persistence. Screenshots and mobile overflow checks are automated evidence, not human approval.

## Intermediate run retained

`20261010T185301Z-9858cf`: **879 entries: 849 PASS, 2 FAIL, 4 BLOCKED, 24 SKIPPED**. Recovery browser and initial PostgreSQL regressions passed. IMPORT-003 and SHIP-001 failed with HTTP 429 because the added browser imports consumed the same loopback IP upload budget immediately before API scenarios. The follow-up run retains those assertions and allows the real rate window to expire. This earlier report remains on disk.

`20261011T015605Z-ce6509`: **893 entries: 863 PASS, 1 FAIL, 4 BLOCKED, 25 SKIPPED**. PostgreSQL: 432 passed; SQLite: 407 passed, 25 skipped; browser: 12 passed, AI-004 failed during dashboard login/loading before the adversarial request. API logs show a roughly 15-minute gap (02:02–02:17 UTC) and the browser case reports 905,025 ms despite its 90-second timeout. This is consistent with a local execution pause, but the cause is not established. No assertion or timeout was changed. The two prior import-rate failures passed after phase pacing. The failed report is retained; a fresh full run is required.

## Demonstration

Open Critical spares readiness, then Import. Follow `frontend/public/recovery-demo/README.txt`; import products, warehouses and inventory through the existing importer first. The synthetic scenario has Plant A short three units, Plant B stock ten with demand nine, and an authorized expedite alternative. The transfer must expose donor shortage. Proposing/approving a case never mutates physical stock or external purchase orders. Source corrections are separate audited human actions.

## Remaining release blockers

- **HOST-001 — BLOCKED:** verified staging project, URL, deployed revision/build and synthetic organizations are unavailable.
- **SSO-001 — BLOCKED:** real WorkOS staging login, invitation, roles and session lifecycle remain unverified.
- **AI-LIVE-001 — BLOCKED:** no authorized staging provider execution evidence. Recovery answers are deterministic; this does not prove external-model safety.
- **VISUAL-REVIEW-001 — BLOCKED:** no explicit human approval of an exact hosted revision on desktop/mobile.

See IMPLEMENTATION.md for conservative evidence rules and limitations: source records do not certify physical stock; approval does not reserve inventory or execute ERP actions; simultaneous approved proposals require revalidation; estimates are not guaranteed outcomes. No unrestricted enterprise-readiness claim is supported.
