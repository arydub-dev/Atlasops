# Operations runbook (RC2)

**Full manual:** [`OPERATIONS_MANUAL.md`](./OPERATIONS_MANUAL.md)

## Deploy

1. `alembic upgrade head` (never `create_all` in staging/production)
2. Deploy API + worker + frontend together when connector/queue code changes
3. Set secrets before first boot (`docs/STAGING.md`, `docs/DEPLOYMENT.md`)
4. Verify `/health/ready` and worker process consuming `arq:queue`

## Rollback

1. Redeploy previous container images (API + worker + web)
2. If a migration must be reversed: `alembic downgrade -1` (test on staging first)
3. Stripe/WorkOS config is external — do not roll back webhook endpoints without dual-write

## Secrets rotation

| Secret | Steps |
| --- | --- |
| SESSION_SECRET | Rotate → all sessions invalidate → users re-login |
| CREDENTIALS_ENCRYPTION_KEY | Re-encrypt connector credentials before discarding old key |
| WORKOS / Stripe keys | Update dashboard + env; verify webhook signatures |
| METRICS_TOKEN | Update scrapers and API env atomically |

## Worker recovery

- Worker crash: process supervisor restarts `arq app.worker.WorkerSettings`
- Redis flush: in-flight jobs lost; connections stuck in `syncing` → re-enqueue sync
- Queue depth: alert if ARQ queue grows unboundedly

## Scaling

- Stateless API replicas OK with shared Postgres + Redis
- Scale workers horizontally for connector throughput
- Postgres is the primary capacity bottleneck

## Health

| Path | Meaning |
| --- | --- |
| `/health/live` | Process up |
| `/health/ready` | DB reachable; Redis reachable when `CONNECTOR_SYNC_INLINE=false` |
| Connection `health` | Last connector probe |
| `/metrics` | Prometheus (Bearer `METRICS_TOKEN` on staging/production) |

See also: `docs/DISASTER_RECOVERY.md`, `docs/STAGING.md`, `docs/MONITORING.md`, `docs/INCIDENT_RESPONSE.md`, `docs/ENV_MATRIX.md`.
