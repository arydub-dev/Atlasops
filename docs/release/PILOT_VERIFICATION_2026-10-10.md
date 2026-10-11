# Supervised pilot release verification — October 10, 2026

## Scope and environment

Baseline: `20261010T132914Z-ffbdba` — 810 entries, 786 passed, zero failed,
six blocked, 18 skipped; NOT READY.

This work adds local isolated fault evidence, not product scope. No deployment occurred,
no public-site fault tests ran, and no production customer data was accessed or modified.
The user confirmed that https://www.atlasops.online/ is the public site, but staging status,
deployed revision, synthetic tenant, WorkOS staging and external-provider configuration
are unverified. Hosted application version: **NOT VERIFIED**. Hosted environment: **BLOCKED**.

## Files affected

- `backend/tests/test_import_process_recovery.py`: three real SIGKILL cases against disposable PostgreSQL, with retry and reconciliation.
- `backend/tests/test_worker_process_recovery.py`: three actual connector/ARQ subprocess fault tests with owned Redis AOF storage.
- `tools/qa/health.py`: aggregate prerequisite evidence only after all named PostgreSQL fault tests pass; absent/skipped cases block and failures fail.
- `tools/qa/test_health.py`: two additional fail-closed evidence tests.
- `tools/qa/README.md`: execution instructions, isolation rules and evidence limits.
- `docs/release/HOSTED_PILOT_REVIEW.md`: staging access inventory and separate human-review checklist.
- `docs/release/PILOT_VERIFICATION_2026-10-10.md`: this report.

No production application code, frontend code or existing advisor/browser assertions changed.
The browser test source was byte-compared with the verified baseline's saved copy.
The existing release verdict function was preserved.

## New observed evidence

### Import transaction interruption

Each case invokes the real inventory importer in a separate process using the non-superuser,
non-RLS-bypassing `qa_app` role. The parent waits for a controlled processing checkpoint
and SIGKILLs the child without cleanup handlers:

1. Between rows, after the first row's savepoint: no durable inventory rows or import outcome.
2. After importer flush, before outer commit: no durable inventory rows or import outcome.
3. After outer commit: both inventory rows and the successful import outcome persist.

Two subsequent real API imports reconcile to exactly two current positions (17 and 23 units),
a warehouse total of 40 and the same inventory-list API total. Retries update current positions;
each completed attempt has a separate ImportJob outcome. No durable in-progress ImportJob is
created by this synchronous importer before the outer transaction commits. Interrupted attempts
therefore disappear rather than remaining marked RUNNING. This is observed inventory-import
transaction behavior; it does not prove all entity/connector import paths have the same semantics.

### Background jobs

Real ARQ workers execute the application's `sync_connection` and connector mapping against
PostgreSQL. Only Salesforce HTTP is synthetic; the worker result, database writes, queue,
processes and errors are not mocked successful responses.

- A queued job survives Redis termination/restart from its AOF without rebuilding the queue.
- A worker is killed while the actual connector request is executing and ImportJob is RUNNING.
- Redis restarts from AOF; a replacement worker recovers the interrupted job on attempt two.
- The same queue identity is deduplicated; redelivery under a new identity retains one supplier
  and creates a separate completed sync outcome, rather than duplicating the business record.
- Persistent synthetic upstream connection failure ends at five attempts with FAILED ImportJob,
  error summary, retry count and ERROR connection state; no supplier is imported.
- The worker's actual PostgreSQL backend connection is terminated, then the same queued job
  retries on a new connection and finishes successfully on attempt two with one supplier.

The test worker lease timeout is shortened to two seconds; production settings are unchanged.
This proves the named local connector scenarios, not hosted Redis backup guarantees, outage
recovery objectives, real Salesforce validation or idempotency of every other job type.

## Gate and tests

The prerequisite resolver requires every named PostgreSQL fault case. Missing, skipped or
blocked cases cannot pass; a failed case produces FAIL. All 12 QA harness tests passed,
including the original secret-redaction and fail-closed tests. AI-001/AI-003 are unchanged.

The development fault run `fault-development-20261010T142858Z` passed 395 tests with one
Redis integration skip because the standalone development invocation did not start the
shared Redis fixture. This partial development run is not used as final release evidence.

Final command: `backend/.venv/bin/python tools/qa/health.py --postgres`.

Final run: **`20261010T143131Z-f4fb01`**. Complete counts: **822 entries,
794 passed, 0 failed, 4 blocked, 24 skipped**. Overall **FAIL**, release **NOT READY**,
process exit **1**. Full report and JUnit/browser/scenario evidence are retained under
`.local/qa/runs/20261010T143131Z-f4fb01/`.

- PostgreSQL backend: 397 passed, no skips or failures.
- SQLite backend: 373 passed, 24 skipped. All 24 database-specific skipped cases have
  passing PostgreSQL equivalents in this same run, including the six new fault cases.
- Browser: 12 passed. Original AI-001 and AI-003 both passed unchanged.
- QA harness: 12 passed (run separately, not added to the 822-entry report).
- Every baseline test ID remains present; no baseline failure was converted into a skip.
- Frontend source was not affected; no additional TypeScript/lint/build run was needed.
- One pre-existing Starlette deprecation warning remains.

| Original blocker | Final status | Evidence or remaining need |
| --- | --- | --- |
| JOB-001 | PASS (local connector fault scope) | Three PostgreSQL subprocess fault cases; limitations above |
| IMPORT-ATOMIC-001 | PASS (inventory import scope) | Three PostgreSQL kill-point/retry cases |
| HOST-001 | BLOCKED | Verified staging deployment/revision and synthetic accounts |
| SSO-001 | BLOCKED | WorkOS staging lifecycle access and controlled inboxes |
| AI-LIVE-001 | BLOCKED | Staging provider configuration and observed provider execution |
| VISUAL-REVIEW-001 | BLOCKED | Human review/sign-off against the staged revision |

Compared with baseline: 12 added entries (six cases in two database phases), two local
blockers resolved, zero failed tests. Six additional SQLite skips are explicit platform
requirements, each covered by its PostgreSQL PASS; no existing assertion was removed.
The fail-closed gate correctly rejects release while hosted prerequisites remain missing.

**Verdict: not ready to approve a hosted pilot yet.** The isolated recovery evidence is
stronger; hosted user journeys, identity lifecycle, real-provider safety and human review
still require actual staging evidence. No production-readiness claim is made.

## Outstanding access and approval

- A verified staging deployment URL, hosting environment, Git revision/build ID and migration revision.
- Explicitly synthetic test organizations and controlled admin/restricted-user test accounts.
- WorkOS staging application/organization access and controlled invitation inboxes.
- A staging external AI provider project, model and test budget, configured through secure settings;
  actual provider request evidence is required. Deterministic SKU/delivery responses do not qualify.
- A named human reviewer to approve desktop/mobile layouts and states against the exact staged revision.

No passwords or API keys should be supplied in chat or reports. See HOSTED_PILOT_REVIEW.md
for detailed lifecycle, workflow, external-provider and human review steps.
