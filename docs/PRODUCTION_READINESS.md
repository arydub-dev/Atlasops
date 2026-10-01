> Current audit: [LAUNCH_REPORT.md](LAUNCH_REPORT.md). Historical snapshot below.

# ATLASOPS Production Readiness

**Updated:** 2026-08-12  
**Related:** [PRODUCTION_AUDIT.md](./PRODUCTION_AUDIT.md) · [RC3_RELEASE_REPORT.md](./RC3_RELEASE_REPORT.md) · [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md)

---

## Status snapshot

| Stage | Status |
| --- | --- |
| Local demo | **LOCAL DEMO READY** |
| Private design partner (staging) | **NOT READY** — RC3 validation: Gates 1+3 NOT TESTED; Gate 4 Postgres API isolation **PASS** (fixed) |
| Paid pilot | **NOT READY** |
| General production SaaS | **NOT READY** |

**RC3 PASS RATE:** 5/12 (42%). See [RC3_RELEASE_REPORT.md](./RC3_RELEASE_REPORT.md).

---

## What was fixed / hardened (cumulative)

1. Schema drift migrations + `ensure-schema` CLI  
2. `./start.sh` portable launcher (inline sync for local)  
3. Health live vs ready; Redis optional only when `CONNECTOR_SYNC_INLINE=true`  
4. Mission Control / enterprise endpoints unblocked after schema reconcile  
5. AI provider abstraction; simulation prompts do not invent numbers  
6. **CSRF Origin/Referer middleware** for cookie mutations (`CSRF_ORIGIN_CHECK`)  
7. **Production compose** requires secrets; closes DB/Redis/API/FE ports  
8. Boot fails closed on missing WorkOS, metrics token, billing enforce, CSRF, non-localhost FRONTEND_URL/redirect in production  
9. Sentry SDK dependency + worker init  
10. Frontend App Router error/loading/global-error/not-found; analytics ErrorState+retry  
11. `force-disruption` CLI for demo sales path  
12. Simulation plan feature enforcement when billing enforce is on  
13. **RC3 validation:** empty Postgres Alembic+RLS proven; backup/restore proven with superuser dump; `create_organization` sets tenant GUC; **request-path GUC survives auth commit** (`after_begin` + `get_db_with_tenant` rebind)  

---

## Remaining blockers (must be proven live)

1. Working Docker/runtime + gitignored secrets → `docker-compose.prod.yml` health endpoints  
2. WorkOS AuthKit E2E on HTTPS  
3. Stripe test-mode checkout + live webhooks (FORCE RLS customer lookup fixed in 0013)  
4. One connector sandbox E2E through ARQ  
5. Sentry DSN events from API + worker  
6. Staging soak / load artifacts  
7. Document backup role must be BYPASSRLS/superuser (app-role `pg_dump` fails under FORCE RLS)  

---

## Deploy (production-like)

```bash
cp .env.example .env   # fill ALL required secrets — no defaults
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Local demo:

```bash
./start.sh
# Dev login: demo@example.com
# Optional: cd backend && DATABASE_URL=sqlite:///./dev.db python -m app.cli force-disruption
```

---

## Required production environment variables

See `.env.example` and `startup_checks.py`. Critical:

`DATABASE_URL`, `REDIS_URL`, `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`,  
`WORKOS_*`, `FRONTEND_URL`, `CORS_ORIGINS`, `METRICS_TOKEN`,  
`FEATURE_BILLING_ENFORCE=true`, `CSRF_ORIGIN_CHECK=true`,  
`SESSION_COOKIE_SECURE=true`, `CONNECTOR_SYNC_INLINE=false`,  
`ALLOW_CREATE_ALL_ON_STARTUP=false`, `NEXT_PUBLIC_DEV_LOGIN=false`

Optional but recommended: `STRIPE_*`, `SENTRY_DSN`, `OPENAI_API_KEY`
