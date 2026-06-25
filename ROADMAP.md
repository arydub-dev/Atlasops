# ATLASOPS — Roadmap

This roadmap describes planned direction. It is indicative, not a commitment to dates or
ordering. Items reflect operational needs identified during design and deployment
planning.

## Near term

| Item | Why it matters |
| --- | --- |
| **Background job queue** | Move file imports and risk/alert recomputation out of the request lifecycle so large ingestions and periodic scoring run asynchronously. |
| **Audit log explorer UI** | Make the existing `audit_logs` data browsable and filterable for operational and compliance review. |
| **Encrypted connector credentials** | Store connector secrets encrypted at rest (or via a secrets manager) rather than masked-only. |
| **Frontend test coverage** | Add component and end-to-end tests for the application surfaces. |
| **Rate limiting** | Request throttling on authentication and public endpoints. |

## Mid term

| Item | Why it matters |
| --- | --- |
| **Production-ready connectors** | Real ERP/WMS/TMS integrations with per-customer endpoint configuration, authentication flows, incremental sync, and webhooks. |
| **Workflow execution** | Turn recommended actions and alerts into tracked tasks with owners, due dates, and status — closing the loop from insight to action. |
| **KPI impact tracking** | Measure whether recommended actions improved on-time delivery, reduced stockouts, or lowered risk, to refine the recommendation engine. |
| **Real-time updates** | WebSocket push for alerts and shipment events to remove polling latency. |
| **Advanced simulations** | Multi-scenario comparison, saved scenario portfolios, and simulation diffs for business reviews. |

## Long term

| Item | Why it matters |
| --- | --- |
| **Multi-tenancy & SSO** | Organization-level data isolation and SAML/OIDC authentication for enterprise identity providers. |
| **Operational ontology layer** | A formal entity-relationship model above raw tables to enable richer cross-entity and graph-based analysis. |
| **Forecasting models** | Statistical demand forecasting (e.g. ARIMA/Prophet) replacing heuristic projections. |
| **Agentic investigations** | Multi-step Copilot workflows that gather context across modules before presenting a conclusion. |
| **Geospatial basemap** | Vector tile basemap behind the Network View for geographic context on international networks. |

## Out of scope

ATLASOPS is an operational intelligence layer, not a system of record. It is not intended
to replace ERP, WMS, or TMS platforms, and it does not autonomously execute supply chain
actions. Human judgment remains central to every decision the platform supports.
