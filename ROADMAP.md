# ATLASOPS / Supply — Roadmap

Post–Supply v2 foundation. Items below build on multi-tenancy, WorkOS, Stripe, and the connector SDK.

## Near term

| Item | Why it matters |
| --- | --- |
| Raise test coverage toward 90%/80% | Harden CI gates for enterprise procurement |
| Frontend E2E (Playwright) for onboarding + tenant isolation | Catch auth/org regressions |
| Import rollback + mapping wizard polish | Safer production data loads |
| Connector credential UI (OAuth redirect flows) | Complete Dynamics/Salesforce connect UX |
| Audit log explorer UI | Compliance review without SQL |

## Mid term

| Item | Why it matters |
| --- | --- |
| Additional ERP connectors (NetSuite, SAP) | Expand addressable market |
| Workflow execution / approvals | Close loop from insight → action |
| Real-time WebSocket updates | Lower alert latency |
| httpOnly cookie SameSite hardening for split domains | Multi-domain deployments |

## Long term

| Item | Why it matters |
| --- | --- |
| Multi-region + Kubernetes | Higher availability / DR |
| Agentic multi-step investigations | Richer AI operations |
| Advanced forecasting models | Planning sophistication |
| Formal operational ontology | Graph-scale analysis |

## Out of scope

ATLASOPS/Supply is an operational intelligence layer, not a system of record. It does not replace ERP/WMS/TMS or autonomously execute supply-chain mutations without human approval.
