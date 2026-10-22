# No-cost restricted reviewer profile

Enable REVIEWER_DEMO_ONLY=true only in an isolated staging deployment; set NEXT_PUBLIC_REVIEWER_DEMO_ONLY=true for its build. Existing credential checks, secure boot, Redis authentication throttling, PostgreSQL runtime role/RLS, tenancy and RBAC remain mandatory. The main /login surface uses the existing restricted reviewer login form, with no new authentication scheme.

API access is restricted to the configured non-admin demo user with one active membership in the private synthetic organization. Only synchronous operational read/import/recovery/incident and session routes are exposed. Connector mutations, external integrations, WorkOS onboarding, billing, administration, job scheduling and external AI are unavailable. Existing normal staging/production readiness still requires a worker heartbeat. The restricted profile reports its explicit mode and disabled worker capability; this does not pass enterprise/SSO/external-AI release gates.

All existing release assertions remain intact. Verify main login in a fresh browser, membership restrictions, the entire synthetic workflow, persistence, session revocation and mobile layout before sharing credentials. A successful API call is insufficient. Do not remove project-wide deployment protection; prefer a deployment-specific reviewer sharing mechanism after explicit approval where required.
