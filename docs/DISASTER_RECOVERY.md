# Disaster Recovery & Backups — Supply v2

## RPO / RTO targets (single-region SaaS)

| Metric | Target |
| --- | --- |
| RPO | ≤ 24 hours (daily backups); ≤ 1 hour with continuous WAL if enabled |
| RTO | ≤ 4 hours for database restore + app redeploy |

## PostgreSQL

1. Use managed Postgres (Render / RDS / Neon / Cloud SQL) with automated daily backups.
2. Retain at least 7 daily + 4 weekly snapshots.
3. Before major migrations, take a manual snapshot.
4. Restore procedure:
   - Provision a new database from snapshot
   - Point `DATABASE_URL` at the restored instance
   - Run `alembic upgrade head` if the snapshot predates latest migrations
   - Verify `/health/ready` and a sample tenant query
   - Cut DNS / platform traffic to the restored environment

## Redis

- Redis holds job queues only (ARQ). Loss is acceptable; reconnect and re-enqueue failed syncs from `connections` with `status=error`.
- Do not store session authority solely in Redis — sessions are in Postgres `sessions` table.

## Object / file storage

- When object storage is added for imports, enable versioning + cross-region replication.
- Until then, import payloads are transient; retain `import_jobs` metadata in Postgres.

## Secrets

- Rotate `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`, WorkOS, and Stripe keys via your secrets manager.
- After rotating `CREDENTIALS_ENCRYPTION_KEY`, re-encrypt connector credentials (or force reconnect).

## Application recovery

1. Redeploy backend + frontend from the last known-good image/tag.
2. Confirm CI green on the release commit.
3. Run smoke: login → switch org → list shipments → connector health.
4. Announce incident timeline in the status page / customer channel.

## Restore drill evidence (required before paid pilot)

Document each restore exercise:

| Field | Value |
| --- | --- |
| Date | |
| Environment | staging / production |
| Snapshot ID | |
| Restore started | |
| App healthy (`/health/ready`) | |
| Sample tenant query OK | |
| Measured RTO | |
| Operator | |

Do not claim RTO ≤ 4h until at least one timed drill is recorded.

## Scripts

- Schema: `cd backend && alembic upgrade head`
- Local demo disruption overlay: `python -m app.cli force-disruption --org "Demo Manufacturing Co"`

## 2026-09-22 local verification

PASS: PostgreSQL 16 custom-format dump restored into a separate empty database. Two synthetic organizations and their shipments were recovered. Runtime role saw zero unscoped shipments and exactly one shipment under each tenant context. Schema revision: `0016_sales_leads`. Dump + database creation + restore + verification: 1.11 seconds on this workstation.

This is **not** a hosted RTO, off-host backup test, or recovery of production data. Managed backup schedule, encrypted remote storage, retention, recovery credentials and a full application recovery drill remain NOT TESTED. Preserve encryption keys separately; losing them makes encrypted connector credentials and sales inquiries unreadable.

The restore helper now refuses nonempty targets and does not print the database URL. Use `scripts/restore_drill.sh` only with a newly created isolated database. Retain evidence of row counts, per-tenant visibility and application login after restoring. Never run restore into the active application database.

## 2026-09-30 local application recovery

PASS: isolated synthetic dump restored into a new empty PostgreSQL database using scripts/restore_drill.sh. A restricted application role saw zero unscoped shipments, 1000 tenant-scoped shipments and 1025 suppliers. The restored application returned 200 for readiness and authenticated Mission Control. Managed/off-host backup and real WorkOS recovery remain NOT VERIFIED. See reports/2026-09-30-pilot-validation.md.
