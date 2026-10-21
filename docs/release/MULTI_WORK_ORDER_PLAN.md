# Multi-work-order recovery implementation plan

Baseline: authenticated application b95c3d8, not the separate public demo release.
Historical local QA: 20261019T093608Z-fb1880, 901 entries / 871 pass / 0 fail / 4 blocked / 26 skipped. Not evidence for this change.

1. Extend deterministic allocation through a bounded plan simulator: current state, individual documented actions, combinations of two distinct actions. Reuse the full tenant demand ledger; no LLM arithmetic or source mutation.
2. Validate shared donor stock, PO identity, rule quantities, deadlines, permissions and evidence freshness across the complete plan. Reject overlapping consumption and newly worsened shortages. Show hypothetical outcomes even for donor-blocked transfers where trustworthy inputs permit calculation.
3. Persist selected plan and alternatives in existing RecoveryCase JSON, linked Incident and audit records. No schema migration. Recompute and compare at proposal/approval; reject overlapping active decisions and stale sources. Approval records a decision only.
4. Add a Recovery plan comparison tab, evidence and uncertainty details, and reuse resolution history. Preserve existing per-work-order planner and assertions.
5. Add evidence-qualified integration catalogue and data-flow component with sourced logos where permitted; preserve existing setup/import paths.
6. Generate a relative-date multi-work-order synthetic fixture without modifying existing orgs or production data.

Acceptance: shared stock/inbound allocation; donor harm; feasible combinations; overlapping rule/PO consumption; authorized substitutes/repair; unknown costs/timing; stale or contradictory inputs; nonmutation; scoped API and permission checks; proposal/approval/source-change rejection; incident/outcome persistence; frontend type/lint/build and browser walkthrough. Retain failed results.

Limits: bounded enumeration, not mathematical optimization; no autonomous maintenance changes, ERP writes or physical stock movements. Plans with unknown costs cannot be ranked as cheapest. Hosted login, WorkOS lifecycle, external AI and human visual approval remain blocked until fresh evidence proves otherwise. No paid infrastructure or production migration authorized.

## Implemented scope and limits

- New simulator reuses engine.calculate and documented rule candidates; no new database tables or migrations. Maximum 8 selected orders, 12 action candidates, 250 active demand lines, pairs of at most two full-deficit actions. Requests beyond limits fail explicitly rather than silently sampling demand.
- No duplicate authorization, PO-line use or same-requirement full-deficit actions within a plan. Shared donor stock is evaluated in aggregate. Unknown readiness prevents a feasible-plan claim. Repair scenarios additionally need a repairable-item availability reference; this is recorded customer evidence, not independent inspection or serial-number inventory management.
- Ranking: no newly worsened shortage; feasible plans first; sum of restored priority weights (6 minus source priority), number restored, known cost only under the existing known_cost policy with complete common-currency evidence, latest estimated arrival, stable ID. This is a bounded heuristic, not mathematical optimization or savings prediction.
- Case JSON retains comparison, source fingerprint, plan signature, rationale, authenticated owner and due date. Approval recomputes the plan; source changes and elapsed evidence invalidate it. Same-tenant plan proposals/approvals serialize on the organization row in PostgreSQL. Overlapping active decisions sharing rule, requirement, PO or donor stock evidence are rejected for new simulator plans. Legacy single-action behavior is preserved; decisions are not physical stock reservations.
- A recorded outcome does not alter inventory or automatically prove recovery. Final readiness for all work orders is retained separately from user-reported outcome and cost. External execution, part-quantity splitting, more than two simultaneous actions, formal customer-specific priority scoring, and autonomous rescheduling are deferred.
- tools/recovery/demo.py --multi generates fresh relative-date files into a caller-selected folder. Existing default fixture and QA assertions are preserved. No staging or production records are recreated.
- Integration catalogue: SAP Business One, Salesforce, Dynamics Business Central and UPS are PROTOTYPE; CSV/XLSX IMPORT AVAILABLE based on local import verification; SAP S/4HANA and Oracle Fusion PLANNED. No catalogue card claims a live connection. SAP and UPS use sourced Simple Icons SVGs; Business Central official SVG is used in the architecture diagram only. Oracle logo needs written authorization; Salesforce logo usage is pending asset/permission review. Generic icons are identified as such, not recreated logos.
- October 21 read-only Vercel inspection still shows no REDIS_URL in branch-specific Preview settings. WorkOS/reviewer variable presence is not lifecycle evidence. New code must not replace production or change the public main-site login before isolated database targeting and hosted dependencies are verified.
