# Core functionality review — 2026-10-03

Scope: import-based operational decision support. Connector development is deferred at the user's request. This is not production certification or proof of enterprise ROI.

## Useful daily workflow

1. An authorized company user imports supplier, warehouse, product, inventory and shipment data using supported CSV/Excel schemas, reviewing mapping and rejected rows.
2. The team checks shipment exceptions, stockouts, reorder thresholds and supplier performance. Outputs depend on the completeness and accuracy of supplied demand/threshold/performance fields.
3. Users investigate related entities and timelines, prioritize risks, and use incidents/workflows to coordinate action.
4. Scenario simulation estimates disruption effects using deterministic formulas; the Copilot provides assistive explanations. Neither represents validated forecasts or autonomous purchasing decisions.
5. Refresh source files and compare actual outcomes against a baseline. Manual imports imply manual data freshness; do not claim real-time visibility.

## Verified in this pass

29 selected workflow tests passed: CSV import/audit, invitations and access boundaries, inventory classification, graph/timeline/search, risk indicator generation and workflow APIs. Synthetic fixtures were used; external identity and billing were not exercised.

Found and fixed an inventory category inconsistency: overlapping reorder/max-stock thresholds allowed one line to be counted as both low stock and overstock. SQL summary and overstock filtering now follow the same precedence as the row-level classification. Added a regression that verifies dashboard totals, filtered items and row status agree. Zero and absent supplier data/heuristic-confidence fixes from PR #2 remain relevant.

## What still needs functional acceptance

- Reconcile every imported entity's source count, totals, IDs and relationships against a representative anonymized company export, including re-import/update behavior.
- Verify reorder outputs against buyer policy, lead times, demand quality, order multiples, inbound orders and reservations. Current quantity-to-target rules are not a comprehensive procurement optimizer.
- Run a complete import-to-investigation-to-resolution browser journey, not only isolated API smoke tests.
- Confirm imported stale/unknown inputs are distinguishable from current and measured inputs. Current snapshot charts do not establish historical trends.
- Define usefulness with the operating team: time to identify an exception, accuracy of prioritized issues, time to resolve it, and planning effort saved. Establish a baseline before measuring improvements.
- Complete production authentication and Redis configuration for actual access. Deferring connectors does not remove the shared rate-limiting requirement.

Recommended pilot scope: one team, one site, regular file imports, inventory/shipment exception review and human-approved actions. Do not sell unverified forecasting accuracy, automated optimization, real-time integration or guaranteed savings.
