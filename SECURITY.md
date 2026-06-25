# Security Policy

ATLASOPS is built on concrete, reviewable security controls. This document describes the
controls implemented in the platform and how to report a vulnerability.

## Supported versions

This project is pre-1.0. Security fixes are applied to the `main` branch. Pin to a commit
or tag for reproducible deployments.

| Version | Supported |
| --- | --- |
| `main` (latest) | Yes |
| Older commits | Best effort |

## Implemented controls

### Authentication & access
- **JWT authentication** via an OAuth2 password flow; tokens are verified on every
  authenticated request.
- **Role-based access control** enforced per endpoint through a dependency factory
  (`require_roles`), following the principle of least privilege.
- **bcrypt password hashing** (via passlib); credentials are never stored in plaintext.

### Data & input
- **Input validation** with Pydantic v2 on all requests and ingestion rows.
- **Audit logging** of sensitive actions to the `audit_logs` table.
- **Connector secrets are masked** — only the last four characters of an API key are
  retained for display.

### Transport & deployment
- **TLS-ready.** The platform is designed to run behind a reverse proxy terminating TLS;
  all client/API traffic should be encrypted in transit.
- **CORS allow-listing.** Allowed origins are configured explicitly via `CORS_ORIGINS`;
  wildcard origins should not be used in production.
- **Environment-driven configuration.** Secrets are provided via environment variables;
  no secrets are committed to the repository (`.env` is git-ignored, `.env.example`
  contains placeholders only).
- **Containerized deployment** with Docker for reproducible, isolated runtime environments.

## Deployment hardening checklist

Before any non-local deployment:

- [ ] Set a strong, unique `JWT_SECRET_KEY` (32+ characters).
- [ ] Set strong database credentials; never use the local development defaults.
- [ ] Remove or replace the seeded demo accounts.
- [ ] Serve all traffic over HTTPS (TLS at the proxy or platform layer).
- [ ] Restrict `CORS_ORIGINS` to your real frontend domain(s).
- [ ] Store connector credentials in a secrets manager rather than the database.
- [ ] Review role assignments for least privilege.

## Known limitations

These are documented honestly and tracked on the roadmap:

- JWTs are stored in `localStorage` on the client, which is exposed to XSS; httpOnly
  cookies are a planned hardening step.
- Connector credentials are masked but not encrypted at rest.
- There is no built-in rate limiting; add it at the proxy/gateway layer.
- The platform is currently single-tenant; multi-tenant isolation is on the roadmap.

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities.

Instead, report them privately using GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository (Security → Report a vulnerability).

When reporting, please include:

- A description of the vulnerability and its impact
- Steps to reproduce
- Affected component(s) and version/commit

We aim to acknowledge reports within a reasonable timeframe and will coordinate
disclosure once a fix is available.
