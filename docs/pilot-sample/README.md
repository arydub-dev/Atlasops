# File-based pilot acceptance exercise

Synthetic fixtures only. Use a dedicated test organization, never a customer workspace.

1. Import warehouses.csv as Warehouses, then products.csv as Products. Preview mappings before committing; each should accept one row.
2. Import inventory-initial.csv as Inventory. Expect exactly one low-stock line, quantity 5, days of supply 5, suggested reorder 25.
3. Create an incident, record a planner decision and resolve it. This records a decision; it does not place a purchase order.
4. Import inventory-refreshed.csv as Inventory. Expect the same current position, quantity 20, reorder 0 and one healthy line. Repeating the upload must not increase the position count.
5. Record source rows, accepted/rejected rows, observed values, timestamps and operator. Run the same review in a second organization and confirm no cross-organization visibility.

Inventory imports are full current-position snapshots for included warehouse/SKU pairs: supplied/defaulted threshold fields replace the current position fields. Omitted pairs remain unchanged. This does not maintain a historical snapshot series. Supplier, warehouse, product and shipment files do not yet provide a general-purpose update contract; do not repeatedly upload those files expecting an upsert.

The automated API version is backend/tests/test_pilot_import_journey.py. Real browser, identity-provider and production-role acceptance must still be performed on the deployed release.
