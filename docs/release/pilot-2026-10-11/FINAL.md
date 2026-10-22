# Enterprise pilot evidence review — October 11, 2026

**Verdict: FAIL / NOT READY.** No hosted checks executed, no public-site fault testing and no customer data used. Main push was subsequently authorized by the user; it remains blocked on invalid local GitHub authentication. No separate deployment command was issued.

## Exact identity and environment

Historical run `20261011T100228Z-f5c7b7`: exact Git revision **unknown**. Workspace has no Git metadata and that run did not capture backend hashes. Public repository HEAD observed: `40e06963d4d58189beee1387e3cc1e9a75b73af6`; do not attribute historical tests to it.

New run **20261011T102413Z-910e34**, completed **2026-10-11T10:32:33.245324+00:00**.
Allowlisted source SHA256: **016545e7565650a563f5ea28882387937e270693a2f2d41aba52fd87c6548324**. Before/after fingerprints match; original manifests copied here. A local Git candidate can be linked to this content identity after commit, but its commit must not be presented as a revision recorded before the tests ran.

Environment: isolated local synthetic SQLite + disposable PostgreSQL 16.14 with NOSUPERUSER/NOBYPASSRLS application role, owned Redis 8.10.2, Python 3.12.13, Node 25.8.0, Chromium/Next development server, deterministic local AI. No hosted URL/build was verified. Local Node version is not a staging runtime attestation.

## Results

| Total | PASS | FAIL | BLOCKED | SKIPPED |
| --- | --- | --- | --- | --- |
| 901 | 871 | 0 | 4 | 26 |

PostgreSQL: 436 passed. SQLite: 410 passed, 26 skipped. Browser: all 13 passed. All 26 SQLite skips have corresponding passing PostgreSQL cases, verified by testcase identity; skipped entries remain SKIPPED. Existing AI-001/AI-003/AI-004 and Recovery browser checks PASS. All previous baseline IDs remain and no previous PASS regressed.

Focused safety plus QA self-tests: 51 passed, 2 PostgreSQL-only skipped, 3 subtests passed. TypeScript and ESLint PASS. Application UI/build source was unchanged by this audit; prior optimized build remains the recorded build evidence, not a new hosted build.

Four new material-gap regressions: elapsed-time approval revalidation without source edits; competing outstanding proposals with a donor correction plus non-mutation/repeated-approval/audit checks; malicious imported source text cannot replace deterministic grounding; direct PostgreSQL RecoveryCase RLS. Interleaving test does not establish simultaneous transaction serializability.

New provenance tests cover exclusion of runtime secret/generated files and content identity changes. Runner captures source before/after and fails on drift. Synthetic browser demo now imports a supplier through the existing importer. No product features, application calculation behavior, migrations or release assertions were changed in this audit phase.

## Artifacts and preservation

`latest-report.json` / `latest-report.md`: copied completed report. `latest-source-before.json` / `latest-source-after.json`: source identities. `retained-artifacts.json`: SHA256 inventory of retained reports including failures. Original full run: `.local/qa/runs/20261011T102413Z-910e34`. Original reports remain untouched; private fixture credentials are neither copied nor committed. Artifact references/hashes do not constitute an off-machine backup of raw evidence.

See `AUDIT.md` for security/correctness review and unresolved concurrency, late-option semantics, simultaneous import, migration-upgrade and historical-outcome limits. See `ACCEPTANCE.md` for exact gate procedures, proposed responsible roles, expected results and missing prerequisites; `gates.json` records timestamped BLOCKED statuses. See `DEMO.md` for repeatable synthetic input/import/shortage/comparison/approval/outcome/persistence steps and distinctions between calculations, estimates and human decisions.

## Release blockers and priorities

HOST-001, SSO-001, AI-LIVE-001 and VISUAL-REVIEW-001 all **BLOCKED**. Required next: verified separate staging project/URL/build and synthetic users; WorkOS test lifecycle access; securely configured live provider with approved test budget and telemetry; named human approval of that exact revision.

Before a supervised pilot, establish candidate provenance, complete authorized staging acceptance, resolve or explicitly constrain the documented decision-support risks, test hosted recovery/monitoring and populated migration, and assign operating/support ownership. Approval is not execution or a reservation. No production-readiness claim is supported.
