> Latest supervised-pilot status: [September 30 readiness report](docs/PILOT_READINESS_2026-09-30.md). Deployment target: Vercel + Render + Upstash; hosted gates remain blocked pending repository/provisioning.

> Current release status: see [the launch report](docs/LAUNCH_REPORT.md) and [local validation evidence](docs/reports/2026-09-29-release-checks.md). Hosted commercial launch remains unverified; historical readiness claims are not current approval.

# ATLASOPS

**Operational intelligence for modern supply chains.** ATLASOPS unifies operational
data, monitors risk, coordinates decisions, and turns fragmented supply chain
information into actionable intelligence — in a single platform.

<p align="center">
  <img alt="Next.js 15" src="https://img.shields.io/badge/Next.js-15-black?logo=next.js" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python_3.12-009688?logo=fastapi&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green" />
</p>

---

## Executive Summary

ATLASOPS is a cloud-based operational intelligence platform for supply chain
operations. It maintains a unified operational model — suppliers, warehouses, products,
inventory, shipments, alerts, and risk assessments — and exposes it through surfaces
designed for daily operations, analysis, and executive review.

It does not replace ERP, WMS, or TMS systems. It sits above them as a decision layer:
aggregating signals, scoring risk, recommending responses, and supporting what-if
analysis before decisions are committed. The platform ships with a fully seeded dataset
so every surface is operational immediately, and supports connecting your own data
through CSV/Excel import and a connector framework.

---

## Business Problem

Most organizations manage supply chain operations across multiple systems that were
never designed to work together:

- ERP for orders and master data
- WMS for warehouse positions
- TMS for carrier tracking
- Supplier portals, spreadsheets, and email for exceptions
- Separate reporting tools for leadership reviews

The result is predictable: operators spend time reconciling data instead of acting on
it. A delayed shipment in the TMS may not surface alongside the inventory position it
affects. A deteriorating supplier may not appear in the same view as the shipments and
SKUs that depend on them. Leadership briefings are assembled manually from exports that
are already stale. Problems are discovered after they have already caused impact.

---

## Why ATLASOPS Exists

ATLASOPS exists to close the gap between **detecting** an operational exception and
**deciding** what to do about it. It is organized around three questions that operations
and leadership teams ask during every shift:

| Question | How the platform answers it |
| --- | --- |
| **What is happening?** | Mission Control aggregates health scores, KPIs, open alerts, and trend charts. Shipments, inventory, warehouses, and suppliers each have dedicated operational views. The Network View shows geographic topology and active routes. |
| **Why is it happening?** | Risk assessments score exposure by category (supplier, shipment, inventory, geographic). The situation report names contributing suppliers, warehouses, and trends. Analytics surfaces concentration and performance patterns. |
| **What should happen next?** | Recommended actions are ranked by priority with expected impact and estimated cost. Alerts include prescribed response guidance. The Simulation Center models disruption scenarios. The Operations Copilot answers operational questions grounded in live data. |

---

## Core Capabilities

- **Mission Control** — composite health score, executive KPIs, AI situation report,
  ranked recommended actions, and a critical alert feed in one cockpit.
- **Operational visibility** — shipments, inventory, warehouses, and suppliers with
  search, filtering, timelines, and exception management.
- **Risk intelligence** — explainable 0–100 scoring across supplier, shipment, inventory,
  and geographic categories, with factors and recommendations.
- **Simulation** — what-if modeling for supplier shutdown, port closure, warehouse
  outage, demand spike, and weather disruption with quantified impact.
- **Operations Copilot** — natural-language investigation grounded in live data, with a
  deterministic local engine fallback.
- **Executive briefs** — one-click leadership summaries with Markdown and PDF export.
- **Data integration** — CSV/Excel ingestion and an extensible connector framework with
  pipeline monitoring.

---

## System Architecture

ATLASOPS is a three-tier application: a Next.js frontend, a FastAPI backend exposing a
versioned REST API, and a PostgreSQL database. An optional OpenAI integration powers the
Operations Copilot, with a deterministic local engine as a fallback.

The system is organized into three layers; data flows upward from ingestion to decision
support.

```
┌─────────────────────────────────────────────────────────────┐
│  DECISION LAYER                                              │
│  Mission Control · Situation Reports · Recommended Actions  │
│  Operations Copilot · Executive Briefs · Simulations        │
├─────────────────────────────────────────────────────────────┤
│  OPERATIONAL LAYER                                           │
│  Shipments · Inventory · Warehouses · Suppliers             │
│  Alerts · Risk Assessments · Analytics · Network View       │
├─────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                  │
│  Domain tables · Seeded dataset · CSV/Excel import          │
│  Connector framework · Pipeline jobs                        │
└─────────────────────────────────────────────────────────────┘
```

Full detail, including data flow, deployment, ER, request lifecycle, and integration
diagrams, is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Browser"]
        UI["Next.js 15 · TypeScript · Tailwind · Recharts"]
    end

    subgraph Backend["FastAPI application"]
        API["REST API /api/v1/*"]
        AUTH["WorkOS sessions + RBAC + API tokens"]
        BILL["Stripe billing"]
        CONN["Connector SDK"]
        subgraph Services["Domain services"]
            MET["Metrics / Analytics"]
            RISK["Risk Engine"]
            ALERT["Alert Engine"]
            SIM["Simulation Engine"]
            ING["CSV/Excel ingestion"]
            AI["Operations Copilot"]
        end
    end

    DB[("PostgreSQL + RLS")]
    REDIS[("Redis + ARQ worker")]
    OPENAI["OpenAI API (optional)"]
    EXT["Salesforce · Dynamics BC · UPS · CSV/Excel"]

    UI -->|HTTPS JSON + httpOnly session cookie| API
    API --> AUTH
    API --> BILL
    API --> CONN
    API --> Services
    Services --> DB
    AUTH --> DB
    CONN --> REDIS
    EXT -->|OAuth / APIs / files| CONN
    EXT -->|files| ING
    AI -.->|when key set| OPENAI
```

---

## Operational Workflows

How different parts of the platform work together during realistic scenarios.

### Supplier reliability deterioration

| Stage | What happens |
| --- | --- |
| **Trigger** | A supplier's delivery reliability drops below threshold. The risk engine creates a supplier-category assessment, and a `supplier_failure_risk` alert is generated. |
| **Investigation** | The operator opens Mission Control and sees the alert in the critical feed. The situation report names the supplier. The Suppliers page shows the scorecard and six-month trend. |
| **Analysis** | Risk Intelligence shows the scored assessment with contributing factors. Analytics reveals which shipments and SKUs depend on this supplier. Network View shows the supplier's position relative to affected warehouses. |
| **Decision** | Mission Control recommends activating a backup supplier and placing the vendor on a recovery plan. The operator runs a supplier-shutdown simulation to quantify exposure before escalating. |

### Inventory shortage risk

| Stage | What happens |
| --- | --- |
| **Trigger** | Inventory for a high-velocity SKU falls below its reorder point. The alert engine generates an `inventory_stockout_risk` alert. |
| **Investigation** | The Inventory page shows the SKU in low-stock status with a days-of-supply estimate; the warehouse card shows utilization context. |
| **Analysis** | A risk assessment scores inventory exposure; analytics shows the SKU's demand trend; Mission Control includes the shortage in the situation report. |
| **Decision** | Alert guidance suggests emergency replenishment or inter-warehouse transfer. A demand-spike simulation stress-tests whether safety stock is adequate. |

### Regional disruption affecting shipments

| Stage | What happens |
| --- | --- |
| **Trigger** | Multiple shipments from the same origin are delayed simultaneously. Delay hotspots appear on the Network View; geographic risk is elevated. |
| **Investigation** | The Shipments page filtered by origin shows the cluster; Network View highlights the hotspot with delay counts. |
| **Analysis** | Analytics shows delivery performance for the affected lane; the Copilot answers "why are delays increasing?" with supplier and lane context. |
| **Decision** | Recommended actions suggest expediting high-value shipments and pre-positioning safety stock. A port-closure simulation estimates downstream inventory impact. |

---

## Key Features

### Mission Control
A composite supply chain health score (weighted across on-time delivery, inventory
health, supplier reliability, and risk), executive KPIs, an AI situation report, ranked
recommended actions, a critical alert feed, and supporting trend charts — the primary
command surface for the start of a shift.

### Shipments
Full lifecycle management with search, filter, sort, and pagination. Each shipment has a
tracking timeline built from discrete events, per-shipment delay risk scoring, and
role-gated status updates.

### Inventory
Multi-warehouse views with health classification (healthy, low stock, overstock,
stockout), reorder recommendations from reorder points, safety stock, and average daily
demand, and historical snapshots separated from live positions.

### Warehouses
Capacity, utilization, regional assignment, and risk level per facility, with search,
region filter, and sort — a network-level view of capacity and risk concentration.

### Suppliers
Rankings and scorecards covering delivery reliability, average delay, fulfillment rate,
and defect rate, with six-month performance trends and top/bottom performer
identification.

### Risk Intelligence
An automated engine scoring exposure 0–100 across supplier, shipment, inventory, and
geographic categories. Each assessment includes a severity level, description,
contributing factors, and a recommendation, and can be recomputed on demand.

### Alert Management
Structured alerts with types, priority levels, and an Open → Acknowledged → Resolved
lifecycle, with filtering and statistics — a triage queue rather than an undifferentiated
notification stream.

### Analytics
Delivery, supplier, inventory, and forecast-style analytics with time series, bar, donut,
and heatmap visualizations to support weekly and monthly reviews.

### Network View
An interactive map of warehouses and suppliers as nodes, active routes as arcs, and delay
hotspots by origin, with zoom, pan, risk-colored nodes, and click-to-inspect panels.

### Simulation Center
What-if modeling for supplier shutdown, port closure, warehouse outage, demand spike, and
weather disruption, quantifying revenue, inventory, shipment, and operational impact with
mitigation recommendations.

### Operations Copilot
A chat interface that answers operational questions grounded in a live context snapshot.
Uses OpenAI when configured; otherwise a deterministic local engine produces consistent,
auditable answers without external dependencies.

### Executive Briefs
One-click generation of a structured briefing (Executive Summary, Current Risks,
Operational Performance, Key Recommendations, Strategic Concerns), exportable to Markdown
and PDF.

### Public Website
A separate, light-themed marketing site (`app/(marketing)`) presents the product to
visitors, with solutions, platform, integrations, security, pricing, documentation, and a
get-started workspace chooser, kept fully distinct from the authenticated application.

---

## Technology Stack

| Layer | Technology | Rationale |
| --- | --- | --- |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Recharts | Server/client boundaries, type-safe API integration, maintainable styling, production builds |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic v2 | Auto-generated OpenAPI, request validation, a testable plain-Python service layer |
| Database | PostgreSQL 16 (SQLite for local evaluation) | Relational model + JSON columns + concurrent access; SQLite removes infra for local dev |
| Auth | Email-first WorkOS SSO + httpOnly `supply_session` cookies; org-scoped API tokens | Enterprise SSO without provider buttons; no JWT in localStorage |
| Multi-tenancy | `organization_id` on domain tables + PostgreSQL FORCE RLS | Shared-schema isolation for B2B SaaS |
| Billing | Stripe Checkout, Customer Portal, signed webhooks (idempotent) | Seat/plan lifecycle for commercial pilots |
| Connectors | Connector SDK: Dynamics 365 BC, Salesforce, UPS | Real OAuth/API integrations (sandbox-validated before GA) |
| AI | OpenAI (optional) + deterministic local engine | Natural-language interaction without a single point of failure |
| Packaging | Docker Compose (API + worker + Redis + Postgres + frontend) | Local parity with multi-service production |

---

## Screenshots

Screenshots and product imagery live in [`docs/screenshots/`](docs/screenshots). Add PNG
captures of Mission Control, the Network View, the Simulation Center, and the Data
Pipeline Monitor there and reference them here.

> The application runs locally with a fully seeded dataset, so every screen is populated
> immediately after installation.

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (optional — SQLite works for local evaluation)
- Docker and Docker Compose (optional)

### Quick start (local, SQLite)

From the repository root:

```bash
./start.sh
```

This frees ports 3000 and 8000, prepares a SQLite database on first run, and starts both
services. Open http://127.0.0.1:3000/login — enter your work email and Continue
(WorkOS). For local-only sign-in when WorkOS is unset, enable
`NEXT_PUBLIC_DEV_LOGIN=true` in development.
Stop with `./stop.sh`.

---

## Docker Setup

```bash
cp .env.example .env
docker compose up --build
```

The backend container initializes tables and seeds data on first boot when
`SEED_ON_STARTUP=true`.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API docs (ReDoc) | http://localhost:8000/redoc |

---

## Configuration

Configuration is environment-driven. Copy `.env.example` to `.env` for Docker Compose, or
set variables directly for local development. No secrets are committed to the repository.

### Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | `postgresql+psycopg://...` (production) or `sqlite:///./dev.db` (local) |
| `SESSION_SECRET` | Yes | Session signing secret (32+ characters) |
| `CREDENTIALS_ENCRYPTION_KEY` | Yes (prod) | Fernet key for connector credential encryption |
| `WORKOS_API_KEY` / `WORKOS_CLIENT_ID` | Yes (prod) | WorkOS AuthKit |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Yes (billing) | Stripe API + webhook verification |
| `REDIS_URL` | Yes (connectors) | Queue for ARQ worker |
| `REDIS_PASSWORD` | Yes (Compose prod) | Password injected into the bundled Redis service |
| `CORS_ORIGINS` / `FRONTEND_URL` | Yes | Allowed browser origins |
| `NEXT_PUBLIC_API_URL` | Yes (frontend) | Backend URL reachable from the browser |
| `ENVIRONMENT` | Yes (prod) | `production` fails closed without required secrets |
| `FEATURE_BILLING_ENFORCE` | No | When `true`, plan seat/usage limits are enforced |
| `SEED_ON_STARTUP` | No | Optional demo seed (never enable in production tenants) |

---

## Running Locally

Start a database (or use SQLite):

```bash
docker compose up db -d
```

Backend:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://atlasops:atlasops@localhost:5432/atlasops"
python -m app.cli init-db
python -m app.cli seed --if-empty
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm ci
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev -- -H 0.0.0.0 -p 3000
```

### Tests

```bash
cd backend && python -m pytest
```

Integration tests run against an isolated SQLite database and cover authentication, RBAC,
and core API endpoints.

---

## Local development auth

Production and staging use **email-first WorkOS SSO** (see [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)).
For local development when WorkOS keys are unset and `ENVIRONMENT=development`,
`POST /api/v1/auth/dev-login` is available and the login UI shows a dev form only when
`NODE_ENV=development` and `NEXT_PUBLIC_DEV_LOGIN=true`. There are **no** shared demo passwords for production.

Optional org data seeding (`python -m app.cli seed`) is for empty local databases only —
never enable `SEED_ON_STARTUP` for customer tenants.


---

## Enterprise Deployment

**Single host (Docker Compose):** Suitable for internal deployments and design-partner
pilots. Place a reverse proxy (Caddy, Nginx, Traefik) in front for TLS. Set strong values
for `SESSION_SECRET`, `CREDENTIALS_ENCRYPTION_KEY`, and `POSTGRES_PASSWORD`. Include the
`worker` + `redis` services for connector sync.

**Split deployment:** Frontend on a managed host (e.g. Vercel), backend/worker/Redis and
PostgreSQL on a managed host (e.g. Render). Set `NEXT_PUBLIC_API_URL` to the backend's
public URL and `CORS_ORIGINS` / `FRONTEND_URL` to the frontend domain.

Sessions are cookie-based (not JWT). Scale API replicas behind a sticky or shared session
store as needed; PostgreSQL and Redis are the primary data-plane scaling considerations.
Full instructions: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

**Human staging / design-partner ops:** follow [`docs/OPERATIONS_MANUAL.md`](docs/OPERATIONS_MANUAL.md)
(deploy, WorkOS/Stripe/connectors, soak, k6 load, DR, Go/No-Go).

---

## Data Integration

Supply v2 is multi-tenant. Tenant data arrives through:

- **CSV / Excel import** — validate → preview → commit into tenant-owned domain tables,
  with `ImportJob` + audit log rows.
- **Connector SDK** — production connectors for **Dynamics 365 Business Central**,
  **Salesforce**, and **UPS**. Credentials are encrypted at rest. Sync runs through the
  connector registry (worker preferred for long jobs).

There is no simulated ERP sync path in the API. Other ERPs (SAP, Oracle) are **not**
shipped connectors. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

---

## Security

Supply v2 security model (see [`SECURITY.md`](SECURITY.md) / [`docs/SECURITY.md`](docs/SECURITY.md)):

- WorkOS authentication with httpOnly, Secure, SameSite session cookies
- Organization membership + permission catalog (`require_permission`) on API routes
- PostgreSQL FORCE RLS on tenant tables (`app.current_org_id` GUC)
- Org-bound API tokens (`sup_…`); revoked/rotated tokens rejected
- Stripe webhook signature verification + `stripe_events` idempotency
- Encrypted connector credentials; production fails closed without required secrets
- No demo passwords or JWT-in-localStorage auth path

Set `ENVIRONMENT=production` only with WorkOS, session secret, encryption key, and TLS.

---

## Roadmap

Foundation complete for Supply v2. Remaining work toward GA (see [`ROADMAP.md`](ROADMAP.md)
and [`docs/reports/RC1_RELEASE_READINESS.md`](docs/reports/RC1_RELEASE_READINESS.md)):

- Staging soak with live WorkOS, Stripe test mode, and one connector sandbox
- Enqueue connector sync on the ARQ worker by default (not inline request)
- Expand Playwright coverage for full browser onboarding once staging secrets exist
- Audit log explorer UI and Settings surfaces for tokens/billing
- Additional connectors beyond Dynamics BC, Salesforce, and UPS

---

## Project Structure

```
atlasops/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── api/             routers + RBAC dependencies
│   │   ├── core/            config, database, security
│   │   ├── models/          SQLAlchemy ORM models + enums
│   │   ├── schemas/         Pydantic contracts
│   │   ├── services/        domain logic (metrics, risk, alerts, simulation, ingestion, AI)
│   │   ├── seed/            synthetic data engine
│   │   ├── cli.py           operational commands
│   │   └── main.py          app assembly
│   ├── alembic/             database migrations
│   ├── tests/               pytest integration tests
│   └── requirements.txt
├── frontend/                Next.js application
│   ├── app/
│   │   ├── (marketing)/     public website
│   │   ├── (app)/           authenticated application
│   │   └── login/           authentication
│   ├── components/          UI, charts, marketing, shared widgets
│   └── lib/                 API client, auth, hooks, types
├── docs/                    OPERATIONS_MANUAL, STAGING, API, DATABASE, …
├── load/k6/                 Staging load tests
├── docker-compose.yml
├── docker-compose.staging.yml
├── ARCHITECTURE.md · ROADMAP.md · SECURITY.md · CONTRIBUTING.md
├── CHANGELOG.md · CODE_OF_CONDUCT.md · LICENSE
└── start.sh · stop.sh
```

---

## API Documentation

The API is versioned under `/api/v1` and documented interactively:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

A written reference is available in [`docs/API.md`](docs/API.md).

---

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
development workflow, coding standards, and pull request process, and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.

---

## License

Released under the [MIT License](LICENSE).

---

## Closing Thoughts

Supply chain operations produce a large volume of data that is genuinely useful and
genuinely hard to act on. The data exists across systems that were purchased, configured,
and maintained for good reasons — but those systems were not designed to answer "what
should we do next?" in a single conversation.

ATLASOPS explores how operational data can be unified, interpreted, and connected to
decision support: health scoring that reflects actual network conditions, risk
assessments tied to specific entities, recommended actions with stated impact and cost,
and simulations that let teams test responses before committing resources.

The platform is intended to support operators and decision makers, not replace them.
Simulations inform; they do not execute. Recommendations suggest; they do not act. The
Copilot assists investigation; it does not autonomously manage the supply chain. Human
judgment remains central — the system's role is to make that judgment better informed,
faster, and based on a shared operational picture.
