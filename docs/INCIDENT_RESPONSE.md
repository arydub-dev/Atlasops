# Incident response (RC3)

## Severity

| Severity | Definition | Response |
| --- | --- | --- |
| Critical | Data loss, auth bypass, all tenants down, billing double-charge | Page immediately; war room |
| High | Single-tenant outage, sync queue down, webhook failures, elevated 5xx | Respond < 1h |
| Medium | Degraded latency, partial connector failure | Business hours |
| Low | Cosmetic / docs | Backlog |

## First 15 minutes

1. Check `/health/ready` and `/health/live` on API  
2. Confirm worker process alive (`arq` / Render worker logs)  
3. Confirm Redis + Postgres from managed console  
4. Grab `X-Request-ID` from failing client / logs  
5. Check `stripe_webhook_total` and `connector_enqueue_total` on `/metrics`  

## Common playbooks

### API not ready (`not_ready:db`)

- Managed DB status / connection limit  
- Recent migration failure → rollback image; `alembic downgrade` only after staging proof  

### API not ready (`not_ready:redis`)

- Redis restart / maxmemory  
- Sync will 503 until Redis returns — do not enable `CONNECTOR_SYNC_INLINE` in prod  

### Worker not processing

- Restart worker service  
- Inspect ARQ queue keys  
- Re-enqueue failed connection syncs after fix  

### Stripe webhook failures

- Verify `STRIPE_WEBHOOK_SECRET`  
- Replay from Stripe dashboard (idempotent via `stripe_events`)  

### Suspected tenant leak

- Freeze affected orgs  
- Capture request IDs + audit_logs  
- Confirm RLS GUC + app filters in logs  

## Communications

- Design partners: status email within 1 hour for High+  
- Paid pilots (when approved): contractual status page / email per MSA  

## Post-incident

Write short report: timeline, root cause, blast radius, fix, follow-ups. Store under `docs/reports/incidents/`.
