# Critical Spares Readiness — implementation and evidence boundaries

## Architecture reviewed and reused

AtlasOps uses FastAPI/SQLAlchemy/Alembic, tenant-scoped database sessions and PostgreSQL
FORCE RLS, an existing validated CSV/XLSX parser and inventory importer, permission-based
API dependencies, an append-only audit helper, and Next.js with the existing API client,
sidebar and component styles. Incidents already support assignment, investigation,
mitigation and resolution. The advisor has deterministic inventory/delivery evidence paths.

The implementation is additive: existing products, warehouse/site names and current
inventory positions remain authoritative operational records. New typed source records
represent maintenance requirements, stock evidence (reservations/usability/source count),
PO lines, authorized action rules and one optional allocation policy. Stock evidence does
not silently replace inventory quantities. A mismatch creates an UNKNOWN result.

Two new tenant-owned relational tables hold versioned-by-audit source records and recovery
cases. Typed JSON payloads are validated before persistence; source identity is unique per
organization and record kind. Relationships are resolved by exact SKU and site identifiers,
or a fresh explicitly authorized alias. No description-based merges or graph database.
Unmatched and ambiguous inputs remain visible as data-quality issues.

## Migration

`0018_recovery_engine` follows `0017_sap_business_one`, adds `recovery_records` and
`recovery_cases`, their organization indexes and uniqueness, and FORCE RLS policies.
It does not rewrite existing inventory, shipment, purchase-order or incident rows.
It accounts for legacy bootstrap migrations that create current metadata on fresh databases.
Its frozen schema definitions do not import future ORM table definitions.

Downgrade drops the new module tables and would destroy recovery history; it must not be
run against a populated environment without an explicit retention/backup decision.
Hosted migration/rollback acceptance is not established by a disposable local migration.
No production migration was run.

## Contracts and import workflow

1. Use the established products, warehouses and inventory CSV/XLSX importer.
2. Use `/recovery/import/{kind}` for `stock`, `requirement`, `inbound`, `rule`, or `policy`.
3. Use `GET /recovery/contracts` for exact field contracts. Blank numeric fields remain null,
   never zero. Date/timestamps require an explicit timezone and normalize to UTC.
4. All rows validate before writing. Imports are bounded to 5,000 rows/15 MB. Duplicate
   source IDs in one file are rejected. Identical retries are no-ops; changed records require
   the review/correction endpoint with original values, correction and a reason.
5. Corrections use an optimistic original-value check plus row locking. Audit entries preserve
   original/corrected values, actor and timestamp. No source identity rewrite is permitted.

The recovery import does not initiate ERP synchronization. Existing purchase-order headers
are not sufficient to establish material availability, so only explicit imported PO-line
quantities enter the allocator. A shipment reference is retained as provenance; it is not
counted again as separate inbound supply. Source evidence remains a recorded claim,
not an independent verification of physical stock or supplier performance.

## Deterministic allocation and uncertainty

All active requirements share one allocation ledger. Ordering is required date, priority
(1 highest), work-order ID, source ID. Available stock is usable recorded stock minus
explicit reservations; reservations are treated as unavailable global commitments and are
not silently added back for a particular work order. Each stock/inbound unit is consumed once.

Confirmed, fresh, dated inbound with supplier/date-source evidence is counted only when
expected by the requirement deadline and not already overdue/unreceived. Unconfirmed or
missing dates never become guaranteed supply. Missing essential identifiers, quantities,
stock positions or contradictory counts produce UNKNOWN. Staleness produces AT RISK.
A supported quantity deficit produces SHORTAGE; only supported coverage produces READY.
Past deadlines cannot establish historical readiness from a current snapshot.

The optional policy configures source freshness and arrival/known-cost ranking. Multiple
policies conflict and block reliable readiness. Cost ranking requires complete comparable
currency/cost inputs for feasible options; otherwise arrival and stable IDs order results.
No calibrated confidence score, downtime prediction, savings or cheapest claim is invented.

## Recovery scenarios and human workflow

Transfer/substitution checks reserve all imported donor demand before exposing surplus.
Unsafe donor transfers are rejected and still show the counterfactual donor shortage.
Expediting advances an existing supported PO line rather than adding duplicate inbound.
Repair options require an explicit permitted rule with quantity, lead time and authorization.
An optional rule is source evidence, not independent proof of compatibility or repairability.
Missing approval, quantity, timing or trusted donor stock prevents a feasible recommendation.
Rescheduling remains a human-review request and does not assume a readiness improvement.

Planner GET requests are non-mutating. Selecting an option creates a proposed recovery case,
an existing Incident owned initially by the caller, an immutable plan snapshot and audit event.
Approval is a separate permission-controlled operation. Source fingerprint and current
feasibility are checked again; stale proposals are rejected. Approval does not reserve stock,
place orders, contact suppliers or write back to any system. Concurrent approved proposals
must be revalidated before real execution; there is no autonomous execution or reservation engine.

The linked existing incident UI handles reassignment, notes and lifecycle transitions.
Recording an actual outcome requires a reference, notes and a past timestamp. Final readiness
is recomputed from current records rather than forced to READY. Costs remain optional.
The case retains recommended versus selected actions, estimated versus recorded outcome,
actor/timestamps, and recorded readiness. Outcome evidence is user supplied, not independently
verified physical delivery. On-time resolution requires recorded READY state and a resolved
incident by the deadline; an action timestamp alone is not treated as a resolved shortage.

## UI and copilot

`/recovery` provides Readiness, Data trust, Resolution history, Management and Import views,
with a work-order detail and side-by-side planner. Filters cover site, asset, priority and date.
Evidence IDs open source review; inventory IDs identify existing Inventory records.
Management reports observed statuses, case/owner/incident state, recorded case cycle time and
known costs without currency conversion. Case creation is the first persisted recovery-warning
record; earlier warnings and historical exposure are not inferred.

Recovery-specific advisor questions use the same scoped snapshot/calculator/planner and
recorded case outcomes. They run deterministically and never send recovery records to an
external AI provider. Missing evidence causes abstention. Existing advisor inventory/delivery
regressions remain intact. This is not external-model safety verification.

## Security and limits

`recovery.read`, `recovery.manage` and `recovery.approve` are enforced server-side, together
with inventory/product/warehouse read access. Import also requires imports.create and case
creation requires alerts.create. Owner/admin/operations roles receive module access; planner,
auditor and viewer have explicit read-only access. Demo operator access remains within the
existing synthetic demo organization. Every query and correction is organization-scoped;
new tables are included in FORCE RLS and tenant-isolation regression checks.

Stored text is data, never a prompt instruction or code. UI text is rendered through React.
The module has no external communication or write-back mechanism. Reports fail explicitly
rather than silently analyzing partial data above the supervised-pilot limits (10,000 recovery
records/current positions/catalog products; 500 case-history records). Audit view is bounded
and explicitly shows the most recent 500 entries.

Intentional deferrals: full ERP connectors, automatic PO writes, supplier emails, autonomous
purchasing/substitution/rescheduling, generalized predictive maintenance, cross-customer
learning/sharing, calibrated forecasts, live physical inventory certification, optimization of
all simultaneous recovery actions, and automatic inventory reservations on approval.

The hosted workflow, WorkOS staging, external AI and human visual review gates remain BLOCKED
until actual authorized hosted evidence exists. Nothing in this module changes those gates.
