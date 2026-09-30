# Environment matrix (dev → staging → production)

| Variable / behaviour | Development | Staging | Production |
| --- | --- | --- | --- |
| `ENVIRONMENT` | `development` | `staging` | `production` |
| Fail-closed boot | No | **Yes** | **Yes** |
| Unknown env name | — | Treated as hardened | Treated as hardened |
| `SESSION_COOKIE_SECURE` | false OK | **true** | **true** |
| `SESSION_TTL_HOURS` | 12 default | 12 (or policy) | 12 (or policy) |
| `SESSION_REMEMBER_TTL_HOURS` | 720 default | set per policy | set per policy |
| `SESSION_IDLE_MINUTES` | 60 default | set per policy | set per policy |
| `SESSION_SLIDING_ENABLED` | true | true | true |
| `CREDENTIALS_ENCRYPTION_KEY` | derived from session if empty | **required** | **required** |
| WorkOS keys | optional (dev-login) | **required** | **required** |
| `REDIS_URL` | optional for boot | **required** | **required** |
| Redis PING in `/health/ready` | only if `CONNECTOR_SYNC_INLINE=false` | **yes** (inline forbidden) | **yes** |
| `CONNECTOR_SYNC_INLINE` | may be true (tests) | **false** | **false** |
| `FEATURE_BILLING_ENFORCE` | false OK | recommended true | **must be true** |
| `METRICS_TOKEN` | optional | **required** | **required** |
| `/metrics` | public | bearer required | bearer required |
| OpenAPI `/docs` | on | off (default) | off |
| `SEED_ON_STARTUP` / demo | discouraged | **false** | **false** |
| Alembic on deploy | compose runs it | compose staging runs it | **Separate migration job** |
| `TRUST_PROXY` | false | true (overlay) | true (private reverse proxy) |
| `NEXT_PUBLIC_DEV_LOGIN` | true OK | **false** | **false** |

Sources: `startup_checks.py`, `docker-compose*.yml`, `render.yaml`, `config.py`.

## Launch-specific configuration

- `DATABASE_URL`: restricted runtime PostgreSQL role (NOSUPERUSER, NOBYPASSRLS); standard provider postgres/postgresql URLs normalize to psycopg.
- `MIGRATION_DATABASE_URL`: migration owner, supplied only to migrations/provisioning.
- `RUNTIME_DATABASE_ROLE`, `RUNTIME_DATABASE_PASSWORD`: role provisioning inputs; generated password at least 32 characters.
- `PUBLIC_HOST`, `NEXT_PUBLIC_SITE_URL`: DNS hostname and canonical HTTPS site origin.
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*`: test mode for staging, live mode only after verified checkout/recovery.
- `LEAD_CAPTURE_ENABLED`: defaults false; enable after final privacy/contact information and staffed intake.
- `AI_TIMEOUT_SECONDS` (20), `AI_MAX_OUTPUT_TOKENS` (1200), `AI_MAX_CONTEXT_CHARS` (40000): bounded provider requests. Provider account spend limits also need configuration.
- `RESEND_API_KEY`, `EMAIL_FROM`: verified invitation email sender.

The legacy Render blueprint is not the production deployment path. Use PRODUCTION_DEPLOYMENT.md. Never copy real environment files into Docker images or source control.
