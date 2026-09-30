# Supervised pilot operations runbook

Status: operational procedures prepared; hosted execution and alert delivery NOT VERIFIED.

## Before admitting any customer data

Name the pilot owner, technical responder, support address and customer sponsor. Record the release commit, plan limits, user count, data volume, connector objects, support hours and escalation path in the pilot agreement. All P0 and launch-critical P1 findings must be resolved and the eight readiness gates approved. Use synthetic data until then.

Verify signup, invitation acceptance, role restrictions, tenant switching, logout, CSV/XLSX reconciliation, dashboards, simulations, Copilot fallback, reports, API token revocation, Stripe recovery and Salesforce sandbox sync. Record source totals and rejected-row reasons. Recommendations remain human-reviewed.

## During pilot operation

- At opening and closing of the staffed support window: check API readiness, database/Redis health, ARQ heartbeat and queue age, failed/retrying imports, Salesforce last successful sync and data freshness.
- Review API 5xx/latency, failed authentication, Stripe webhook errors, AI fallback/error rate, database connections/storage and Redis command/connection usage. Sentry configuration alone is not proof that a notification arrived.
- Reconcile customer source totals after each new mapping/sync. Record import IDs, release and organization identifiers, not raw business files or credentials in support tickets.
- Confirm daily backup completion and retention; repeat recovery after material schema/infrastructure changes. Keep encryption keys recoverable outside the database backup.
- Review support requests and success criteria with the sponsor on the agreed schedule. Stop expanding scope if error rate, data freshness or support capacity breaches agreed pilot targets.

## Incident response

Suspected tenant leak/data corruption: stop onboarding and affected writes, preserve redacted evidence, restrict access and escalate to the designated owner. Do not delete evidence or rotate encryption keys blindly. Communicate through the agreed incident process; no notification has been sent by this task.

API errors: correlate X-Request-ID with Sentry and logs. Check current deploy, readiness and database limits. Redeploy the known-good compatible image if needed; do not expose SQL/provider response bodies to users.

Worker outage: inspect ARQ health key via platform console, Render worker logs and Upstash connection limits. Restart the worker, then verify an isolated synthetic probe and one idempotent test sync. Do not flush Redis or blindly duplicate jobs. Escalate repeated failures; preserve dead-letter/import records.

Stripe: verify endpoint/environment/signing-secret mapping and current provider status. Replay the specific test event through Stripe after fixing the cause. Never manually grant paid access based on the browser success URL. Do not replay live events in staging.

WorkOS: compare callback URL, client/environment and organization mapping. Investigate state/PKCE/session errors without recording codes or cookies. Never turn on development login in staging/production.

Database recovery: restore into a separate empty instance; apply migrations as the migration role, provision restricted runtime grants, connect an isolated app, verify source totals and tenant visibility, then coordinate a controlled cutover. Keep the original database intact until acceptance.

## Retention decisions to approve

CSV/XLSX parser bytes are transient; imported operational rows and import history persist. AI prompts/responses/context snapshots persist in AIReport. Uploaded documents are soft-deleted; object removal is not automated. Organization deletion disables access but does not purge all records. Connector credentials remain encrypted until their records are removed. Application/provider log retention depends on deployment configuration.

Before launch, approve retention periods for each category, configure provider log/backup lifecycles, and implement/validate required purge workflows. No universal automated deletion policy is claimed. Document attachments require working object storage; the selected architecture does not yet include one. Keep them outside the agreed pilot scope or provision/validate storage and scanning before use.

## Release/stop decision

Do not accept payment/customer data with unverified tenant/auth boundaries, missing durable storage for enabled features, missing backups, unstaffed support or undelivered alerts. On completion, export the customer's agreed data, revoke access/connector credentials according to the signed scope, and execute the approved retention policy with recorded evidence.
