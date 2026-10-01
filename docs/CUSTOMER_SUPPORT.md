# Customer support

Launch owner must configure a monitored support address, named primary/backup responders, operating hours and escalation contact. These facts are not supplied and must not be invented. No support SLA is currently committed.

Intake: collect organization ID, request ID, page, timestamp, observed behavior and reproduction steps. Never request passwords, API keys, database credentials or raw customer exports over email. Use a secure agreed channel for necessary redacted examples.

Triage: security/isolation or data loss is P0; auth, import, payment or worker outage is P1. Acknowledge through the configured support channel, assign an owner, preserve evidence and follow INCIDENT_RESPONSE.md / SECURITY_RUNBOOK.md. Do not promise an untested recovery time.

Common issues:
- Login loop: verify HTTPS callback, same-site origins and secure cookies.
- Import rejection: use CUSTOMER_ONBOARDING.md; UTF-8, unique headers, values only.
- Sync queued indefinitely: check Redis, worker health and failed jobs before retrying.
- Payment blocked: use the billing portal; never manually grant payment status from a browser claim.
- Copilot unavailable: distinguish provider failure from missing operational context.

Sales inquiries: enable only after final data-handling notice. Platform operators list/delete through `/api/v1/admin/leads`; org admins have no access. Proposed retention is 90 days for unqualified inquiries, subject to operator approval and automated purge implementation. Until approved, intake remains disabled.
