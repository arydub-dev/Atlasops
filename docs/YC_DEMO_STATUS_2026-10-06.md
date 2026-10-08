# YC demo implementation and admission status

This is not a hosted-demo completion certificate. The new changes are local; deployment and a clean-browser walkthrough have not been verified.

Implemented: an operator-provisioned fictional organization with 240 products and current inventory positions, four warehouses, four suppliers, 40 shipments, 12 sales orders, three incidents, and unconfigured SAP Business One/Salesforce connections. Ordinary authentication, tenant permissions, models, calculations and APIs are retained. No login bypass or fake connector success is added.

The seed includes HP-240 at 42 units against a 100-unit reorder threshold and a 292-unit target, a delayed inbound shipment, zero-stock positions, overstock and incident workflows. Supplier scores are synthetic scenario inputs; no customer savings or forecasting accuracy has been established. Local AI retrieval now includes priority inventory positions and related at-risk shipments; it describes stock coverage rather than claiming demonstrated prediction accuracy.

Daily-workflow changes include shipment ETA updates, inventory-to-warehouse total reconciliation, incident assignment to the current operator, investigation/mitigation transitions, permission checks, progress history, and resolution. The reset control is disabled unless its exact organization is allowlisted by the operator and additionally requires demo ownership/admin access. CSV and XLSX imports are in `docs/yc-demo-imports` with instructions on create versus update semantics.

## Remaining admission requirements

| Requirement | State |
|---|---|
| Local seed/import/AI/reset and incident code | Implemented; automated verification recorded below |
| Dedicated hosted owner, operations and viewer logins | BLOCKED: dedicated verified identity and hosted setup needed |
| Hosted organization populated | NOT DONE |
| Latest changes pushed/deployed | NOT DONE; current directory has no Git metadata and previously checked CLI authentication was invalid |
| Hosted Redis and durable worker | FAIL at last live check: readiness 503 `not_ready:redis`; worker not independently verified |
| Clean-browser complete demonstration | NOT RUN |
| Hosted persistence and isolation acceptance | NOT RUN |
| External SAP/Salesforce integration | Credentials unavailable; deliberately unconnected |
| Dependency security gate | Outstanding npm audit findings; no bypass applied |
| Customer ROI or enterprise production certification | Not established |

Private login/provisioning and presentation instructions are stored in ignored `.local/YC_DEMO_RUNBOOK.md`. No credentials are included in the public kit. Deployment alone does not satisfy these acceptance criteria.

## Verification performed locally

- PostgreSQL with a restricted application role and Redis: **352 passed**, no skips; one existing Starlette deprecation warning. Includes the migration-backed RLS and queue tests. Isolated test services only, not hosted production.
- SQLite full suite: **333 passed, 19 skipped** (PostgreSQL/Redis-specific cases), same deprecation warning.
- Final seed relationship and supplier-aware AI changes: **22 focused tests passed** on both SQLite and isolated PostgreSQL/Redis.
- Frontend typecheck, ESLint and optimized Next.js production build: passed, 60 static pages generated.
- All seven workbook worksheets parsed and validated by the actual import implementation; spreadsheet previews inspected and date formatting corrected before export.
- Public readiness recheck on October 6: **HTTP 503, `not_ready:redis`**. No authenticated browser acceptance run was performed.

Test fixtures provide authenticated local sessions; these results do not prove hosted WorkOS login, invitations, email delivery or customer permissions end to end. The isolation fixture includes another company's zero-stock position and verifies that its SKU and name are absent from demo AI context. Reset tests verify exact organization allowlisting and reject viewer access.
