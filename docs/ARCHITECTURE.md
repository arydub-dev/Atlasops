# Architecture guide

The implementation uses Next.js / React for the browser, FastAPI / SQLAlchemy for the API, PostgreSQL for durable domain data, and Redis / ARQ for queued connector work. The root ARCHITECTURE.md describes the domain layers.

Identity uses WorkOS and opaque server-side session cookies. Permission checks run in the API; tenant UUIDs scope queries and PostgreSQL RLS. API tokens are org-bound and cannot inherit platform-admin access. Scheduled tasks must commit tenant writes before changing tenant context. API/worker database roles must be NOSUPERUSER NOBYPASSRLS; migrations use a separate role. Database startup rejects privileged runtime roles.

Data enters through bounded CSV/XLSX imports or connector jobs. Domain services compute metrics, risks and simulation estimates. Copilot reads a permission-filtered context snapshot. Optional providers include OpenAI, Resend, Sentry, PostHog and S3-compatible storage; unset integrations are not proof of delivery.

Sales inquiries are encrypted records outside the tenant domain. Only session-authenticated platform operators can list/delete them; normal org admins cannot. Intake is disabled by default pending privacy and operator configuration.

No new infrastructure provider is chosen without a deployment target. The current source snapshot has no Git history; initialize/publish a repository before enabling CI deployment.
