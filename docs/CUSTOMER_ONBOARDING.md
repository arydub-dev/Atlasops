# Customer onboarding

Use a controlled pilot after the live release gates pass. Agree on one business question, data owner and authorized users. Record warehouse count, active SKUs, shipment volume, current reporting effort and exception process before importing.

1. Sign in through configured WorkOS; create the organization.
2. Confirm the correct organization and roles; invite only required users.
3. Import warehouses, products and suppliers before dependent inventory. Use a small sample first.
4. Upload UTF-8 CSV or macro-free XLSX (values only). Maximum 15MB compressed input, 50MB expanded workbook, 10,000 data rows and 100 columns.
5. Use unique headers, map fields and review preview errors. Correct invalid numbers and unknown references. Integer quantities must be whole nonnegative numbers; risk/reliability percentages are 0–100.
6. Commit and inspect imported/rejected counts. Duplicate constrained records are rejected without discarding valid rows. Re-import is not an upsert. Inventory warehouse/SKU references must exist in the same organization.
7. Compare dashboard totals to the source and review a shipment, stock position, supplier and risk.
8. Ask Copilot for a briefing; review its saved context and distinguish observations from recommendations.
9. Run a simulation with recorded assumptions; do not interpret it as a guaranteed forecast.
10. Review access, billing, support and the weekly pilot review schedule.

Legacy XLS/XLSM and formula workbooks must be converted to macro-free, values-only XLSX or CSV. Import previews validate field types; reference and duplicate checks also occur at commit. Large asynchronous import progress and rollback UI remain pending. Shipment imports currently default shipped time/ETA; do not sell those defaults as carrier-provided ETAs.
