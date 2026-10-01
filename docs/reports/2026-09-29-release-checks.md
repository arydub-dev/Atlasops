# Local release checks — 2026-09-29

Environment: local macOS workstation, Python 3.12, PostgreSQL 16, restricted NOSUPERUSER/NOBYPASSRLS test role, isolated Redis. Tests contain synthetic data only. Test-role TRUNCATE permission exists solely for test cleanup; production provisioning does not grant it.

| Check | Result | Scope/limitation |
| --- | --- | --- |
| Backend full SQLite suite | 253 passed, 19 skipped | PostgreSQL/Redis-specific checks skipped here |
| Backend full PostgreSQL suite | 271 passed, 1 skipped | Real FORCE RLS; Redis queue check run separately |
| Final Stripe regression suite after two added tests | 11 passed | Real PostgreSQL, mocked Stripe API; positive activation and wrong-customer rejection included |
| Redis/ARQ integration | 1 passed | Actual Redis/worker, mocked Salesforce HTTP |
| Fresh migrations | PASS through 0016_sales_leads | Isolated UTF-8 PostgreSQL database |
| Frontend lint/typecheck | PASS | Next.js 15.5.26 / TypeScript |
| Frontend production build | PASS | 59 static pages generated |
| Chromium smoke | 5 passed, 3 staging skipped | Local production build; API interception for auth/inquiry |
| npm audit | 0 known vulnerabilities | Fresh lockfile install; advisory snapshot only |
| pip-audit requirements | No known vulnerabilities | Python 3.12 requirement resolution; advisory snapshot only |
| pip check | No broken requirements | Installed backend environment |
| Compose merge/configuration | PASS | Only proxy ports 80/443 published, migration/runtime URLs distinct |
| Secret scan | Reviewed, no real secret confirmed | detect-secrets source scan; findings were dummy fixtures, documented local defaults and generated TypeScript hashes; no Git history available |
| Docker container execution | NOT TESTED | Local Docker daemon unavailable |
| Hosted provider journeys / load / soak / alert receipt | NOT TESTED | Deployment/provider/operational inputs absent |

## Reproduction

Backend: `cd backend && .venv/bin/python -m pytest -q --tb=short`.

PostgreSQL: migrate an isolated database as owner, grant restricted test role DML plus TRUNCATE for fixture cleanup, then set `SUPPLY_CI_POSTGRES=1`, `DATABASE_URL` to that role and `ALLOW_CREATE_ALL_ON_STARTUP=false` before running pytest. Never point test cleanup at a customer database. The generic suite uses unavailable Redis to avoid sharing rate counters across independent tests; run `tests/test_salesforce_arq_redis.py` separately with an isolated `REDIS_URL`. This separate check is now included in CI.

Frontend: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build`; copy `.next/static` and `public` into the standalone output, install Playwright Chromium, run `npm run test:e2e`. Staging URL is deliberately unset for local smoke. Hosted smoke does not certify actual signup or payments.

Audits: `npm audit --audit-level=high` and `pip-audit -r backend/requirements.txt` with Python 3.12. Scans are point-in-time checks, not proof of absence of all security defects.

The initial all-tests-with-Redis run failed because independent tests shared real rate-limit counters. The isolated PostgreSQL run and dedicated Redis check passed; no production rate limiter was disabled to obtain passing results. Earlier dependency attempts exposed a telemetry incompatibility and a stale nested PostCSS lock entry; both were corrected before the reported passes.

Remote GitHub Actions was not run from this source snapshot. The updated workflow must run against the actual release commit before deployment. Historical September 22 restore evidence remains in DISASTER_RECOVERY.md; it is not a new hosted restore result.
