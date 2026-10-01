# CI follow-up — 2026-09-30

Release PR: https://github.com/arydub-dev/Atlasops/pull/1
Initial CI: https://github.com/arydub-dev/Atlasops/actions/runs/36761564858

## Verified remote results for 9909531

- PASS: PostgreSQL backend tests and Alembic/RLS job.
- PASS: frontend lint/typecheck/build job.
- PASS: browser smoke job (10 passed, 6 hosted checks skipped).
- PASS: production container builds.
- FAIL: SQLite job at dependency audit, after its pytest step passed.
- FAIL: Gitleaks action, unexpected exit 1. Detailed logs require authentication.

## Corrective changes prepared locally

- PyJWT 2.14.0 has CVE-2026-101918; upgraded to patched 2.15.0.
- Current pip-audit after upgrade: no known vulnerabilities.
- Full local SQLite suite after upgrade: 274 passed, 19 skipped.
- Security checkout now fetches full history. The official Gitleaks action scans the base parent through head, unavailable with the previous shallow checkout. This is a probable cause of its exit 1; remote logs and rerun must confirm resolution.
- Official checksum-verified Gitleaks 8.30.1: no leaks in fetched Git history or explicit PR range 51c491c^..9909531. No allowlist or scan bypass added.

The corrective changes are not yet published or remotely verified. The temporary GitHub token was revoked by the user. Restore authentication through gh auth login --hostname github.com --web; do not share credentials in chat.

Render remains on initial repository selection. No paid infrastructure was created. Hosted identity, billing, connectors, Redis jobs, alerts, recovery and load validation remain outstanding. This release is not approved for paying customers.
