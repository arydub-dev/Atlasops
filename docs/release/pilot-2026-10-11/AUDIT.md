# Recovery Engine implementation and safety audit

October 11, 2026. Source reviewed: models/registration, migration 0018, contracts, store, engine, copilot routing, API, permissions, Recovery UI/navigation, fixture generator, regression/browser tests and implementation documentation. No application behavior changed in this audit phase. New safety tests, QA provenance capture and synthetic supplier-demo coverage were added.

## Provenance and preservation

The supplied working directory has **no .git**. Public GitHub HEAD was observed as `40e06963d4d58189beee1387e3cc1e9a75b73af6`, read without credentials. This is not the historical tested revision. Run `20261011T100228Z-f5c7b7` has no contemporaneous backend source manifest; the runner imported backend code directly from the workspace. A copied frontend exists, but it cannot establish a complete backend/migration commit. **Historical exact Git SHA: BLOCKED / unknown.** Do not retroactively label a newly made commit as that run's revision.

`source-comparison.json` records current allowlisted differences from public HEAD; `retained-artifacts.json` hashes retained reports/XML/browser/scenario/screenshots, including failed intermediate runs. Original artifacts remain unchanged under ignored `.local/qa/runs`; hashes in a document are not an off-machine backup or proof of Git tracking. Runtime private fixture data stays excluded. The QA runner now writes source-before/source-after manifests and fails with SOURCE-DRIFT if their content identities differ. These allowlisted hashes identify application/migration/test source and selected configs, not an entire repository, installed dependencies or a historical commit.

A local isolated Git review candidate is being prepared separately. The user subsequently explicitly authorized pushing main after being informed that Vercel may deploy a push. No separate deployment command is authorized or planned. Push remains pending valid local GitHub authentication. Existing GitHub CLI authentication is invalid; no credential was placed in reports or used from chat. Public read access sufficed for inspection.

## Confirmed safety coverage

| Property | Evidence / boundary |
| --- | --- |
| Tenant access | snapshot queries scope records, products, inventory and warehouses by organization; API permission checks; foreign-record/case/audit denial tests |
| PostgreSQL RLS | FORCE RLS and non-bypass application role; record and newly added case direct-SQL foreign-org invisibility tests |
| Quantities | one stock/inbound ledger; reservations unavailable; duplicate PO lines excluded; stale/missing/conflicting evidence never falsely READY; transfer donor preview tested |
| Approval | separate permission, source fingerprint, fresh feasibility check, case row lock and single transition; elapsed evidence expiry newly tested |
| Competing proposals | new test holds two proposals, approves one without stock change, corrects donor commitment and confirms second approval is rejected; this is sequential interleaving, **not simultaneous concurrency proof** |
| Audit | actor/time and original/corrected values/reason asserted; no API edit path for audit history. This is not cryptographic/WORM immutability against database administrators |
| Import | strict typed CSV/XLSX validation, duplicate IDs, all-or-nothing rejection, identical retry no-op and conflicts requiring audited correction |
| Grounding | same deterministic calculator; no recovery source sent to external AI; missing-record abstention, cross-org data and new stored-source injection check |
| No execution | preview is pure; proposal/approval/outcome do not change inventory; no supplier messaging or ERP write-back path in module |

## Unresolved findings and restrictions

1. **P1: approval concurrency / point-in-time reads.** Sources are read before case row locking, across separate SQL statements; source edits can race with approval. Different cases do not share a reservation lock. Two approvals against unchanged source may both succeed. Existing row lock serializes one case's status, not the underlying material commitment. No test proves serializable simultaneous approval/source mutation. Before operational execution, a named planner must recheck current source and all approved commitments; acceptance of this restriction must be explicit. Automated execution is out of scope and prohibited. Unrestricted multi-planner execution needs a separate concurrency design/verification.
2. **P1: “feasible” does not imply recovery by deadline.** Deterministic reproduction: fixture Plant A needs 5, has 2, deadline 2030-01-04; permitted transfer with lead_days=10 produces `feasible=true`, arrival 2030-01-11, `target_after=SHORTAGE`, empty limitations. API permits proposal/approval of that supported action even though it does not solve the deadline shortage. Preview is honest about SHORTAGE, but the label can mislead. Pilot reviewer must reject presenting such an option as a completed recovery; resolve wording/semantics before broad operational use. No expected value was changed to hide this finding.
3. **P1: missing source revision.** Historical run cannot be tied to an exact commit. New manifests improve future evidence but do not reconstruct the past. Authoritative checkout and release-owner revision attestation remain prerequisites.
4. **P2: import concurrency.** Identical sequential retries are tested. Simultaneous first imports with the same source key can race into the unique constraint; controlled retry/error behavior is not established. Restrict pilot imports to one operator/job per organization pending concurrency verification.
5. **P2: migration coverage.** Fresh database migration passes; legacy bootstrap may create current metadata. This does not prove upgrade of a populated 0017 database or hosted rollback/restore. Verify separately in staging before accepting data.
6. **P2: recorded outcome semantics.** On-time is computed when outcome is recorded from current READY plus resolved incident and deadline. Later incident resolution does not update it; after-deadline entry cannot establish historical readiness. The demo explains this point-in-time limit; do not sell it as historical SLA measurement.
7. **P2: source trust and limits.** Supplier string on inbound is provenance, not a verified foreign-key supplier match or synchronization. Recorded authorization/compatibility is human-supplied. Stock metadata freshness does not prove physical count accuracy. Case/report limits and no aggregate currency conversion are documented. Recovery-specific requests for an unknown work-order ID may fall back to authorized broad summaries rather than explicit ID-specific abstention; do not portray an unrelated summary as evidence for that ID.

These findings are not erased by passing tests. New tests establish only their named scope. Four hosted gates remain BLOCKED; no enterprise-readiness or ROI claim is supported.
