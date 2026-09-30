# ATLASOPS Master Platform — Vision Alignment & Build Roadmap

**Philosophy:** Build what differentiates us. Integrate everything else.  
**Role:** Operational Intelligence Layer over ERP / CRM / WMS / TMS — never replace them.  
**Inspiration:** Palantir Gotham for supply chains.

> This document is the living map from the Master Build Prompt to the current Supply v2 codebase.  
> Prefer extending modules over greenfield rewrites. Keep **ARQ** (not Celery) and **Next 15** unless a migration is funded.

---

## Stack decisions (locked)

| Prompt | ATLASOPS today | Decision |
| --- | --- | --- |
| Next.js 16 | Next **15.5** + React **19** | Stay on Next 15 until a dedicated upgrade sprint |
| Celery | **ARQ + Redis** | Keep ARQ — same role, already wired in Render/compose |
| Auth | WorkOS | Integrate only — email-first SSO done |
| Billing | Stripe | Integrate only |
| Workers | Redis/ARQ | Schedule + DLQ added in platform foundation |

---

## What we BUILD (IP)

| Capability | Status | Next investment |
| --- | --- | --- |
| Mission Control | EXISTS | Richer widgets / map (Mapbox) |
| Risk engine | EXISTS | Configurable weights, country/weather modules |
| Simulation | EXISTS | More scenarios + cost models |
| Analytics KPIs | EXISTS | OTIF / carbon / forecast accuracy depth |
| AI Copilot | PARTIAL | Multi-step orchestration + citations |
| Connector SDK | PARTIAL | Schedule, retry, DLQ, conflict, mapping |
| Canonical graph | PARTIAL | **PO / SO / Events** foundation; later assets/vehicles/routes |
| Alert engine | PARTIAL | Channel delivery (email/webhook → Slack/Teams) |
| RBAC | PARTIAL | Activate teams/depts/custom roles in API+UI |
| Settings | PARTIAL | Members, billing, connectors, audit in UI |

---

## What we INTEGRATE (never rebuild)

| Vendor | Status | Module |
| --- | --- | --- |
| WorkOS | EXISTS | `identity/workos.py` |
| Stripe | EXISTS | `billing/` |
| Resend | WIRED (optional) | `integrations/email.py` |
| Sentry | WIRED (optional) | `integrations/sentry_setup.py` |
| PostHog | WIRED (optional) | `integrations/analytics.py` |
| S3 / R2 | WIRED (optional) | `integrations/storage.py` |
| Flagsmith | WIRED (optional) | `integrations/flags.py` |
| Better Stack / Grafana | Operator Prometheus scrape | docs/MONITORING.md |
| Intercom / Termly / Meilisearch / Mapbox | Planned | Frontend snippets when keys present |

---

## Phased roadmap

### Phase A — Platform foundation (this sprint)
1. Vendor integration layer (env-gated, no-op without keys)
2. Canonical **PurchaseOrder**, **SalesOrder**, **OperationalEvent**
3. Alert channel dispatcher (in-app + Resend email + outbound webhook)
4. Connector **retry**, **DLQ**, **scheduled sync** cron

### Phase B — Operational Intelligence (delivered)
1. Operational Knowledge Graph (`/graph/*`) + unified Timeline (`/timeline`)
2. Connector Platform V2 protocol (validate, fieldMappings, incrementalSync, health, retry, …)
3. Mission Control 2.0 widgets (PO/SO, timeline, connectors, graph, incidents, risk heatmap)
4. Mapbox network map (optional `NEXT_PUBLIC_MAPBOX_TOKEN`; SVG fallback retained)
5. AI orchestration pipeline (`POST /ai/orchestrate`) — intent → graph/timeline/risk → grounded response
6. Incident management (`/incidents`) with linked entities + timeline
7. Enterprise search (`GET /search`), executive report kinds (`/reports/*`), platform observability (`/observability/platform`)

Remaining polish (non-blocking):
- Deeper Teams/Department hierarchy activation UI
- Meilisearch / Intercom / status page links (commercial packaging)

### Phase C — Enterprise operations (delivered)
1. Connector Studio (catalogue, mapping, preview, diagnostics, health scoring)
2. Data Quality Engine + Mission Control Data Health
3. Workflow Automation (triggers/conditions/actions + ARQ cron/jobs)
4. Enterprise Admin + Security Center (members, tokens, webhooks, audit, lockout)
5. Role-specific executive dashboards with saved layouts
6. Predictive intelligence (delays, suppliers, shortages, congestion, anomalies)
7. Documents/attachments (R2-compatible storage)
8. Customer Success onboarding/adoption/health report
9. Platform Ops dashboards (workers, connector latency, AI, automations)

### Phase D — Commercial GA gates
See `docs/reports/RC3_COMMERCIAL_PILOT_CERTIFICATION.md`: staging soak, DR, load, live WorkOS/Stripe/connector E2E.

---

## Data pipeline (target)

```text
Connector → Validate → Transform → Canonical Model → Graph
    → Risk Engine → Analytics → Mission Control → AI Copilot
```

Each stage remains a modular service. Failures land in connector DLQ or import job error summaries.

---

## Success criteria (reminder)

ATLASOPS succeeds when Fortune 500 teams can:
1. Connect enterprise systems  
2. Normalize into one operational graph  
3. See Mission Control intelligence  
4. Predict risk and simulate disruption  
5. Act with AI grounded in tenant data  

Commodity auth, billing, email, monitoring, flags, and storage stay third-party.
