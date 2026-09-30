# ATLASOPS Application Security Audit

**Role:** Principal Application Security Engineer  
**Frameworks:** OWASP Top 10 (2021), CWE/SANS Top 25, secure coding principles  
**Date:** 2026-07-31  

Critical and High findings below were remediated in the same change set unless marked **Open**.

---

## Remediated (High)

| ID | Issue | Primary fix location |
| --- | --- | --- |
| A1 | Invite privilege escalation to `owner`/`admin` | `rbac/permissions.py` `can_invite_role`, `identity/orgs.py` |
| A2 | Silent invite auto-accept on login | `identity/discovery.py` (explicit token only) |
| A3 | Domain / IdP claim via settings mass-assignment | `api/routers/orgs.py` `update_current_org` |
| A4 | API token retains `is_platform_admin` | `api/deps.py` |
| A5 | SSRF via org webhooks + Slack/Teams URLs | `core/outbound_url.py`, `alert_channels.py`, webhook create |
| A6 | Secrets in plaintext `Connection.config` | `api/routers/data.py` |
| A7 | AI context ignores RBAC | `services/ai_advisor.py` |
| A8 | Unbounded import DoS | `api/routers/data.py` 15MB cap |

## Remediated (Medium)

| ID | Issue | Fix |
| --- | --- | --- |
| A9 | Salesforce SOQL identifier injection | `_soql_ident` allowlist |
| A10 | HTML injection in emails | `core/html_safe.py` + alert channels |
| A11 | `/health/ready` exception leakage | Opaque `not_ready:*` codes |
| A12 | Virus scan marked `clean` without scanner | Status `pending` until real scan |
| A13 | Document path-like filenames | Basename sanitize |
| A14 | Rate-limit Redis sticky fail-open | Cooldown retry |

## Open (ops / follow-up)

| ID | Risk | Notes |
| --- | --- | --- |
| B1 | ~~High~~ **Fixed (2026-08-12)** | ARQ jobs HMAC-signed; Redis AUTH required in production boot |
| B2 | ~~Medium~~ **Fixed (2026-08-12)** | Stripe customer index preferred over metadata; mismatch uses index |
| B3 | Medium | Incomplete audit hash chain |
| B4 | Medium | Emergency lockout does not revoke IdP sessions / suspend org |
| B5 | High (deps) | Frontend npm audit highs (postcss via Next, sharp) — patch cadence required |

See [SECURITY_AUDIT.md](./SECURITY_AUDIT.md) for the full 2026-08-12 posture report.

## Regression tests

`backend/tests/test_security_hardening.py`, `test_security_attack_matrix.py`, plus SSRF, CSRF, auth guards, Stripe, and Postgres RLS suites. CI job: `.github/workflows/ci.yml` → `security`.
