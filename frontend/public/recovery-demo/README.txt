Synthetic Recovery Engine demo. Generated 2026-10-10T18:51:44.136919+00:00

Import products.csv, warehouses.csv and inventory.csv through the existing Data Sources importer (in that order).
Then import stock.csv, requirement.csv, inbound.csv and rule.csv from Critical spares readiness > Import, selecting each matching record type.
Files are available at /recovery-demo/<filename>.csv.

WO-A is short by 3. Plant B has 10 but needs 9: transferring 3 would create donor risk and must be rejected. The documented expedite option advances the existing 3-unit PO line without duplicating inbound. Its known direct cost is USD 90.
Choose the expedite option, record a rationale and due date, propose it, and approve it in Resolution history. No purchase order or external system is changed.
Use the linked incident for assignment and lifecycle updates. Record a synthetic actual outcome reference. Readiness remains unchanged until authorized source imports/corrections establish the new operational facts.
For a final READY result, review the inbound source and correct promised_at to the documented expedited date with a reason, or import a new current inventory snapshot plus an audited stock-evidence correction after receipt; do not count a received PO as still open.

After seven days these files intentionally become stale. Regenerate synthetic dates with tools/recovery/demo.py; never silently refresh timestamps on real source data.
