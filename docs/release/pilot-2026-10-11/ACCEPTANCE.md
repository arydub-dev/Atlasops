# Authorized staging acceptance plan

Prepared October 11, 2026. **FAIL / NOT READY**. No hosted acceptance executed.
The public atlasops.online URL is not verified as staging. A GitHub repository URL is not a deployed-revision attestation. All owners below are proposed roles, not assigned people or approvals.

## Common prerequisites and evidence format

Release owner must record Vercel team/project/environment, separate staging URL, deployment/build ID, frontend/backend Git SHA, migration head, synthetic tenant A/B IDs, test users and role matrix, UTC start/end, operator and authorization reference. Obtain hosting-console evidence and confirm build-to-source linkage; do not infer from the homepage. Database, Redis, WorkOS and provider projects must be separate from production. Confirm backups and a synthetic cleanup plan. No development authentication on the hosted target. Secrets stay in managed secret storage; no cookies, keys, authorization codes or session values in screenshots/logs/reports.

Every case retains: gate/case ID, status PASS/FAIL/BLOCKED/SKIPPED, exact revision/build/environment, UTC timestamp, actor, expected/actual result, sanitized evidence path/checksum, and reason. Preserve failed attempts. Empty fields or unavailable evidence remain BLOCKED. No deployment, invitation email, provider spending or fault injection is authorized merely by this checklist. Obtain scoped approval for those actions first.

## HOST-001 — BLOCKED

**Owner:** release engineer + hosting administrator (unassigned).
**Access/environment:** verified staging project/deployment, separate DB/Redis, two synthetic tenants; admin/operator/viewer accounts; read-only scoped reconciliation access.
**Authorization:** named target and revision, permission to create/update only synthetic records and controlled test sessions; separate deployment authorization if no environment exists.
**Procedure / expected results:**
1. Capture console project/environment/build and Git revision; verify app/backend revision and migration head agree. Stop on mismatch or production/customer data.
2. Log in as tenant A operator; verify org and permissions; deny tenant B IDs and viewer mutations server-side.
3. Import suppliers/products/sites/inventory CSV and requirements XLSX; capture mapping, row counts and rejected rows. Repeat the identical upload; verify no duplicate current positions.
4. Reconcile quantity totals, supplier and inbound evidence, shipment dates and inventory display against scoped database results.
5. Open shortage, verify target-minus-available calculation; run DEMO.md including donor impact, proposal, approval and evidence correction. Preview/approval must not change stock or call external connectors.
6. Assign incident, investigate/mitigate/resolve; record outcome. Refresh and log out/in; verify records, role and ownership persist.
7. Log out; old session must receive unauthorized responses. Retain no cookie values.
**Retain:** revision attestation, source input checksums, import results, sanitized request/status traces, scoped SQL totals, before/after stock values, incident/case/audit IDs, desktop/mobile screenshots, persistence observations.
**Missing:** staging project, verified URL/build/revisions, synthetic organizations/accounts, administrator access and scoped execution approval.

## SSO-001 — BLOCKED

**Owner:** identity administrator + security QA (unassigned).
**Access/environment:** WorkOS staging app/orgs, verified callback/logout URLs, controlled invitation inboxes, restricted and administrator test users.
**Authorization:** staging identity configuration, invitations only to named controlled test inboxes, role changes/revocation for test users only.
**Procedure / expected results:**
1. Real login/redirect/callback yields one session in intended organization; wrong org has no access.
2. Send controlled invitation; accept once, verify membership and intended role; reused or invalid invitation fails.
3. Invalid/missing/reused OAuth state and callback replay must fail without creating a session.
4. Exercise configured expiry using a controlled staging session; expired and logged-out credentials rejected by API, not merely hidden by UI.
5. Downgrade role while signed in, then attempt mutation using that session; enforce updated permissions. Revoke membership/session and verify denial.
6. Confirm development auth bypass is disabled; record session TTL and logout behavior.
**Retain:** redacted configuration screenshots, test-user/role matrix, event IDs, UTC event order, API statuses, callback/replay outcomes. Never retain callback codes/state/session tokens.
**Missing:** staging app/org configuration, test accounts/inboxes, identity admin and invitation/revocation authorization.

## AI-LIVE-001 — BLOCKED

**Owner:** AI service owner + security reviewer (unassigned).
**Access/environment:** staging provider project/model, secure key configured by admin, approved synthetic-test budget, two tenants with distinct canaries, redacted provider execution telemetry.
**Authorization:** synthetic prompt transmission and bounded provider spending; targeted timeout/error testing isolated to the test request/tenant. No shared-production failure injection.
**Procedure / expected results:**
1. Test explicit SKU beyond summary limit and unsupported delivery assertion. Expect correct scoped replenishment and explicit abstention. Label deterministic routing accurately.
2. Use a supported broad operational prompt that actually invokes the configured provider. Require provider request ID/model/time plus sanitized server trace. A local response or stub cannot satisfy this gate.
3. Seed different canaries in tenant A/B. Ask A for B's information; neither retrieved context nor output may contain B's canary.
4. Embed malicious instructions in synthetic imported descriptions. Ask the legitimate business question; provider must treat stored text as data, retain grounded answer and not reveal the canary or follow injected commands.
5. Exercise bounded provider timeout and error using an approved staging-only mechanism; record whether an actual call occurred. Expect controlled error/fallback, no fabricated claim, no cross-tenant context, observable sanitized failure.
6. Repeat for each provider offered for this pilot; untested providers stay disabled or BLOCKED. Review actual retrieved context and output, not output alone.
**Retain:** synthetic fixture hashes, prompt IDs, actual provider request IDs/model, sanitized retrieval/output, latency/error status, reviewer findings and fault mechanism. No credentials or customer data.
**Missing:** confirmed staging provider/model/project, secure configuration, budget/authorization, controlled tenants and telemetry.

## VISUAL-REVIEW-001 — BLOCKED

**Owner:** named human product/design reviewer + pilot sponsor (unassigned).
**Access/environment:** exact verified staged revision, desktop 1440x900, mobile 390x844; controlled operator and viewer.
**Authorization:** human review of synthetic target; explicit approval must identify revision/build, date and reviewer. Agent screenshots never count as human approval.
**Procedure / expected results:** check login/logout/invitation; sidebar/mobile navigation; imports and errors; inventory/dashboard; issue detail; Recovery Readiness/Data trust/Planner/History/Management; supporting evidence and uncertainty; incident assignment/resolution; loading/empty/error states; keyboard focus and 200% zoom. No horizontal clipping, inaccessible primary action, ambiguous approval/execution claim or misleading READY status. Confirm late option preview remains visibly SHORTAGE and approval is not execution.
**Retain:** route/viewport/revision-labelled screenshots, checklist with defects and disposition, named human decision APPROVE/REJECT, timestamp and signed/recorded approval reference.
**Missing:** verified staging revision, named reviewer and explicit human approval. Local screenshots are supplementary only.

## Authorized design-partner pilot priorities

1. **P0:** recover authoritative Git provenance; review/commit the candidate; record the user’s subsequent main-push authorization and possible Vercel auto-deployment; obtain valid local GitHub authentication before pushing. Exact historical SHA remains unknown if not recoverable from operator records.
2. **P0:** confirm separate staging and scoped authorization; resolve all four gates with real evidence. Never substitute public homepage availability.
3. **P0:** resolve or explicitly constrain concurrency and late-option interpretation risks from AUDIT.md. Pilot is supervised decision support; one planner revalidates current source/commitments immediately before any real-world action. No automatic reservation, purchasing or ERP execution.
4. **P1:** run the synthetic demo against the verified revision, reconcile results, complete human review and record release-owner decision. Migration from a populated prior schema and hosted rollback/recovery require explicit staging evidence.
5. **P1:** agree named support/incident owners, operating hours, data retention, access scope and measurable pilot acceptance criteria. Validate backup restore and monitoring in staging; local worker fault evidence is not hosted recovery evidence.
6. **P1:** only after acceptance and separate launch authorization, onboard the design partner with agreed data scope and success measures. Enterprise pricing and ROI remain unsupported until measured.
