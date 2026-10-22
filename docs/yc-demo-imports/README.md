# Fictional Atlas Manufacturing import kit

All records are synthetic, generated for demonstration. Supplier scores are scenario inputs, not measured customer performance. Prices are USD. Inventory is units. This kit contains values, not formulas.

Use the actual Data Sources → Import screen. Select the entity, upload CSV or the workbook, select the matching worksheet, review mapping and validation, then commit. Each worksheet is a separate import; uploading the workbook does not import every worksheet automatically.

## In the provisioned demo workspace

1. Import `inventory_refresh.csv` as Inventory. HP-240 changes from 42 to 80 units. The reorder recommendation changes from 250 to 212 units (292 target minus current stock). Warehouse inventory totals update in the same transaction.
2. Repeat the same file. Expect one accepted unchanged row, no additional position and no additional stock.
3. Import `shipment_update.csv` as Shipments with **Update existing** selected. The seeded SHP-1050 ETA becomes October 15, 2026 UTC. Repeat to verify one existing shipment is updated, never duplicated. These are fixed demonstration dates; replace them before a later presentation.
4. Reset the allowlisted demo workspace using its administrator reset control to restore the seeded scenario.

Do not import the supplier/warehouse create sheets over an already seeded workspace: their names are not idempotency keys. Product and shipment create mode rejects existing unique identifiers. Idempotency is implemented for inventory snapshots and explicit product/shipment updates, not every create import.

## In a new, empty disposable organization

Import Suppliers, Warehouses, Products, Shipments, then Inventory. The inventory sheet has 240 positions and uses warehouse names and product SKUs to resolve relationships. The other master-data import sheets do not attach supplier/product/warehouse foreign keys to shipments; use the operator seed for the fully linked storytelling scenario. `shipment_update` targets the seeded workspace, not this empty-organization import.

The importer returns accepted/rejected rows and created/updated/unchanged outcomes. Review rejection details instead of presenting a partially accepted file as complete. Risk/alert refresh still uses the existing background-job configuration and must be verified on the host.
