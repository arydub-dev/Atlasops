# Demo integration catalogue — evidence review (2026-10-17)

The public /demo Data Sources tab is informational and synthetic-only. No connection credentials, database writes, background jobs, new authentication flows or migrations are added. Existing authenticated /data-sources workflows are unchanged.

| Source | Display status | Evidence and scope |
|---|---|---|
| CSV/XLSX | Prototype | Existing authenticated file parsing, worksheet selection, mapping and import code; local import/reconciliation tests. Public demo has preloaded examples, not upload execution. |
| SAP ERP / S/4HANA | Planned | No adapter found. Never inferred from Business One support. |
| Oracle Fusion Cloud ERP | Planned | No adapter found. Coverage and APIs require discovery. |
| SAP Business One | Prototype | Development revision 364187b includes Service Layer /b1s/v2 login, endpoint allowlist, pagination and explicit suppliers/products/sales-order mappings. Not included in the production backend baseline; local test evidence only. |
| Salesforce | Prototype | Deployed baseline adapter has OAuth/SOQL Account or configured-object supplier mapping. Development branch adds wider explicit mapping. No external sandbox/customer execution verified. |
| Dynamics 365 Business Central | Prototype | OAuth/API implementation maps items to products and sales orders to shipment records. Sales orders do not establish physical dispatch/delivery. No live verification. |

No catalogue source is labelled Available for the hosted public demo, and no live sync timestamp or health indicator is invented. Setup actions show actual prerequisites, not fake Connect buttons. Generic synthetic field mapping previews are not vendor-schema claims. Recovery navigation uses the unchanged public demo calculation and workflow.

Existing connector architecture reviewed: per-organization Connection models; require_permission checks and scoped retrieval in backend/app/api/routers/data.py; Fernet credential serialization in connectors/credentials.py; SSRF validation in connectors/ssrf.py; queued jobs, cursor/retry and dead-letter handling in connectors. No live validation of these mechanisms is claimed here.

Validation: deployed-baseline Salesforce/credential tests 34 pass, 1 PostgreSQL-only skip; RBAC/tenant isolation/SSRF tests 16 pass. Development mapped connectors/import journey/Recovery Engine tests 54 pass, 2 PostgreSQL-only skips. Existing public-demo state/calculation/abstention tests 3 pass. TypeScript, lint and production build pass. These are local tests; browser hosted checks are retained separately in local evidence. Earlier PostgreSQL evidence remains preserved, not replaced by skipped checks.

Remaining integration work: customer-authorized test environments, product-specific read scopes, live authentication/session checks, source mapping and reconciliation, sync/retry monitoring, disconnect and credential-removal verification. External ERP writes remain out of scope.
