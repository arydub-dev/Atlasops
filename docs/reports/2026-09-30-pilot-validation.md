# Pilot validation evidence — September 30, 2026

Release is a local source snapshot without Git history/remote/release SHA. Nothing here certifies a hosted production deployment.

## Executed checks

| Command/check | Status | Actual result |
| --- | --- | --- |
| `cd backend && .venv/bin/python -m pytest -q --tb=short` | PASS | 274 passed, 19 skipped, 1 deprecated HTTP constant warning; 6.68s |
| Same suite with `SUPPLY_CI_POSTGRES=1`, restricted test DATABASE_URL, startup create_all disabled | PASS | 292 passed, 1 skipped, same warning; 28.34s |
| `pytest -q tests/test_salesforce_arq_redis.py` with dedicated local Redis/PostgreSQL | PASS | 1 passed; Salesforce HTTP mocked |
| `ENVIRONMENT=test REDIS_URL=... python scripts/verify_queue.py` | PASS | Native Redis enqueue, first-attempt retry, worker execution, result retrieval; isolated queue |
| `npm run lint` / `npm run typecheck` / `npm run build` | PASS | Next.js 15.5.26 production build completed after patching brace-expansion |
| `PLAYWRIGHT_PORT=3317 npm run test:e2e` against standalone build, temporary Chromium | PASS | 10 passed, 6 hosted-staging checks skipped; desktop + Pixel 7 viewport; 3.7s |
| `npm audit fix` compatible transitive update/audit | PASS | Two packages changed; 0 known vulnerabilities after new high-severity brace-expansion advisory |
| `pip-audit -r backend/requirements.txt` under Python 3.12 | PASS | No known vulnerabilities found |
| detect-secrets source scan | PASS | Reviewed findings are test fixtures/documented local defaults; no real secret confirmed; Git history unavailable |
| `alembic upgrade head` on fresh PostgreSQL after legacy guard | PASS | Through 0016_sales_leads |
| Upgrade existing 0015 schema with synthetic user row | PASS | 0016 applied; existing row preserved |
| Upgrade populated legacy 77ea schema | PASS | Expected refusal before any DROP; synthetic row and previous revision preserved |
| Local dump → empty restored DB → migrations → app | PASS | 1000 shipments and 1025 suppliers recovered; unscoped shipments=0; app readiness/dashboard HTTP 200 |
| Vercel JSON / Render YAML + role-separation assertions | PASS | Syntax and local assertions only; provider blueprint validation/deployment NOT VERIFIED |
| Public HTTPS read-only request | PASS | Apex 308 → https://www.atlasops.online/ HTTP 200; certificate verification result 0 |
| Container image build and OS/image vulnerability scans | NOT VERIFIED | Local Docker daemon unavailable; build job added to CI, not run remotely |
| Actual WorkOS/Stripe/Salesforce/Upstash/Sentry | NOT VERIFIED | Provider names supplied; deployment credentials/integration execution not available |

One skipped PostgreSQL test is the Redis integration, which was run separately. SQLite skips correspond to PostgreSQL/Redis-only tests. Browser smoke uses intercepted API responses for route/inquiry behavior; no authenticated hosted journey is implied. Dependency audits are point-in-time results, not a guarantee of absence of all vulnerabilities.

## Measured synthetic baseline

Command: `DATABASE_URL=<restricted local atlasops_pilot_benchmark> backend/.venv/bin/python scripts/local_pilot_baseline.py`.

Dataset: 1 organization, 1000 shipments, 25 suppliers, 10 warehouses, 100 products, then import 1000 additional suppliers. Real local PostgreSQL/restricted runtime role; TestClient in-process requests, sequential, 20 samples per read endpoint, no concurrent load.

| Operation | Measurement |
| --- | --- |
| Shipment list (limit 25) | p50 8.60ms; p95 9.69ms |
| Mission Control | p50 37.28ms; p95 38.68ms |
| CSV import 1000 supplier rows | 702.00ms; all 1000 imported |

These exclude network/TLS, browser rendering, multi-user contention, remote Redis, external connectors and AI providers. They are NOT staging load-test evidence or a scalability/SLA claim. The script refuses remote databases and any database name except the dedicated local benchmark database.

## Recovery limits

The new local drill connected the application to restored data and checked tenant visibility. It did not verify Render automated backups, off-host encryption/retention, managed PITR, full WorkOS login, or a production RTO/RPO. No recovery time is claimed.

## Access state and next execution

Render account verified and signed in. New Web Service screen requests a Git provider connection; no repository is connected there. Connect the correct repository, publish this source and run CI on a release commit before provisioning staging. Do not overwrite or deploy an older remote snapshot while these local changes are absent from it.
