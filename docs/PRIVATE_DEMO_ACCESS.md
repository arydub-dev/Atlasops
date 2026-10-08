# Private demo access

`/demo-login` is an unlinked, noindex page requiring a login ID and password. Its URL is not a security boundary: the backend verifies the password and workspace restrictions. No credentials are embedded in frontend assets. The normal login page no longer exposes the development login form.

The optional server settings are `DEMO_LOGIN_ID`, `DEMO_LOGIN_PASSWORD_HASH` (bcrypt), `DEMO_LOGIN_USER_ID`, and `DEMO_LOGIN_ORG_ID`. Empty settings disable the endpoint. The configured identity must be active, not a platform administrator or WorkOS identity, and must have exactly one active viewer or demo_operator membership without custom permissions. It must not own the organization. The organization must have `settings.private_demo=true`, be active, and contain fictional data only.

Demo sessions use the existing HTTP-only cookies, rate limiting, session expiration and server-side authorization. Changing the password hash, disabling the account/configuration, adding memberships or elevating the role invalidates its demo sessions. Normal production WorkOS sign-in is unchanged. Enabling private credentials disables the development passwordless endpoint even in local development.

Viewer credentials permit read-only exploration. The demo_operator role additionally permits imports, incident actions and AI chat in an explicitly marked fictional workspace. Neither role grants administration. Use separately invited named operator accounts for supervised interactive workflows. Shared credentials do not identify individual visitors.

Local credentials and configuration are stored under ignored `.local/`, with owner-only file permissions. `start.sh` reuses that configuration without reseeding the workspace. Do not commit, publish, or paste the configuration into frontend environment variables. Rotate the bcrypt hash and update the private credential handout together when access should end.

Remote access requires deployment of this code, a dedicated synthetic hosted organization and visitor identity, server-side secret configuration, working production dependencies, HTTPS and a verified hosted login. A localhost link works only on the machine running AtlasOps. This change has been verified locally, not deployed.

Verification: 338 backend tests passed; 19 database/service-specific tests skipped in the local SQLite run. Five dedicated tests cover valid/invalid/disabled access, viewer write denial, disabled development login, credential rotation, membership and role changes. Frontend typecheck and lint pass. Running local API verified login 200, 240 inventory positions, mutation 403 and old passwordless login 404.
