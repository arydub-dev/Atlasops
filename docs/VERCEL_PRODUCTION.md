# Vercel production migration — 2026-10-01

The user selected Vercel for application hosting. Render is no longer the deployment target. No Render service was created. This supersedes the provider choice in HOSTED_DEPLOYMENT.md; its security and release gates still apply.

## Current evidence

Release 88675d6 passed all six GitHub CI jobs. This does not verify Vercel deployment, production provider settings, or customer journeys. Dashboard access is currently blocked by Vercel login.

## Preserve and inspect the existing deployment

Before changing project settings, record its team/project, Git branch, root directory, deployed commit, domains, function routing, runtime settings and environment-variable names (never values in reports). The repository contains a root experimentalServices configuration and a frontend-only configuration. Determine which is active before replacing either. Do not merge or promote blindly: main may already auto-deploy.

## Required architecture work

- Keep Next.js and FastAPI on Vercel. Confirm /api/v1 routing and health probes on the existing project; use the supported FastAPI runtime. If separate projects are needed, keep API and frontend on same-site custom domains for secure cookies.
- Reuse existing managed PostgreSQL if suitable. Otherwise choose a Marketplace integration after reviewing pricing. Set DATABASE_URL explicitly to a restricted, non-superuser, non-BYPASSRLS runtime role using the provider pooler. Keep migration-owner credentials in a separate controlled migration environment. Never run migrations or seed routines from a public endpoint or build preview.
- Redis remains necessary for distributed rate limiting. Reuse or provision dedicated staging/production Redis with TLS. A Redis database alone does not execute queued jobs.
- ARQ currently requires a persistent worker and is NOT operational just by deploying the API on Vercel. Replace its transport and scheduler with a durable serverless execution design before enabling connectors/scheduled workflows. Vercel Queues has Python support but is beta; assess availability and service limits. Preserve tenant signatures, retries, idempotency, failure records, and bounded execution. Verify duplicate delivery, timeout recovery, provider pagination and cron authentication. Do not replace durable processing with unawaited background tasks or enable inline sync in production.
- Verify platform request/response limits against imports, document uploads and exports. Larger files need authenticated direct-to-object-storage uploads, file validation and asynchronous ingestion; do not promise the current 15 MB API upload allowance works through Vercel.
- Configure WorkOS, Stripe, Sentry, email, and connector sandbox credentials in environment-scoped settings. Staging must not use production data or production provider keys. Configure stable preview/staging domains and protection.
- Run real hosted authentication, tenant-isolation, Stripe lifecycle, Salesforce reconciliation, queue recovery, alert receipt, backup restore and representative load checks before production promotion.

## Local changes in this follow-up

Added deployment ignore files at root/frontend/backend to exclude credentials, database dumps, Redis snapshots, logs and build caches. Prefer POSTGRES_URL over explicitly unpooled fallback aliases when DATABASE_URL is absent. DATABASE_URL remains authoritative to prevent overriding an explicitly configured runtime role. Tests cover both precedence cases.

## Official references

- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/limitations
- https://vercel.com/docs/queues

Status: NOT production ready. Dashboard inspection, serverless job migration and hosted validation are outstanding.
