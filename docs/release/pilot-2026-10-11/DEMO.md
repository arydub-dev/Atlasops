# Repeatable synthetic customer demonstration

Use a fresh isolated synthetic organization, never customer data. Hosted execution is BLOCKED until ACCEPTANCE.md prerequisites and authorization are satisfied. The fixture generator writes CSV files only; it does not contact a database.

Generate fresh fixtures into an isolated folder:

```bash
backend/.venv/bin/python tools/recovery/demo.py --output /tmp/atlasops-pilot-demo
```

Record generator/source revision, UTC time and SHA256 of each CSV. Freshness is seven days by default. Do not relabel real stale evidence with new timestamps.

1. In existing Data Sources import **suppliers.csv**, then products.csv, warehouses.csv and inventory.csv. Supplier performance values are explicitly synthetic, not measured reliability. In Critical spares readiness → Import, select and import stock.csv, requirement.csv, inbound.csv and rule.csv. For XLSX acceptance use the same rows in a workbook and confirm the selected sheet.
2. Plant A has 2 units, needs 5 in three days: calculated shortage **3**. Plant B has 10 and needs 9: calculated surplus **1**. Open both requirement lines and source records; verify quantities, reservations, usability and timestamps.
3. Compare transfer of 3 (estimated one day, recorded synthetic USD25) with expedite of the existing 3-unit PO (estimated one day, synthetic USD90). Current inbound is five days away, after the deadline. Transfer creates Plant B shortage **2** and must be rejected as infeasible. Expedite preview covers A and preserves B; it does not create extra PO supply.
4. Show evidence IDs/source details and assumptions. On a separate synthetic copy, remove an inbound date/confirmation or make stock stale: results must expose uncertainty and never silently become READY. Restore only through an audited correction with reason.
5. Authorized test operator records rationale and due date, proposes expedite; authorized approver reviews and approves. This is a simulated human decision, not a supplier instruction, reservation or purchase. Inventory must remain A2/B10.
6. In Data trust, record a **synthetic** confirmed expedited promised date before the deadline with an explicit correction reason/reference. Observe computed READY based on that commitment; it is not proof of physical receipt. No correction should be presented as independent external validation.
7. Open linked incident, assign owner, move through investigation and mitigation, resolve with synthetic evidence. Then record actual-outcome reference, notes and past timestamp. Final readiness is recomputed; recorded on-time flag is a point-in-time observation, not inferred retrospectively. If recording outcome before resolving incident, on-time is false and remains that recorded snapshot.
8. Refresh, then log out/in and verify source correction, owner, incident state, approval and outcome persist. Capture before/after quantities, record IDs and audit actor/time/original/corrected/reason. Retain CSV hashes, screenshots and sanitized API results.

Calculated: shortfall, allocation, donor impact, readiness and reconciliation. Estimated: lead time, future arrival and synthetic direct cost; no guaranteed service level or savings. Human decisions: compatibility/permission evidence, choice, approval, source correction and outcome attestation. No live supplier sync, ERP write-back or external AI execution is demonstrated.

Automated coverage: frontend/qa/recovery.spec.ts covers supplier/inventory/recovery imports, planner, donor impact, proposal/approval, source correction, outcome, incident transitions and refresh. Existing login test checks re-login generally; a Recovery-specific re-login observation is still required during staged acceptance. Do not claim that this local browser case alone establishes hosted persistence.
