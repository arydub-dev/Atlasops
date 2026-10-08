# AtlasOps YC-focused MVP — October 8, 2026

Status: the core operational loop is implemented and locally tested. Hosted acceptance is NOT complete. This report does not certify enterprise readiness or customer traction.

## Product

AtlasOps turns supply-chain exports into a prioritized list of problems and recommended actions for operations teams. It complements an ERP; it does not replace procurement, accounting or warehouse execution.

## Core workflow

Import CSV/Excel → detect current shortages, excess stock and shipment risks → inspect evidence → review a transparent recommendation → create or reopen an existing active incident → assign to yourself, record progress notes and resolve → refresh operational data.

The landing page now presents operational priorities ahead of charts. Ranking uses severity then recorded days of stock coverage. Shortages and overstock are inventory positions, not distinct SKUs across warehouses. Resolving a task does not remove a physical shortage until the data changes. A resolved incident can be followed by a new incident if the underlying problem persists.

## Working features and evidence

- Current inventory, product and warehouse joins; shipment links resolved through organization-scoped SKU, warehouse name and supplier name during imports. Missing or ambiguous links are rejected. Blank update cells preserve current relationships.
- Priority detail pages distinguish stored quantities, calculated coverage, rule-based replenishment, related shipments and recommendations. Missing fields are shown as unavailable. Shipment association does not establish causation.
- Source-row locking reuses existing active incidents for the same priority on PostgreSQL. Incidents include related entities, severity, current operator assignment, progress notes, investigation/mitigation and resolution.
- Advisor context includes the same operational priorities; SKU-specific questions use matching inventory data. Responses do not claim external actions occurred.
- Core navigation foregrounds priorities, inventory, suppliers, warehouses, shipments, incidents, imports and advisor. Other tools remain accessible through Show all tools.
- Restricted `demo_operator` permission set allows imports, AI and incident workflows only for the allowlisted fictional workspace; no administrative reset, security management or connector writes. Existing viewer accounts remain read-only. The local shared account has been changed to this operator role; credentials remain in the private ignored file.
- Recommendation views and priority-to-incident actions create audit events. Authorized operators can query `/api/v1/priorities/usage/summary` for scoped stored counts: imports, accepted rows, created/resolved incidents, stored AI reports, recommendation views and distinct viewers. These are activity events, not proof of customer ROI. Synthetic workspaces are labelled; seeded records are included in historical totals. General return-user retention analytics are not yet implemented.
- Automated full SQLite suite: **342 passed, 19 skipped**, one existing deprecation warning. The skipped tests require PostgreSQL/Redis. Frontend typecheck, lint and optimized build passed. Focused checks were repeated after final advisor/relationship changes.
- Running local API: login 200, priority feed 200, advisor 200, import schema 200, logout followed by authenticated request 401. Seeded counts: 7 critical, 21 low-stock positions, 1 overstock, 4 shipment risks, 2 open incidents. HP-240 recommendation 250, two active inbound links. These are fictional scenario results, not customer traction.

## Five-minute demonstration

1. Open `/demo-login` and use the private credentials. Credentials are not displayed on the website.
2. Open Operational priorities. Explain the source data and severity/coverage ranking.
3. Find HP-240, open its evidence page and inspect 42 units, threshold 100, target 292 and related shipments.
4. Explain the 250-unit rule-based suggestion; incoming stock and reservations are not subtracted automatically.
5. In Advisor, ask “Why is HP-240 at risk?” and “What should we address first?”
6. Return to the priority. Create/open the related incident, assign it to yourself, start investigation, save a note and resolve it. The stock problem correctly remains.
7. Import `inventory_refresh.csv` from the existing synthetic kit. Verify 80 units and recommendation 212, then import it again and verify unchanged outcome.
8. Refresh, log out and sign in again. Verify records persist. Use an unrelated account to verify organization isolation before presenting to outside users.

## First customer pilot

Start with a supervised CSV/Excel pilot in a separate organization using a named operations account. Import warehouses/products first, then inventory and linked shipments. Supplier names and warehouse names must be unambiguous; product SKUs and shipment references must be stable. Review rejected rows and source counts with the customer. Collect feedback on whether detected problems are important and whether the recommended actions are useful. Track actual incidents resolved, returning usage and attributable outcomes before expanding scope or making savings claims.

## Limitations and next milestones

Hosted private access, environment configuration and clean-browser persistence acceptance still need completion. Existing Redis/worker readiness and dependency-security failures remain deployment blockers; this work does not bypass them. No SAP or Salesforce sandbox has been validated, and neither is required for the file-based MVP. Order-line ingestion/reconciliation is outside this workflow. Shared demo accounts cannot attribute activity to individual visitors; named accounts are needed for pilot evidence. Current priority computation scans the organization's current records and requires workload testing before large imports. No live customer pilot, measured savings, forecasting accuracy or funding outcome has been demonstrated.

Next: complete hosted acceptance, observe the first operator performing the loop without coaching, record where they struggle, improve mappings/ranking based on real datasets, and then measure repeat usage and operational value. Do not declare the MVP complete until the hosted acceptance sequence succeeds without developer assistance.
