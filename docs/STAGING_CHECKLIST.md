# Staging environment checklist (RC2)

Staging must closely match production. Use [`STAGING.md`](./STAGING.md) for setup.

## Services

- [ ] PostgreSQL 16 (non-superuser app role; RLS enabled)
- [ ] Redis 7 + ARQ worker (`arq app.worker.WorkerSettings`)
- [ ] API (`alembic upgrade head` on deploy; no `create_all`)
- [ ] Frontend (HTTPS)
- [ ] Reverse proxy TLS termination
- [ ] Render (or equivalent) includes Redis + worker (see `render.yaml`)

## Secrets / env

- [ ] `ENVIRONMENT=staging` (fail-closed same family as production)
- [ ] `SESSION_SECRET` (≥32 chars), `SESSION_COOKIE_SECURE=true`
- [ ] `CREDENTIALS_ENCRYPTION_KEY`
- [ ] `WORKOS_API_KEY`, `WORKOS_CLIENT_ID`, `WORKOS_REDIRECT_URI`, cookie password
- [ ] `STRIPE_SECRET_KEY` (test), `STRIPE_WEBHOOK_SECRET`, price IDs
- [ ] Connector sandbox credentials (SF, Dynamics, UPS)
- [ ] `FRONTEND_URL`, `CORS_ORIGINS` exact match
- [ ] `FEATURE_DEMO_SANDBOX=false`, `SEED_ON_STARTUP=false`
- [ ] `CONNECTOR_SYNC_INLINE=false`
- [ ] `FEATURE_BILLING_ENFORCE=true` for paid-pilot rehearsal
- [ ] `METRICS_TOKEN` set for production scrapers; recommended on staging

## Verify

- [ ] Session cookie: HttpOnly, Secure, SameSite=Lax; logout clears matching flags
- [ ] HTTPS-only browser access
- [ ] CORS allows only staging frontend origin with credentials
- [ ] CSP headers present
- [ ] Stripe webhook URL reachable; signature required; duplicate delivery safe
- [ ] WorkOS callback → org onboarding → dashboard
- [ ] Connector: OAuth → test → **queued** sync → worker completes → tenant data visible
- [ ] SSRF: configuring `base_url=https://127.0.0.1` is rejected
- [ ] `/health/ready` returns `checks.database` and `checks.redis`
- [ ] `/metrics` returns 404 without `Authorization: Bearer $METRICS_TOKEN`
- [ ] CSV import → dashboard → audit log
- [ ] API token create / use / revoke
- [ ] Benchmark: `python scripts/benchmark_api.py --auth --write-report`
- [ ] Alerts wired per `docs/MONITORING.md`

## Soak / DR

- [ ] 7–14 day soak; `scripts/soak_snapshot.py` samples in `docs/reports/soak_samples.jsonl`
- [ ] Restore drill Pass recorded in `docs/reports/RC3_RESTORE_DRILL.md`
