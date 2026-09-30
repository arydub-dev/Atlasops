# Go-live checklist

Release decision: NOT READY until every launch-critical item has linked evidence. A checkbox is not evidence by itself. Record release ID, environment, date and operator.

## Product
- [ ] Hosted core workflow and onboarding pass with real identity provider
- [ ] CSV/XLSX source totals reconciled; duplicate/reference failures reviewed
- [ ] Demo synthetic and isolated; no blocking browser/accessibility issues

## Security
- [x] Local restricted-role PostgreSQL isolation suite passes; see reports/2026-09-29-release-checks.md (rerun for actual release commit)
- [ ] Hosted session, logout, permission and tenant attack tests pass
- [ ] No secrets in artifacts; dependency/secret scans pass
- [ ] HTTPS, CORS, cookies and deployed headers verified

## Infrastructure
- [ ] API/frontend/worker/PostgreSQL/Redis deployed with separated roles
- [ ] Domain and HTTPS verified; private services not publicly exposed
- [ ] Backup schedule and retention configured; off-host restore tested
- [ ] Monitoring receives API/worker errors; alerts reach staffed responder
- [ ] Load and at least 7-day soak recorded with no open P0/P1

## Billing/integrations/AI
- [ ] WorkOS signup through dashboard verified
- [ ] Stripe checkout, duplicate webhook, upgrade/cancel and failed-payment recovery verified
- [ ] One supported connector sandbox: OAuth → queue → records → dashboard
- [ ] AI provider failure, data isolation, spend caps and concurrency verified

## Commercial
- [ ] Legal entity, privacy/terms, support contact and data retention finalized
- [ ] Pricing approved and price IDs configured
- [ ] Intake enabled only after privacy/support prerequisites; operator retrieval tested
- [ ] Pilot sponsor, success criteria and signed scope recorded
- [ ] Staffed sales/support process and rollout owner named
