# Vercel + Render + Upstash supervised pilot deployment

Status: NOT VERIFIED. User-selected architecture (2026-09-30): Vercel frontend at https://www.atlasops.online (atlasops.online redirects here); Render Docker API, Managed PostgreSQL and dedicated ARQ worker; Upstash Redis; WorkOS; Stripe; Salesforce Developer Edition; Sentry email/Slack destinations. Naming below is proposed, not evidence that resources exist.

## Environment routing

| Input | Staging | Production |
| --- | --- | --- |
| Frontend | https://staging.atlasops.online | https://www.atlasops.online |
| API custom domain | https://api-staging.atlasops.online | https://api.atlasops.online |
| WorkOS redirect | https://api-staging.atlasops.online/api/v1/auth/callback | https://api.atlasops.online/api/v1/auth/callback |
| Stripe | test keys/prices/webhook | test validation first; live only after acceptance |
| Database/Redis | dedicated staging resources | independent production resources |

The API must use a same-site custom domain for the current Secure/SameSite=Lax host-only session cookie. Set NEXT_PUBLIC_API_URL to the matching API origin and NEXT_PUBLIC_SITE_URL to the frontend origin. Fetch already includes credentials. CORS_ORIGINS and FRONTEND_URL must equal the exact frontend origin. Avoid arbitrary Vercel preview origins for authenticated staging; assign a stable staging custom domain. Do not change cookies to SameSite=None as a workaround without reviewing the security design.

## Release sequence

1. Obtain the actual Git repository and release commit; push these changes and require CI to pass. This local directory currently has no Git remote. Disable auto-deploy in Vercel/Render until the release gates are configured. Render's template explicitly disables auto-deploy.
2. Import `render.yaml` as the staging template only. Review region and paid compute selection; the template does not purchase resources here. Render Managed PostgreSQL must have private-only connectivity (`ipAllowList: []`). Use the returned private hostname, not a guessed URL. Do not import over existing services without mapping names and preserving existing data.
3. Create a dedicated Upstash staging database. Use the native TCP TLS `rediss://` connection string as REDIS_URL for API/worker; do not use REST URL/token variables. Choose an appropriate region and record command/connection limits and eviction policy. Execute `scripts/verify_queue.py` against staging before claiming ARQ compatibility. Observe reconnect, retry and worker heartbeat behavior under the selected service limits.
4. Build the backend image from the release commit. In a **dedicated trusted migration environment** with Render database network access, provide only migration secrets. Run `DATABASE_URL="$MIGRATION_DATABASE_URL" alembic upgrade head`, then run `python scripts/provision_runtime_role.py` from the repository root using the backend environment. Never supply MIGRATION_DATABASE_URL to the public API or worker. The exact migration runner/network access remains to be provisioned; do not use production secrets in local development. Keep database backup/restore access independent of the runtime account.
5. Set DATABASE_URL on API/worker to the restricted role. Set the same per-environment SESSION_SECRET and CREDENTIALS_ENCRYPTION_KEY on both so job signatures and encryption match. Configure every `sync: false` input in the Render template. Add optional OPENAI_API_KEY/model only when approved for the pilot data. Start API with the Docker command in the template; start worker with `arq app.worker.WorkerSettings`. No application process runs migrations.
6. In Vercel set **Root Directory = frontend**, Framework = Next.js, Node = 22, install = `npm ci`, build = `npm run build`; use `frontend/vercel.json`. The repository-root experimental multi-service `vercel.json` is a legacy alternative and must not control this project. Set NEXT_PUBLIC_DEV_LOGIN=false and the API/site origins above. Do not put backend credentials in Vercel frontend variables.
7. Add DNS records exactly as the provider dashboards specify, verify certificates for frontend/API, and configure WorkOS callback/logout origins. Verify unauthenticated APIs reject access, login sets the API-host cookie, frontend credentialed requests work, CSRF rejects unrelated origins, and logout revokes the session.
8. Configure Stripe test product/price IDs and signed webhook at API origin `/api/v1/billing/webhooks/stripe`. Run successful payment, failure, retry, cancellation, duplicate/out-of-order event and recovery cases. Preserve provider event IDs as evidence, never secrets/card data.
9. Configure Salesforce Developer Edition credentials in the tenant connector UI. Verify supported Account-to-Supplier synchronization, tenant boundaries, retries and source-total reconciliation. Dynamics/UPS remain beta and NOT VERIFIED until separately tested.
10. Configure Sentry and actual alert destinations. Generate a controlled staging error, record event receipt and notification receipt separately. Scrape authenticated `/metrics`, monitor readiness and ARQ heartbeat, configure database/Redis provider alerts. Do not send customer data in test alerts.
11. Enable Managed PostgreSQL backup/PITR features appropriate to the chosen plan, document retention/encryption/access, restore into a separate database, connect a staging app and verify tenant visibility and sample data. Record timestamps; do not infer recovery from plan features.
12. Run full staging browser journeys and representative staging load. Only after gates pass, repeat the release sequence with independent production resources and explicit production configuration. Do not point staging at production data.

## Rollback

Stop new onboarding and pause connector writes when investigating data integrity. Redeploy the previous known-good API/worker/frontend commit only if compatible with current schema. Prefer additive forward fixes. Do not run blanket Alembic downgrades; 0016 downgrade deletes sales inquiries. For data recovery, restore to a new database, verify and then switch connections under controlled maintenance. Keep encryption keys recoverable separately.

## Sources

Reviewed official [Render Blueprint reference](https://render.com/docs/blueprint-spec), [Vercel project configuration](https://vercel.com/docs/project-configuration) and [Upstash Redis compatibility](https://upstash.com/docs/redis/overall/compatibility). Their documented features are not proof that this application's deployed integrations pass.

Observed 2026-09-30: one HTTPS request followed the apex redirect to https://www.atlasops.online/ and returned HTTP 200 with certificate verification successful. This does not verify the deployed code version, authenticated app, API, or ownership of provider resources. Keep the observed canonical frontend origin in FRONTEND_URL, CORS_ORIGINS and NEXT_PUBLIC_SITE_URL.
