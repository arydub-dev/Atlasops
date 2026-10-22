# Demo experience review — 2026-10-15

Scope: local improvements; not hosted acceptance. Production remains unchanged.

Implemented in this iteration:
- Private login password visibility, busy/error behavior and restrained branding.
- Explicit synthetic workspace label for private-demo organizations as well as seeded organizations.
- Optional three-step demo exploration guide linking existing workflows.
- Operations overview with real readiness and recovery-case queries, bounded lists, unknown/empty/error states and incident links. Pending means proposed or approved; recently resolved means linked recovery incident status resolved. These are not all incidents or supplier delivery metrics.
- Active navigation semantics, skip link, keyboard focus and reduced-motion styles.
- Recovery planner response versioning to prevent a previous work-order request replacing the latest selection. Successful mutations clear old selection/options before further action.
- Copilot copy no longer promises every answer has citations or labels an unknown provider as local.

Known limitations requiring work before delivery:
- Existing seed does not preload Recovery Engine records; operator must import the generated synthetic recovery kit before handing over the account. Reviewers should not perform this setup.
- No verified hosted demo account, URL, database target, provider, or visual approval.
- Previous GitHub preview build reported success on Oct 15 for 3095148, but deployment belongs to abd26; local staging resource was provisioned in acmea9. Build success is not evidence of runtime health.
- The latest UI changes are not that deployed revision.
- Vercel CLI remains unauthenticated. User acknowledged access request but did not yet confirm successful CLI authentication.
- Existing demo reset does not establish safe Recovery Engine restoration; do not enable reset for reviewer. Restore in a separately authorized disposable synthetic environment after validating dependencies.
- Earlier audit caveats (concurrent approvals, no inventory reservation/execution, point-in-time outcomes, external connectors unverified) remain.

Hosted acceptance and recording sequence:
1. Record exact deployed commit, build, isolated database identity and synthetic organization.
2. Operator preloads fresh fixture kit and verifies A2/required5, B10/required9, late PO3 and authorized expedite. Check organization isolation before credential delivery.
3. Fresh reviewer browser: login, synthetic label, overview, inventory/supplier/shipment exceptions.
4. Readiness: WO-A shortage3; open stock, requirement and PO evidence. Compare transfer3 (donor shortage2) with authorized expedite3 (estimated day1, USD90 synthetic direct cost).
5. Enter rationale/due date; propose and approve. Explain this records intent and does not execute ERP writes or alter stock.
6. Record explicitly synthetic supplier confirmation through audited source correction; inspect readiness. Assign/advance/resolve linked incident; record outcome with reference.
7. Refresh and re-login; inspect persisted audit history, quantities and outcome.
8. Repeat on mobile, inspect failed requests/logs, obtain human review approval for the exact revision.
9. Deliver restricted demo credentials privately only after the same account passes these steps.

Required evidence: dashboard/readiness/comparison desktop and mobile screenshots, sanitized API assertions and audit records, test counts, deployed SHA, timestamp and explicit human approval. None of the hosted items above have been marked passed.

## Verification results
Full local QA: 20261015T093445Z-faf2bd — 901 entries, 871 PASS, 0 FAIL, 4 BLOCKED, 26 SKIPPED. SQLite 410 passed/26 skipped; PostgreSQL 436 passed; browser 13 passed. The four blocks are HOST-001, SSO-001, AI-LIVE-001 and VISUAL-REVIEW-001. Release FAIL / NOT READY.
Earlier sandbox attempt 20261015T093414Z-7a7a24 retained: 0 pass, 0 fail, 11 blocked, 0 skipped (local sockets not permitted).
Production build, TypeScript, lint and git diff whitespace check passed.
Separate production-build login regression: initial run 2 failed due to selector matching Next route announcer as well as form alert; scoped to form, same assertion. Rerun 2 passed (desktop/mobile). This test-only selector correction occurred after the full suite; application source unchanged. Mocked invalid-credential responses are UI-only evidence, not real hosted login.

This iteration is partial completion of the broader request. No hosted credentials or human visual approval are available, and the preloaded coherent Recovery dataset and tested restoration procedure remain outstanding. Existing tables/navigation largely retained; not a claim of comprehensive redesign or all acceptance criteria satisfied.
