# Supervised hosted pilot evidence checklist

Status: BLOCKED — no verified staging deployment or human sign-off recorded.

User-confirmed resource inventory (October 10, 2026): the public site is
https://www.atlasops.online/, but its staging status and deployed revision are not
verified. Synthetic organization, WorkOS staging access and staging external-provider
configuration are not confirmed. The user explicitly directed that hosted checks remain
BLOCKED and that no destructive tests run against this public site. No hosted test was run.
Local QA is not hosted acceptance. Do not deploy from this checklist automatically.

## Staging prerequisites and identity

Record the staging URL, hosting project/environment, deployed Git revision and build ID,
backend revision, migration revision, UTC test time, operator, and synthetic organization IDs.
Use a separate staging database, Redis, WorkOS staging application and external AI project.
Disable development auth in hosted environments. Never reuse production customer credentials.
Credentials belong in the provider's secret settings or an approved local secret store, not
this document, screenshots, committed fixtures, terminal output or QA reports.

Required access: synthetic admin and restricted-role users; controlled email inboxes for
invitation acceptance; staging WorkOS application/organization administration; staging
provider configuration with a test budget; permission to create/delete synthetic records.
No customer data. Obtain an explicit deployment decision separately if staging does not exist.

## Hosted workflow evidence

For each row record PASS/FAIL/BLOCKED/SKIPPED, reason, timestamp and evidence path.
A screenshot alone does not establish persistence or database reconciliation.

| Check | Required observation | Status |
| --- | --- | --- |
| Login/org | Real hosted login, correct organization and restricted-user denial | BLOCKED |
| CSV/XLSX | Preview, mapping, commit, rejected-row details, repeat upload | BLOCKED |
| Reconciliation | Source totals match scoped database and displayed current inventory; no duplicate current positions | BLOCKED |
| Inventory/shipments | Imported quantities, dates and linked records display accurately | BLOCKED |
| Investigation | Open an issue, inspect evidence, confirm replenishment against configured target/current quantity | BLOCKED |
| Incident | Create, assign, investigate, mitigate, resolve; invalid transitions denied | BLOCKED |
| Persistence | Refresh and new authenticated session retain quantities, ownership, notes and resolution | BLOCKED |
| Logout | Session cookie removed; replay of old session rejected by backend | BLOCKED |

## Real WorkOS staging lifecycle

- Capture sanitized login redirect and callback outcomes; never store authorization codes/tokens.
- Create invitation, accept with controlled inbox, verify intended organization and role.
- Reject cross-organization access, invalid state, reused state and replayed callback.
- Verify expiry and logout against backend authorization, not just navigation.
- Change role and verify fresh requests enforce reduced permissions.
- Revoke session and verify the old cookie/token no longer authorizes requests.
- Record actual WorkOS staging application and organization identifiers plus deployed revision.

## External AI staging validation

Use two synthetic organizations and unique canaries. Record actual provider/model and sanitized
provider request ID or server-side execution trace for each provider-executing case. Local-engine
responses, stubs and timeouts simulated before provider invocation are not live-provider evidence.

Explicit SKU and delivery-event questions intentionally use deterministic evidence handling.
Verify those responses but label them deterministic, then use broad operational prompts to
exercise the configured external provider. Verify missing/foreign records are not exposed in
retrieved context or output. Import malicious instructions in descriptions and verify that the
provider does not follow them. Check cross-org requests, bounded timeout, provider errors and
safe fallback. Record the actual fault mechanism; do not equate a fake response with a provider outage.
If no real provider execution is observed, AI-LIVE-001 remains BLOCKED.

## Human visual review (separate approval)

Reviewer: NOT ASSIGNED. Reviewed deployment/revision: NOT RECORDED. Approval: PENDING.

Review at desktop 1440x900 and mobile 390x844, plus keyboard navigation and 200% zoom:

- Authentication, invitations, expiry and logout; no public demo credentials exposed.
- Navigation, active location, back navigation, focus visibility and readable labels.
- CSV/XLSX selection, mapping, progress, validation errors and completion feedback.
- Dashboards: loading, empty, populated, stale-data and error states; no misleading metrics.
- Inventory and shipment details: long names, tables, quantities, timestamps and overflow.
- Issues/recommendations: calculation readability and links to supporting records.
- Incidents: assignment, state transitions, notes, confirmation and persistence.
- Network failure and permission-denied messages; no stack traces or secrets.

For each view capture a sanitized screenshot, viewport, route, deployed revision, findings and
resolution. Automated screenshots/overflow checks do not supply human approval. The reviewer
must explicitly approve or reject the exact reviewed revision. Material changes require review again.

## Pilot decision

All critical evidence must be present and passing. Keep unresolved checks BLOCKED or FAIL.
Record scope, supervised users, support owner, incident escalation and rollback decision owner.
This checklist does not establish unrestricted enterprise readiness or a commercial SLA.
