# Supply v2 — Operations Manual

**Audience:** SRE / DevOps / QA / Release Manager  
**Purpose:** Deploy, validate, operate, and certify staging for the first design partners.  
**Scope:** Human-operated staging. No new product features. No architecture redesign.

> Use this document as the single runbook. Related detail: `ENV_MATRIX.md`, `MONITORING.md`, `INCIDENT_RESPONSE.md`, `DISASTER_RECOVERY.md`, `STAGING_CHECKLIST.md`.

---

## Table of contents

1. [Staging deployment guide](#part-1--staging-deployment-guide)  
2. [External service configuration](#part-2--external-service-configuration)  
3. [Design partner onboarding](#part-3--design-partner-onboarding)  
4. [Operational checklists](#part-4--operational-checklists)  
5. [14-day soak test plan](#part-5--14-day-soak-test-plan)  
6. [Load test plan (k6)](#part-6--load-test-plan-k6)  
7. [Disaster recovery procedures](#part-7--disaster-recovery-procedures)  
8. [Monitoring & dashboards](#part-8--monitoring--dashboards)  
9. [Go / No-Go checklist (paid pilots)](#part-9--go--no-go-checklist-paid-pilots)

---

# Part 1 — Staging deployment guide

## 1.1 Infrastructure requirements

| Component | Minimum (design partners) | Notes |
| --- | --- | --- |
| Compute API | 1× 1 vCPU / 2 GB | Horizontally scalable later |
| Worker | 1× 1 vCPU / 1 GB | Same image as API; command `arq app.worker.WorkerSettings` |
| Frontend | 1× Next.js standalone / CDN | `NEXT_PUBLIC_API_URL` = public API |
| PostgreSQL 16 | 1 GB storage, daily backups | Non-superuser app role preferred for RLS |
| Redis 7 | 256 MB, `noeviction` | ARQ queue only |
| TLS reverse proxy | Caddy / Nginx / Traefik / cloud LB | Terminates HTTPS |
| Secrets store | 1Password / Doppler / cloud SM | Never commit `.env.staging` |
| Observability | Prometheus scrape + log drain | Grafana optional but recommended |

**Assumed hostnames (replace with yours):**

| Role | Example |
| --- | --- |
| App (frontend) | `https://staging.example.com` |
| API | `https://staging-api.example.com` |

## 1.2 DNS

```text
staging.example.com        → frontend LB / proxy
staging-api.example.com    → API LB / proxy
```

**Verify:**

```bash
dig +short staging.example.com
dig +short staging-api.example.com
```

## 1.3 HTTPS certificates

- Obtain certificates via ACME (Let’s Encrypt) on the reverse proxy, or managed certs on the cloud LB.
- Force HTTPS redirect; HSTS optional on staging.
- API and frontend must both be HTTPS (`SESSION_COOKIE_SECURE=true`).

**Verify:**

```bash
curl -sI https://staging-api.example.com/health/live | head -5
curl -sI https://staging.example.com/ | head -5
# Expect HTTP/2 or HTTP/1.1 200 and no certificate errors
openssl s_client -connect staging-api.example.com:443 -servername staging-api.example.com </dev/null 2>/dev/null | openssl x509 -noout -dates
```

## 1.4 Secrets & environment file

```bash
cp .env.staging.example .env.staging
# Fill every value. Never commit this file.
```

Generate secrets:

```bash
# SESSION_SECRET (≥32 chars)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# CREDENTIALS_ENCRYPTION_KEY (Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# WORKOS_COOKIE_PASSWORD (≥32 chars)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# METRICS_TOKEN
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Required staging values (fail-closed boot):**

| Variable | Required value |
| --- | --- |
| `ENVIRONMENT` | `staging` |
| `SESSION_SECRET` | unique ≥32 |
| `CREDENTIALS_ENCRYPTION_KEY` | set |
| `SESSION_COOKIE_SECURE` | `true` |
| `WORKOS_API_KEY` / `WORKOS_CLIENT_ID` | set |
| `WORKOS_COOKIE_PASSWORD` | non-default |
| `WORKOS_REDIRECT_URI` | `https://staging-api.example.com/api/v1/auth/callback` |
| `REDIS_URL` | set |
| `METRICS_TOKEN` | set |
| `SEED_ON_STARTUP` | `false` |
| `FEATURE_DEMO_SANDBOX` | `false` |
| `ALLOW_CREATE_ALL_ON_STARTUP` | `false` |
| `CONNECTOR_SYNC_INLINE` | `false` |
| `FEATURE_BILLING_ENFORCE` | `true` (recommended) |
| `TRUST_PROXY` | `true` (behind LB) |
| `FRONTEND_URL` / `CORS_ORIGINS` | exact frontend origin |
| `NEXT_PUBLIC_API_URL` | public API URL |
| `NEXT_PUBLIC_DEV_LOGIN` | `false` |
| Stripe test keys + webhook secret | if billing enabled |

See `docs/ENV_MATRIX.md`.

## 1.5 Deploy with Docker Compose (reference path)

From repository root:

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up --build -d
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging ps
```

**Verify each service:**

```bash
# Postgres
docker compose exec db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Redis
docker compose exec redis redis-cli ping   # PONG

# API live + ready (ready includes Redis when queue sync is on)
curl -fsS https://staging-api.example.com/health/live
curl -fsS https://staging-api.example.com/health/ready
# Expect: {"status":"ready","checks":{"database":"ok","redis":"ok"}}

# Worker process
docker compose logs worker --tail 50
# Expect arq worker started, no ConfigurationError

# Migrations applied (API command runs alembic upgrade head)
docker compose exec backend alembic current

# Frontend
curl -fsS -o /dev/null -w "%{http_code}\n" https://staging.example.com/
```

**Render alternative:** apply `render.yaml`, set all `sync: false` secrets in dashboard, confirm API `dockerCommand` runs Alembic, worker runs `arq app.worker.WorkerSettings`.

## 1.6 Reverse proxy (Caddy example)

```caddyfile
staging.example.com {
  reverse_proxy frontend:3000
}

staging-api.example.com {
  reverse_proxy backend:8000
}
```

**Verify CORS / cookies after auth:**

```bash
curl -sI -X OPTIONS https://staging-api.example.com/api/v1/auth/me \
  -H "Origin: https://staging.example.com" \
  -H "Access-Control-Request-Method: GET" | grep -i access-control
```

## 1.7 Security headers & CSP

Browse `https://staging.example.com` and API responses; confirm security middleware headers (see `app/core/security_headers.py`).

**Verify metrics gated:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://staging-api.example.com/metrics
# Expect 404 without token
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $METRICS_TOKEN" \
  https://staging-api.example.com/metrics
# Expect 200
```

**Verify OpenAPI off:**

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://staging-api.example.com/docs
# Expect 404 on staging
```

## 1.8 Backups (day 0)

1. Enable managed Postgres daily backups (retain ≥7 days).  
2. Take a manual snapshot after first successful migrate.  
3. Schedule weekly restore drill (`scripts/restore_drill.sh`).  

**Verify:**

```bash
# Platform-specific: confirm latest backup timestamp in managed console
# Record snapshot ID in ops log
```

## 1.9 Logging & monitoring (day 0)

1. Ship container stdout (JSON logs) to your log drain.  
2. Scrape `/metrics` every 15–30s with Bearer token.  
3. Import alert rules from Part 8 / `docs/MONITORING.md`.  
4. Optional: set `OTEL_EXPORTER_OTLP_ENDPOINT` for traces.

**Verify:**

```bash
python scripts/soak_snapshot.py --base-url https://staging-api.example.com
# Appends docs/reports/soak_samples.jsonl
```

## 1.10 Shutdown / restart drill

```bash
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging stop
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging start
curl -fsS https://staging-api.example.com/health/ready
docker compose logs worker --tail 20
```

---

# Part 2 — External service configuration

## 2.1 WorkOS (email-first enterprise SSO)

See also [AUTHENTICATION.md](AUTHENTICATION.md).

### Required accounts
- WorkOS account + AuthKit enabled  
- Production vs Staging WorkOS environments (use Staging for this stack)
- Customer IdP connections (Okta / Entra / Google Workspace / SAML / OIDC) configured **in WorkOS** — ATLASOPS UI never shows provider buttons

### Permissions / setup
1. Create Application → AuthKit.  
2. Copy **API Key** → `WORKOS_API_KEY`.  
3. Copy **Client ID** → `WORKOS_CLIENT_ID`.  
4. Redirect URI (exact):

```text
https://staging-api.example.com/api/v1/auth/callback
```

5. Set `WORKOS_REDIRECT_URI` to the same value.  
6. Set `WORKOS_COOKIE_PASSWORD` (≥32 random chars).  
7. Frontend after callback lands at `{FRONTEND_URL}/auth/callback` (session cookie already set by API).  
8. Link WorkOS organization IDs / domains for enterprise SSO discovery.

### Common mistakes
- Mismatched http/https or trailing slash on redirect URI  
- Using production WorkOS keys against staging hostnames  
- Leaving `NEXT_PUBLIC_DEV_LOGIN=true` on staging  
- `FRONTEND_URL` not matching the real browser origin (breaks post-login redirect)

### Verify
1. Open `https://staging.example.com/login`.  
2. Enter a work email → **Continue** (no Google/Microsoft/WorkOS buttons).  
3. Complete IdP login; land in onboarding or Mission Control.  
4. `curl -b cookies.txt https://staging-api.example.com/api/v1/auth/me` returns user JSON.  
5. Logout → `/auth/me` returns 401; protected UI redirects to login.  
6. Security → sessions / login history visible for admins.

---

## 2.2 Stripe Test Mode

### Required accounts
- Stripe account in **Test mode**  
- Products/Prices for Starter / Professional (monthly at minimum)

### Setup
1. Developers → API keys → `sk_test_…` → `STRIPE_SECRET_KEY`.  
2. Create Products + recurring Prices; copy price IDs into:

```text
STRIPE_PRICE_STARTER_MONTHLY=price_...
STRIPE_PRICE_PROFESSIONAL_MONTHLY=price_...
# optional annual / enterprise / AI credit prices
```

3. Developers → Webhooks → Add endpoint:

```text
https://staging-api.example.com/api/v1/billing/webhooks/stripe
```

   Events (minimum):  
   `checkout.session.completed`,  
   `customer.subscription.created`,  
   `customer.subscription.updated`,  
   `customer.subscription.deleted`,  
   `invoice.paid`,  
   `invoice.payment_failed`

4. Signing secret `whsec_…` → `STRIPE_WEBHOOK_SECRET`.  
5. Customer Portal enabled for test mode.  
6. `FEATURE_BILLING_ENFORCE=true` on staging.

### Common mistakes
- Live keys (`sk_live_`) on staging  
- Webhook pointing at localhost without Stripe CLI  
- Missing `STRIPE_WEBHOOK_SECRET` (API refuses boot if secret key set without it)  
- Price IDs from wrong Stripe account

### Verify
```bash
# Stripe CLI (optional local tunnel) or Dashboard → Send test webhook
# After checkout:
# - billing_accounts.stripe_customer_id set
# - organization plan/status updated
# - duplicate delivery does not double-reset AI credits
```

Manual: Owner → choose plan → Checkout (test card `4242…`) → return → dashboard access → Customer Portal opens.

---

## 2.3 Salesforce Sandbox

### Required accounts
- Salesforce Developer Edition or Sandbox  
- Connected App with OAuth

### OAuth configuration
1. Setup → App Manager → New Connected App.  
2. Enable OAuth; callback URL can be a placeholder if using password/refresh grants stored as connection credentials (Supply stores tokens on the Connection).  
3. Scopes (typical): `api`, `refresh_token`, `offline_access` (as offered by your org).  
4. Collect `client_id`, `client_secret`.  
5. In Supply connection config set `"sandbox": true` so token host is `test.salesforce.com`.  
6. Provide credentials via `PUT /api/v1/data/sources/{id}/config` (`credentials` + config).  

**Allowlisted hosts only** (`login/test.salesforce.com`, `*.salesforce.com`, `*.force.com`). Arbitrary URLs are rejected (SSRF protection).

### Common mistakes
- Using production login URL against sandbox users  
- Missing security token on password grant  
- Setting `base_url` to an internal IP (rejected)  
- Expecting sync to finish in HTTP response — sync is **queued**; worker must be running

### Verify
1. Create Salesforce connection → configure credentials → **Test** succeeds.  
2. **Sync** returns `status: queued` + `job_id`.  
3. Worker logs show job completion; connection `health` healthy; imported rows visible for tenant.  
4. Audit/pipeline shows import job.

---

## 2.4 Microsoft Dynamics 365 Business Central Sandbox

### Required accounts
- Azure AD tenant + app registration  
- Business Central sandbox environment  
- Admin consent for API permissions

### Setup
1. Azure Portal → App registrations → New.  
2. API permissions: Dynamics 365 Business Central → application permissions as required (e.g. `API.ReadWrite.All` or least privilege your tenant allows) → Grant admin consent.  
3. Certificates & secrets → client secret.  
4. Note `tenant_id`, `client_id`, `client_secret`, BC `environment`, `company_id` (if known).  
5. Supply credentials + config (`environment`, optional `company_id`).  
6. Default API host: `https://api.businesscentral.dynamics.com` (allowlisted).

### Common mistakes
- Delegated permissions without a user context when using client credentials  
- Wrong BC environment name  
- Forgetting admin consent  
- Custom `api_base` outside `*.dynamics.com` (rejected)

### Verify
Same pattern as Salesforce: Test → Sync queued → worker completes → tenant data + job status.

---

## 2.5 UPS (CIE / test)

### Required accounts
- UPS Developer account  
- CIE (Customer Integration Environment) credentials when available

### Setup
1. Obtain `client_id` / `client_secret` for OAuth client-credentials.  
2. Prefer CIE base `https://wwwcie.ups.com` in connection `base_url` (allowlisted) or use `UPS_BASE_URL` / `UPS_CLIENT_*` env defaults.  
3. Store secrets on the Connection credentials (encrypted at rest).

### Common mistakes
- Using production tracking endpoints with CIE credentials  
- Free-form tracking URLs to non-UPS hosts (SSRF reject)  
- No worker → sync stuck queued/syncing

### Verify
Test connection → enqueue sync → tracking events appear for known test tracking numbers (per UPS CIE docs).

### FedEx
FedEx is **not** a shipped connector in Supply v2. Do not document or promise FedEx until a connector exists. Use UPS CIE for carrier validation.

---

# Part 3 — Design partner onboarding

## Checklist (first customer)

### Before kickoff
- [ ] Staging Go items for design partners complete (Part 9 subset)  
- [ ] Partner NDA / DPA signed  
- [ ] Named champion + 1–2 operators identified  
- [ ] Sandbox systems available (or CSV-only pilot agreed)

### Session 1 — Org & access (60 min)
- [ ] Partner owner signs in via WorkOS  
- [ ] Organisation created (name/slug)  
- [ ] Plan selected; Stripe Checkout completed (test or agreed commercial terms)  
- [ ] Webhook confirmed org active  
- [ ] Invite 1–2 teammates; they accept; RBAC verified (viewer cannot manage tokens)  
- [ ] Success: all users reach Mission Control

### Session 2 — Data (60–90 min)
- [ ] Choose path: CSV import and/or one connector sandbox  
- [ ] CSV: suppliers or shipments sample → preview → commit → audit log row  
- [ ] Connector: configure → test → sync queued → data visible  
- [ ] Mission Control / shipments reflect imported data  
- [ ] Success: partner sees **their** data only (spot-check isolation if multi-tenant staging)

### Session 3 — Operations (45 min)
- [ ] Alert triage walkthrough  
- [ ] How to re-run sync / check pipeline  
- [ ] How to open billing portal (owner)  
- [ ] Support channel + severity definitions (`INCIDENT_RESPONSE.md`)  
- [ ] Success criteria agreed (below)

### Success criteria (example — customize per partner)
| Metric | Target (first 14 days) |
| --- | --- |
| Time-to-first-dashboard | ≤ 1 business day after kickoff |
| Critical platform incidents | 0 unresolved > 4h |
| Successful syncs / week | ≥ 5 (if connector path) |
| Partner weekly active operators | ≥ 2 |

### Rollback plan
1. Disable partner org (`suspended`) if data issue.  
2. Revoke API tokens; force logout (revoke sessions).  
3. Disconnect connectors (delete connection / rotate secrets).  
4. If billing error: Stripe test refund / cancel subscription; confirm webhook state.  
5. Restore from snapshot only if corruption (Part 7) — coordinate change window.

---

# Part 4 — Operational checklists

## Daily checks (15 min)

```bash
curl -fsS "$API/health/ready"
curl -fsS -H "Authorization: Bearer $METRICS_TOKEN" "$API/metrics" | head
python scripts/soak_snapshot.py --base-url "$API"
docker compose logs worker --since 24h 2>/dev/null | grep -i error | tail
```

- [ ] Ready = database+redis ok  
- [ ] No sustained 5xx spike  
- [ ] Worker heartbeating / no crash loop  
- [ ] Stripe webhook failures ≈ 0 (Dashboard)  
- [ ] Disk / DB storage not approaching limit  

## Weekly checks (45 min)

- [ ] Review soak JSONL trends (latency, enqueue errors)  
- [ ] Postgres backup present (managed console)  
- [ ] Certificate expiry > 14 days  
- [ ] Open High incidents closed or mitigated  
- [ ] One restore drill dry-run scheduled this month  
- [ ] Dependency advisories skimmed (`pip-audit` / npm audit)  

## Incident response
Follow `docs/INCIDENT_RESPONSE.md` (severity, first 15 minutes, playbooks).

## Failed deployments

1. Check CI green on commit.  
2. `docker compose logs backend --tail 200` for `ConfigurationError` / migrate errors.  
3. Rollback: redeploy previous image tag.  
4. If migrate failed mid-way: restore DB snapshot before re-attempt (never `create_all` on staging).  

**Verify:** `/health/ready` 200; smoke login.

## Worker failures

```bash
docker compose restart worker
docker compose logs worker --tail 100
# Re-enqueue stuck connections via UI/API sync
```

## Redis failures

1. Confirm `redis-cli ping`.  
2. Restart Redis; API readiness fails until up (by design).  
3. **Do not** set `CONNECTOR_SYNC_INLINE=true` on staging.  
4. Re-enqueue failed syncs after recovery.

## Database failures

1. Check managed DB status / connections.  
2. Failover if offered by provider.  
3. If restore required → Part 7.  
4. Verify RLS still active after restore (`alembic` / policy check).

## Stripe webhook failures

1. Dashboard → Webhooks → recent deliveries.  
2. Confirm `STRIPE_WEBHOOK_SECRET` matches endpoint.  
3. Replay event (idempotent via `stripe_events`).  
4. Watch `stripe_webhook_total` metric.

## Connector failures

1. Connection `last_error` + health.  
2. Test connection.  
3. Worker logs for exception.  
4. Credential refresh / reconnect.  
5. Confirm URL allowlist not blocking required host.

## OAuth failures (WorkOS)

1. Redirect URI exact match.  
2. Clock skew.  
3. Correct Client ID / API key environment.  
4. Browser third-party cookie issues (use supported AuthKit flow).

## Certificate renewal

- Prefer ACME auto-renew.  
- 30/14/7 day expiry alerts.  
- After renew: curl HTTPS + login smoke.

## Secret rotation

| Secret | Effect | Steps |
| --- | --- | --- |
| `SESSION_SECRET` | All sessions invalid | Rotate → users re-login |
| `CREDENTIALS_ENCRYPTION_KEY` | Old blobs unread | Re-encrypt connections or force reconnect **before** discarding old key |
| WorkOS keys | Auth outage if mismatched | Dual-run carefully; update redirect |
| Stripe keys/webhook | Billing break | Update env + webhook secret together |
| `METRICS_TOKEN` | Scrape 404 | Update Prometheus + API atomically |

## Backup verification / restore
See Part 7 and `scripts/restore_drill.sh`.

---

# Part 5 — 14-day soak test plan

**Start only after staging deploy + WorkOS login smoke pass.**

### Global pass criteria (end of day 14)
- Zero open **Critical** incidents  
- Zero open **High** incidents without mitigation  
- Ready check success ≥ 99.5% of samples  
- API P95 (authenticated list) advisory < 500 ms under normal load  
- No unbounded Redis memory / queue growth  
- Worker restart count explained (deploys only)

### Daily routine

| Time (UTC) | Action |
| --- | --- |
| 00:05 | `soak_snapshot.py` (cron also every 5–15 min) |
| 09:00 | Human review of last 24h samples + logs |
| 17:00 | Stripe + connector spot check |

### Per-day focus

| Day | Focus | Monitor | Alert threshold | Pass/fail |
| --- | --- | --- | --- | --- |
| 1 | Baseline | ready, RSS, queue≈0 | ready fail >2m | Fail if boot loop |
| 2 | Auth | login success, 401 rate | auth errors spike | Fail if login broken >15m |
| 3 | Billing | webhook ok/dup | webhook error >0 /15m | Fail if unacked webhooks |
| 4 | CSV import | import jobs, audit | import fail rate >20% | Fail if commits 500 |
| 5 | Connector sync | enqueue/sync metrics | enqueue error >0 /15m | Fail if worker dead |
| 6 | Memory | container RSS trend | +50% vs day1 no deploy | Investigate leak |
| 7 | Mid checkpoint | full dashboard review | any High open | Mitigate or fail soak |
| 8 | Queue stress | 10 syncs back-to-back | queue depth growing 1h | Scale worker / fix |
| 9 | DB | conn count, slow queries | conn >80% max | Tune pool |
| 10 | Redis | used_memory | >80% maxmemory | Flush jobs only if safe |
| 11 | Latency | p95 list endpoints | p95 >1s sustained | Profile |
| 12 | Failure inject | restart redis/worker | recovery <5m | Fail if >15m |
| 13 | Security spot | metrics 404 w/o token; isolation | any leak | **Critical** |
| 14 | Sign-off | compile soak report | all High closed | Pass/Fail certificate |

### Tracked signals
API latency · queue length · memory · CPU · DB · Redis · workers · connector syncs · billing webhooks · authentication · error rate (5xx)

Record incidents in `docs/reports/RC2_SOAK_LOG.md` (or new `RC3_SOAK_LOG.md`).

---

# Part 6 — Load test plan (k6)

Scripts live in `load/k6/`. Install: `brew install k6` / https://k6.io.

### Thresholds (design-partner staging)

| Scenario | P95 | Error rate |
| --- | --- | --- |
| Health ready | < 100 ms | < 1% |
| Auth me (cookie) | < 300 ms | < 1% |
| Shipments list | < 500 ms | < 1% |
| Mission Control | < 800 ms | < 2% |

### Environment

```bash
export API_BASE=https://staging-api.example.com
export SUPPLY_SESSION=...          # from browser cookie after login
export ORG_ID=...                  # UUID
export K6_VUS=10
export K6_DURATION=2m
```

### Run

```bash
k6 run load/k6/health.js
k6 run load/k6/authenticated_api.js
# CSV / sync are destructive or queue-heavy — run gated scripts intentionally
k6 run load/k6/csv_import.js        # requires fixture + session
```

Pass = all thresholds green; no worker crash; ready stays ok during test.

---

# Part 7 — Disaster recovery procedures

Targets: RPO ≤24h (daily backup); RTO ≤4h. Detail also in `docs/DISASTER_RECOVERY.md`.

## 7.1 Database backup
1. Rely on managed automated backups.  
2. Before migrations: manual snapshot; record ID + time.  

**Verify:** snapshot listed in console.

## 7.2 Database restore
```bash
./scripts/restore_drill.sh /path/to/dump.sql "$RESTORE_DATABASE_URL"
# Point a temporary API at RESTORE URL
curl -fsS "$TMP_API/health/ready"
# Smoke: login + list shipments for one org
# Record Pass in docs/reports/RC3_RESTORE_DRILL.md
```

## 7.3 Redis recovery
1. Restart Redis.  
2. Confirm API ready.  
3. Re-enqueue failed connection syncs.  
4. Sessions unaffected (Postgres-backed).

## 7.4 Worker recovery
```bash
docker compose restart worker
# or Render: manual restart
```

## 7.5 Application rollback
1. Redeploy previous image digest/tag (API + worker + web).  
2. Do **not** downgrade DB unless migration is reversible and tested.  
3. Smoke Part 1.10.

## 7.6 Infrastructure rollback
1. Revert DNS / LB target group to prior ASG/service.  
2. Confirm certs still valid.  
3. Re-run ready + login.

## 7.7 Secret rotation
See Part 4 table. For encryption key: decrypt with old / encrypt with new in a maintained scripted maintenance window (or force partner reconnect).

## 7.8 Loss of connector credentials
1. Mark connection error.  
2. Partner re-enters secrets via configure UI/API.  
3. Test → sync.  
4. Audit log should show update.

## 7.9 Loss of Stripe webhook delivery
1. Fix endpoint / secret.  
2. Replay missed events from Stripe Dashboard (idempotent).  
3. Reconcile `billing_accounts` vs Stripe customer subscriptions manually if gap >24h.

---

# Part 8 — Monitoring & dashboards

## Dashboards (Grafana or equivalent)

| Dashboard | Panels |
| --- | --- |
| API | RPS, P95 latency, 5xx ratio, ready status |
| Database | Connections, CPU, storage, lag (managed metrics) |
| Redis | Memory, connected clients, evictions (should be 0 with noeviction) |
| Workers | Restart count, log error rate, `connector_sync_*` |
| Authentication | `/auth/*` status codes, rate-limit 429s |
| Billing | `stripe_webhook_total` by result |
| Connectors | enqueue result, sync duration, sync status |
| Infrastructure | Node CPU/mem/disk |

## Metrics (app)
- `http_requests_total`, `http_request_duration_seconds`  
- `connector_sync_total`, `connector_sync_duration_seconds`, `connector_enqueue_total`  
- `stripe_webhook_total`  
- Header `X-Request-ID` for correlation  

## Alert thresholds & pager

| Alert | Severity | Condition | Page? |
| --- | --- | --- | --- |
| SupplyNotReady | Critical | ready failing 2m | Yes |
| SupplyHigh5xx | High | 5xx ratio >5% 10m | Yes |
| SupplySyncEnqueueErrors | High | enqueue errors 15m | Yes |
| SupplyStripeWebhookErrors | High | webhook errors 15m | Yes |
| CertExpiring | Medium | <14 days | No (ticket) |

**Escalation:** on-call SRE (15m) → eng lead (1h) → customer comms for High+ affecting partners (`INCIDENT_RESPONSE.md`).

---

# Part 9 — Go / No-Go checklist (paid pilots)

Every item must be **objectively verified** (command, screenshot, or ticket ID).  
Design partners may start with a **subset** (Infrastructure → Auth smoke → Monitoring scrape).  
**Paid commercial pilots require ALL items Pass.**

### Infrastructure
- [ ] DNS resolves for app + API  
- [ ] HTTPS valid on both  
- [ ] Postgres healthy; `alembic current` = head  
- [ ] Redis PING ok  
- [ ] API `/health/ready` shows database+redis ok  
- [ ] Worker process stable 24h  
- [ ] Frontend loads over HTTPS  

### Security
- [ ] `ENVIRONMENT=staging` or `production` fail-closed boot proven  
- [ ] `SESSION_COOKIE_SECURE=true`; logout clears session  
- [ ] `/metrics` 404 without bearer; 200 with token  
- [ ] `/docs` disabled  
- [ ] `NEXT_PUBLIC_DEV_LOGIN=false`  
- [ ] Tenant isolation spot-check (org A cannot see org B)  
- [ ] SSRF: evil `base_url` rejected  

### Backups & DR
- [ ] Automated DB backup enabled  
- [ ] Restore drill **Pass** recorded (`RC3_RESTORE_DRILL.md`)  
- [ ] Rollback procedure executed once successfully  

### Monitoring
- [ ] Metrics scraped continuously  
- [ ] Alerts routed to on-call  
- [ ] Log drain searchable by `request_id`  

### Billing
- [ ] Stripe **test** checkout succeeds  
- [ ] Webhook signature verified; duplicate safe  
- [ ] Portal opens; upgrade/downgrade/cancel verified  
- [ ] `FEATURE_BILLING_ENFORCE=true`  

### Authentication
- [ ] WorkOS login + email verify path works  
- [ ] Invite accept + RBAC verified  
- [ ] API token create / use / revoke  

### Connectors
- [ ] ≥1 sandbox connector test + queued sync + data visible  
- [ ] Worker required (no inline sync)  

### Performance
- [ ] k6 thresholds green (`load/k6`)  
- [ ] Benchmark report attached (`scripts/benchmark_api.py --write-report`)  

### Soak
- [ ] ≥7 days (prefer 14) samples in `soak_samples.jsonl`  
- [ ] No open Critical/High without mitigation  

### Documentation & ops
- [ ] This manual followed end-to-end by a second engineer  
- [ ] Design partner onboarding checklist completed for pilot #1  

### Decision

| Result | Outcome |
| --- | --- |
| Design-partner subset Pass; paid list incomplete | **Design partners only** |
| All items Pass | Eligible for **paid commercial pilots** certification |
| Any Critical fail | **No-Go** |

---

## Appendix A — Quick command sheet

```bash
API=https://staging-api.example.com
export METRICS_TOKEN=...

curl -fsS $API/health/live
curl -fsS $API/health/ready
curl -fsS -H "Authorization: Bearer $METRICS_TOKEN" $API/metrics | head
python scripts/soak_snapshot.py --base-url $API
python scripts/benchmark_api.py --base-url $API --auth --write-report
k6 run load/k6/health.js
./scripts/restore_drill.sh backup.dump "$RESTORE_URL"
```

## Appendix B — What is out of scope

- FedEx connector (not shipped)  
- Object storage / S3 (not implemented; CSV handled in-request)  
- In-repo Grafana/Alertmanager (operator-owned)  
- Guaranteeing paid-pilot certification without completing Part 9  

---

*End of Operations Manual.*
