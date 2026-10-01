# E2E workflow coverage map

| Workflow | CI coverage | Notes |
| --- | --- | --- |
| 1 Account → org → checkout → dashboard | Partial | API org create + billing authz tests; Stripe Checkout needs staging |
| 2 Invite → accept → permissions | **Ready** | `test_workflows_e2e.py::test_workflow_invite_accept_permissions` |
| 3 Salesforce OAuth → sync | Blocked | Requires sandbox + Playwright with secrets |
| 4 CSV import → audit | **Ready** | `test_workflow_csv_import_audit` + UI smoke |
| 5 API token rotate | **Ready** | `test_workflow_api_token_rotate_and_org_binding` |
| 6 Tenant isolation | **Ready** | `test_workflow_tenant_isolation` + isolation suite |
| 7 Billing upgrade webhook | Partial | Idempotent webhook unit tests; live Stripe test mode on staging |
| 8 Logout session revoke | **Ready** | `test_workflow_logout_revokes_session` + Playwright auth redirect |

| Playwright CI | `frontend/e2e/smoke.spec.ts` — marketing, WorkOS CTA, auth redirect |
| Staging Playwright | `frontend/e2e/staging/` + workflow `staging-e2e.yml` (secrets required) |
| Map | Workflows 2/4/5/6/8 API-ready; 1/3/7 need staging secrets |
