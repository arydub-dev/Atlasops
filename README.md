# SupplyChain Command Center

A supply chain operations platform that unifies shipment visibility, inventory intelligence, supplier performance, risk detection, disruption simulation, and AI-assisted decision support into a single environment.

It is built for operations teams, supply chain leaders, and enterprise architects who need one operational picture across a distributed network — and who need to move from detecting problems to deciding what to do about them.

<p align="center">
  <img alt="Next.js 15" src="https://img.shields.io/badge/Next.js-15-black?logo=next.js" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python_3.12-009688?logo=fastapi&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green" />
</p>

---

## Overview

Most organizations manage supply chain operations across multiple systems that were never designed to work together:

- ERP for orders and master data
- WMS for warehouse positions
- TMS for carrier tracking
- Supplier portals, spreadsheets, and email for exceptions
- Separate reporting tools for leadership reviews

The result is predictable: operators spend time reconciling data instead of acting on it. A delayed shipment in the TMS may not surface alongside the inventory position it affects. A deteriorating supplier may not appear in the same view as the shipments and SKUs that depend on them. Leadership briefings are assembled manually from exports that are already stale.

SupplyChain Command Center addresses this by maintaining a **unified operational model** — suppliers, warehouses, products, inventory, shipments, alerts, and risk assessments — and exposing it through surfaces designed for daily operations, analysis, and executive review.

The platform does not replace ERP or WMS systems. It sits above them as an operational intelligence layer: aggregating signals, scoring risk, recommending responses, and supporting what-if analysis before decisions are committed.

---

## Core Questions

The system is organized around three questions that operations and leadership teams ask during every shift:

| Question | How the platform answers it |
| --- | --- |
| **What is happening?** | Mission Control aggregates health scores, KPIs, open alerts, and trend charts. Shipments, inventory, warehouses, and suppliers each have dedicated operational views. The Network View shows geographic topology and active routes. |
| **Why is it happening?** | Risk assessments score exposure by category (supplier, shipment, inventory, geographic). The situation report names contributing suppliers, warehouses, and trends. Analytics surfaces concentration and performance patterns. |
| **What should happen next?** | Recommended actions are ranked by priority with expected impact and estimated cost. Alerts include prescribed response guidance. The Simulation Center models disruption scenarios. The Operations Copilot answers operational questions grounded in live data. |

Different modules contribute to different parts of this loop, but the intent is consistent: reduce the time between detecting an exception and choosing a response.

---

## Features

Each capability below addresses a specific operational challenge. They are described in terms of what operators need, not what the UI contains.

### Mission Control

**Challenge:** Operations leaders need a single starting point each morning — not ten tabs across five systems.

**What it does:** Mission Control is the primary command surface. It presents a composite supply chain health score (weighted across on-time delivery, inventory health, supplier reliability, and risk), executive KPIs, an AI situation report explaining current conditions, ranked recommended actions, a critical alert feed, and supporting trend charts for shipments, delays, inventory, and supplier performance.

**Why it matters:** It compresses the first hour of a shift — scanning exceptions, understanding context, and identifying priorities — into one screen.

### Shipments

**Challenge:** In-transit inventory is often the hardest to see clearly. Delays are discovered late, and status updates are scattered across carrier portals and email.

**What it does:** Full shipment lifecycle management with search, filter, sort, and pagination. Each shipment has a tracking timeline built from discrete events (status, location, timestamp). Delay risk is scored per shipment. Operations managers can update status subject to role permissions.

**Why it matters:** Gives operators a single place to triage in-transit exceptions and communicate status without switching systems.

### Inventory

**Challenge:** Stockout risk is usually visible only after it materializes, because inventory positions are spread across warehouses and disconnected from demand signals.

**What it does:** Multi-warehouse inventory views with health classification (healthy, low stock, overstock, stockout). Reorder recommendations based on reorder points, safety stock, and average daily demand. Historical snapshots support trend analysis without mixing live and archived positions.

**Why it matters:** Surfaces shortage risk early enough to trigger replenishment or inter-warehouse transfers before customer impact.

### Warehouses

**Challenge:** Distribution network capacity is often managed facility-by-facility, without a network-level view of utilization and risk concentration.

**What it does:** Warehouse cards showing capacity, current inventory, utilization percentage, regional assignment, and risk level. Search, region filter, and sort by utilization or capacity.

**Why it matters:** Helps logistics teams identify near-capacity facilities and rebalance inbound flow before bottlenecks affect fulfillment.

### Suppliers

**Challenge:** Supplier performance data lives in scorecards, emails, and quarterly reviews — not in the operational tools used during daily exception management.

**What it does:** Supplier rankings with scorecards covering delivery reliability, average delay, fulfillment rate, and defect rate. Performance trends over six months. Identification of top and bottom performers.

**Why it matters:** Connects supplier deterioration to the shipments and inventory positions that depend on them, enabling earlier escalation and dual-sourcing decisions.

### Risk Intelligence

**Challenge:** Risk is often discussed qualitatively ("we're exposed in Asia") without a scored, ranked, actionable assessment tied to specific entities.

**What it does:** Automated risk engine scoring exposure from 0–100 across four categories: supplier, shipment, inventory, and geographic. Each assessment includes a severity level (Low → Critical), a description, contributing factors, and a recommendation. Risk can be recomputed on demand.

**Why it matters:** Converts diffuse concern into prioritized, entity-level assessments that feed Mission Control recommendations and executive briefs.

### Alert Management

**Challenge:** Alert fatigue is common when every system generates notifications without priority, context, or a resolution workflow.

**What it does:** Structured alerts with types (delayed shipment, stockout risk, supplier failure risk, demand spike), priority levels (Low → Critical), and a lifecycle (Open → Acknowledged → Resolved). Filtering by type and priority. Statistics on open and resolved alerts.

**Why it matters:** Gives operators a triage queue with clear severity and a path to resolution, rather than an undifferentiated notification stream.

### Analytics Hub

**Challenge:** Leadership needs trend context — not just current-state snapshots — to understand whether conditions are improving or deteriorating.

**What it does:** Delivery performance, supplier performance, inventory health, and forecast-style analytics. Visualizations include time series, bar charts, donut charts, and heatmaps.

**Why it matters:** Supports weekly and monthly reviews with historical context that point-in-time dashboards cannot provide.

### Network View

**Challenge:** Geographic relationships between suppliers, warehouses, and shipment lanes are difficult to see in tabular data.

**What it does:** Interactive map showing warehouses and suppliers as nodes, active shipment routes as arcs, and delay hotspots by origin city. Zoom, pan, risk-colored nodes, and click-to-inspect detail panels showing utilization, active shipments, and open alerts.

**Why it matters:** Makes concentration risk and lane-level delay patterns visible in a form that supports spatial reasoning about the network.

### Simulation Center

**Challenge:** Disruption response is often reactive because there is no structured way to model impact before a scenario occurs.

**What it does:** What-if modeling for supplier shutdown, port closure, warehouse outage, demand spike, and weather disruption. Each simulation quantifies revenue, inventory, shipment, and operational risk impact, and produces mitigation recommendations in plain language. Results are persisted for comparison.

**Why it matters:** Lets teams pressure-test contingency plans and quantify tradeoffs before committing resources.

### Operations Copilot

**Challenge:** Operational questions ("why are delays up?", "which warehouse is at risk?", "what should leadership do?") require manual investigation across multiple views.

**What it does:** A chat interface that answers operational questions grounded in a live context snapshot (KPIs, risk summary, supplier performance, warehouse utilization, open alerts, data source status). Uses OpenAI when an API key is configured; falls back to a deterministic local engine that produces consistent, auditable answers without external dependencies.

**Why it matters:** Reduces investigation time for ad-hoc questions while keeping responses tied to actual system data rather than general knowledge.

### Executive Briefs

**Challenge:** Leadership briefings are assembled manually from exports, often hours after the data was current.

**What it does:** One-click generation of a structured briefing: Executive Summary, Current Risks, Operational Performance, Key Recommendations, and Strategic Concerns. Exportable to Markdown and PDF (browser print).

**Why it matters:** Produces a consistent, data-grounded narrative for leadership alignment without manual report assembly.

### Data Integration

**Challenge:** Operational intelligence is only as current as the data feeding it. Most organizations cannot replace existing ERP, WMS, and TMS investments overnight.

**What it does:** A data ingestion layer supporting CSV and Excel file import (with validation, column mapping, and per-row error reporting) and connector templates for SAP ERP, Oracle ERP, Salesforce CRM, Microsoft Dynamics, WMS, TMS, and generic REST APIs. A Pipeline Monitor tracks every import and sync run. Ingested records land in the same domain tables used by risk scoring, analytics, and the Copilot.

**Why it matters:** Provides a practical path to connected operations without requiring a full system replacement. File import alone is sufficient for many evaluation and pilot deployments.

The platform ships with a seeded dataset so every surface is operational immediately. External data ingestion is additive — it does not remove or replace the seeded data.

---

## Architecture

The system is organized into three layers. Each layer has a distinct responsibility; data flows upward from ingestion to decision support.

```
┌─────────────────────────────────────────────────────────────┐
│  DECISION LAYER                                             │
│  Mission Control · Situation Reports · Recommended Actions  │
│  Operations Copilot · Executive Briefs · Simulations        │
├─────────────────────────────────────────────────────────────┤
│  OPERATIONAL LAYER                                          │
│  Shipments · Inventory · Warehouses · Suppliers             │
│  Alerts · Risk Assessments · Analytics · Network View       │
├─────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                 │
│  Domain tables · Seeded dataset · CSV/Excel import          │
│  Connector framework · Pipeline jobs                          │
└─────────────────────────────────────────────────────────────┘
```

```mermaid
flowchart TB
  subgraph Decision["Decision Layer"]
    MC["Mission Control / Insights"]
    COP["Operations Copilot"]
    BRIEF["Executive Briefs"]
    SIM["Simulation Engine"]
  end

  subgraph Operational["Operational Layer"]
    SHIP["Shipments"]
    INV["Inventory"]
    RISK["Risk Engine"]
    ALERT["Alert Engine"]
    MET["Metrics / Analytics"]
    NET["Network View"]
  end

  subgraph Data["Data Layer"]
    DB[("PostgreSQL / SQLite")]
    SEED["Synthetic Seed"]
    ING["Ingestion Pipeline<br/>CSV · Excel · Connectors"]
  end

  ING --> DB
  SEED --> DB
  DB --> MET
  DB --> RISK
  DB --> ALERT
  DB --> SHIP
  DB --> INV
  DB --> NET
  MET --> MC
  RISK --> MC
  ALERT --> MC
  MET --> COP
  RISK --> COP
  MET --> BRIEF
  RISK --> BRIEF
  DB --> SIM
```

### How data flows

1. **Ingestion.** External data enters through file upload or connector sync. The ingestion pipeline validates rows, maps columns to domain fields, and writes to the same tables used by the rest of the platform. Each run is logged as a pipeline job.

2. **Operational computation.** The metrics service aggregates KPIs and trends. The risk engine scores exposure by category and entity. The alert engine generates alerts from operational state. These run against live database records.

3. **Decision synthesis.** The insights service combines KPIs, risk, and alerts into a health score, situation report, and ranked recommended actions. All three are computed deterministically from live data — they do not depend on an LLM.

4. **AI augmentation.** The Operations Copilot and optional OpenAI integration add natural-language interaction on top of the same context snapshot. The local fallback engine ensures this works without external API access.

5. **Simulation.** The simulation engine reads current network state and applies scenario parameters to estimate impact. Results are persisted and include mitigation recommendations.

### Backend structure

The backend follows a thin-controller, rich-service pattern:

| Layer | Location | Responsibility |
| --- | --- | --- |
| Routers | `backend/app/api/routers/` | HTTP surface, validation, status codes |
| Dependencies | `backend/app/api/deps.py` | JWT validation, RBAC enforcement |
| Services | `backend/app/services/` | Domain logic (metrics, risk, alerts, simulation, insights, AI, ingestion, geo) |
| Models | `backend/app/models/` | SQLAlchemy ORM definitions |
| Schemas | `backend/app/schemas/` | Pydantic request/response contracts |

Aggregate endpoints (`/mission-control`, `/network`) return everything a page needs in a single request to reduce frontend-backend round trips.

Further detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md)

---

## Data Model

The operational model centers on entities that supply chain teams already think in terms of. Database implementation details are in [`docs/DATABASE.md`](docs/DATABASE.md).

```mermaid
erDiagram
  SUPPLIERS ||--o{ PRODUCTS : provides
  SUPPLIERS ||--o{ SHIPMENTS : fulfills
  WAREHOUSES ||--o{ INVENTORY : holds
  WAREHOUSES ||--o{ SHIPMENTS : receives
  PRODUCTS ||--o{ INVENTORY : tracked_as
  PRODUCTS ||--o{ SHIPMENTS : moves
  SHIPMENTS ||--o{ SHIPMENT_EVENTS : has
```

| Entity | Operational meaning |
| --- | --- |
| **Suppliers** | Vendors that provide products. Tracked by reliability score, delay patterns, fulfillment rate, and regional assignment. |
| **Warehouses** | Distribution facilities with capacity, utilization, geographic location, and risk level. |
| **Products** | SKUs with cost, price, category, lead time, and supplier association. |
| **Inventory** | Stock position for a product at a warehouse. Includes reorder point, safety stock, max stock, and average daily demand. Current positions are flagged separately from historical snapshots. |
| **Shipments** | In-transit or delivered movements from origin to destination warehouse. Includes carrier, status, delay risk, units, value, and ETA. |
| **Shipment Events** | Discrete tracking events (status change, location, timestamp) forming a shipment timeline. |
| **Alerts** | Operational exceptions requiring attention. Typed, prioritized, and managed through a resolution lifecycle. |
| **Risk Assessments** | Scored evaluations of exposure for a specific entity and category, with recommendations. |
| **Simulations** | Persisted what-if scenarios with parameters, computed impacts, and results. |

Additional tables support users, authentication, AI report history, audit logs, data source connectors, import pipeline jobs, and application settings.

---

## Design Principles

### Decision Support Over Reporting

Charts and tables are inputs to decisions, not the output. The platform prioritizes health scores, ranked actions, situation narratives, and simulation impact over static dashboards. Every major surface is designed to answer "so what?" and "what next?" — not just "what is the number?"

### Explainable Recommendations

Health scores decompose into weighted KPI components. Situation reports cite specific suppliers, warehouses, and trends. Risk assessments include scored factors and explicit recommendations. The local AI engine produces answers from a structured context snapshot, not from opaque model reasoning. Recommendations should be defensible in a leadership meeting.

### Progressive Adoption

The platform runs fully on a seeded dataset with no external integrations required. CSV and Excel import provide a low-friction path to connected operations. Connector templates (SAP, Oracle, Salesforce, Dynamics, WMS, TMS, REST) demonstrate enterprise integration architecture without requiring immediate production connector implementation. Each step adds value without blocking the previous one.

### Human-in-the-Loop Operations

Simulations inform decisions; they do not execute them. Alerts are acknowledged and resolved by people. Recommended actions include estimated cost and expected impact so operators can apply judgment. The Copilot assists investigation; it does not autonomously change shipment status, reorder inventory, or contact suppliers.

### Enterprise Integration Readiness

Ingestion follows a defined pipeline: connector → validation → transformation → database. Imported records use the same domain tables as seeded data, so risk scoring, analytics, and the Copilot activate automatically. API keys are stored masked. Pipeline runs are logged with row counts, duration, and error summaries. The ingestion architecture is documented separately for teams evaluating deployment.

---

## Example Operational Workflows

These examples show how different parts of the platform work together during realistic scenarios.

### Supplier reliability deterioration

| Stage | What happens |
| --- | --- |
| **Trigger** | A supplier's delivery reliability drops below threshold. The risk engine creates a supplier-category assessment. An alert of type `supplier_failure_risk` is generated. |
| **Investigation** | The operator opens Mission Control and sees the alert in the critical feed. The situation report names the supplier. The Suppliers page shows the scorecard and six-month trend. |
| **Analysis** | Risk Intelligence shows the scored assessment with contributing factors. Analytics reveals which shipments and SKUs depend on this supplier. Network View shows the supplier's geographic position relative to affected warehouses. |
| **Recommended actions** | Mission Control recommends activating a backup supplier and placing the vendor on a recovery plan (ranked by priority with estimated impact and cost). The operator can run a Simulation Center scenario (supplier shutdown) to quantify exposure before escalating to leadership. |

### Inventory shortage risk

| Stage | What happens |
| --- | --- |
| **Trigger** | Inventory for a high-velocity SKU at a warehouse falls below its reorder point. The alert engine generates an `inventory_stockout_risk` alert. |
| **Investigation** | Inventory page shows the SKU in low-stock status with days-of-supply estimate. The warehouse card shows utilization context. |
| **Analysis** | Risk assessment scores inventory-category exposure. Analytics shows demand trend for the SKU. Mission Control includes the shortage in the situation report. |
| **Recommended actions** | Alert response guidance suggests emergency replenishment or inter-warehouse transfer. Recommended actions rank the response by expected stockout-risk reduction. If the shortage is network-wide, Simulation Center can model a demand spike to stress-test whether current safety stock is adequate. |

### Regional disruption affecting shipments

| Stage | What happens |
| --- | --- |
| **Trigger** | Multiple shipments from the same origin city are delayed simultaneously. Delay hotspots appear on the Network View. Geographic risk assessments are elevated. |
| **Investigation** | Shipments page filtered by origin shows the cluster. Network View highlights the hotspot with delay counts. |
| **Analysis** | Analytics shows delivery performance trend for the affected lane. Risk Intelligence scores geographic-category exposure. The Operations Copilot can answer "why are delays increasing?" with supplier and lane context. |
| **Recommended actions** | Recommended actions suggest expediting high-value shipments and pre-positioning safety stock at affected destinations. Simulation Center can model a port closure scenario to estimate downstream inventory impact. |

### Warehouse capacity constraints

| Stage | What happens |
| --- | --- |
| **Trigger** | A warehouse approaches high utilization. Its risk level elevates. Open alerts may reference capacity. |
| **Investigation** | Warehouses page shows utilization bar and risk level. Mission Control KPIs reflect inventory health score decline. |
| **Analysis** | Network View shows inbound routes targeting the facility. Inventory page shows which SKUs are driving volume. Analytics shows utilization trend. |
| **Recommended actions** | Recommended actions suggest rebalancing inbound flow to alternate sites. Simulation Center can model a warehouse outage to quantify stranded inventory and disrupted shipments. |

---

## Technology Stack

Each technology choice reflects a specific requirement. The stack prioritizes type safety, API clarity, and operational simplicity over novelty.

### Frontend — Next.js 15, TypeScript, Tailwind CSS

**Why:** Next.js App Router provides server and client component boundaries, file-based routing, and production-ready builds. TypeScript catches integration errors between the typed API client and backend schemas. Tailwind enables consistent, maintainable styling without a heavy component framework lock-in.

Recharts handles time-series and distribution charts. A shadcn-style component layer (Radix UI primitives) provides accessible, composable UI elements. `next-themes` supports dark and light mode via CSS variables.

### Backend — FastAPI, Python 3.12, SQLAlchemy 2.0

**Why:** FastAPI generates OpenAPI documentation automatically, validates requests with Pydantic v2, and performs well for I/O-bound API workloads. Python's ecosystem supports data processing (ingestion, analytics) without a separate ETL runtime.

SQLAlchemy 2.0 provides a mature ORM with explicit query construction. The service layer is plain Python functions — testable without HTTP, swappable without framework coupling. Alembic manages schema migrations for production deployments.

### Database — PostgreSQL 16 (SQLite for local evaluation)

**Why:** PostgreSQL handles the relational model (suppliers, warehouses, inventory, shipments with events), JSON columns (risk factors, simulation parameters), and concurrent API access. SQLite is supported for local development and CI to eliminate infrastructure dependencies during evaluation.

The `is_current` flag on inventory records separates live positions from historical snapshots, keeping live queries fast while preserving trend data for analytics.

### Authentication — JWT with bcrypt, RBAC

**Why:** JWT tokens allow stateless API authentication suitable for split frontend/backend deployment. bcrypt password hashing is well-understood and sufficient for this deployment model. Four roles (Admin, Operations Manager, Analyst, Executive) gate write operations without over-engineering permission granularity.

OAuth2 password flow is used for login. Tokens are validated on every authenticated request. The frontend stores tokens in localStorage and redirects on 401.

### AI Layer — OpenAI (optional) + deterministic local engine

**Why:** LLMs add value for natural-language interaction but should not be a single point of failure. Core intelligence (health scores, situation reports, recommended actions, executive briefs) is computed deterministically from live data. The Copilot uses OpenAI when `OPENAI_API_KEY` is set; otherwise a rule-based local engine produces grounded answers from the same context snapshot.

This means every AI surface works in air-gapped environments, CI pipelines, and local development without external API access.

### Deployment Model — Docker Compose, split Vercel + Railway/Render

**Why:** Docker Compose provides a single-command local and VPS deployment. Split deployment (static frontend on Vercel, API on Railway/Render) matches common team ownership patterns (frontend and backend deployed independently) and scales each tier separately.

---

## Running the Platform

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

This frees ports 3000 and 8000, seeds a SQLite database on first run, and starts both services. Open http://127.0.0.1:3000 and sign in with `ops@scc.io` / `ops12345`.

Stop with:

```bash
./stop.sh
```

### Local development (PostgreSQL)

Start a database:

```bash
docker compose up db -d
```

Backend:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://scc:scc_password@localhost:5432/scc"
python -m app.cli init-db
python -m app.cli seed --if-empty
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev -- -H 0.0.0.0 -p 3000
```

### Docker deployment

```bash
cp .env.example .env
docker compose up --build
```

The backend container initializes tables and seeds data on first boot when `SEED_ON_STARTUP=true`.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| API docs (ReDoc) | http://localhost:8000/redoc |

### Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `DATABASE_URL` | Yes | `postgresql+psycopg://...` or `sqlite:///./dev.db` |
| `JWT_SECRET_KEY` | Yes | Signing key for access tokens (32+ characters in production) |
| `JWT_ALGORITHM` | No | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default: `1440` (24 hours) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins for the frontend |
| `OPENAI_API_KEY` | No | Enables OpenAI for the Copilot; omit to use local engine |
| `OPENAI_MODEL` | No | Default: `gpt-4o-mini` |
| `NEXT_PUBLIC_API_URL` | Yes (frontend) | Backend URL reachable from the browser |
| `ENVIRONMENT` | No | `development` or `production` |
| `SEED_ON_STARTUP` | No | Seed database on container start (Docker only) |

See `.env.example` for the full Docker Compose configuration.

### Database initialization and seed data

```bash
python -m app.cli init-db                              # create tables
python -m app.cli seed --if-empty                      # seed only when empty
python -m app.cli seed --scale demo                    # lighter dataset (~faster)
python -m app.cli seed --scale full                    # full dataset (~100k inventory rows)
python -m app.cli create-user EMAIL NAME ROLE PASSWORD # add a user
python -m app.cli reset                                # drop and recreate all tables
```

The seed engine generates deterministic synthetic data: 50 suppliers, 100 products, 25 warehouses, 5,000 shipments with tracking events, and approximately 100,000 inventory records (current positions plus weekly historical snapshots). Four demo users are created with distinct roles.

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@scc.io` | `admin1234` |
| Operations Manager | `ops@scc.io` | `ops12345` |
| Analyst | `analyst@scc.io` | `analyst123` |
| Executive | `exec@scc.io` | `exec12345` |

### Tests

```bash
cd backend && PYTHONPATH=. pytest
```

Integration tests run against an isolated SQLite database and cover authentication, RBAC, and core API endpoints.

---

## Deployment

### Development

Local development uses hot-reload on both tiers (`uvicorn --reload`, `next dev`). SQLite eliminates the need for a running PostgreSQL instance during initial evaluation. The seeded dataset provides realistic data volume without manual setup.

### Production

**Single host (Docker Compose):** Suitable for internal deployments, pilots, and environments where a single VPS or on-premise host is available. Place a reverse proxy (Caddy, Nginx, Traefik) in front for TLS termination. Set strong values for `JWT_SECRET_KEY` and `POSTGRES_PASSWORD`.

**Split deployment (Vercel + Railway/Render):** Frontend on Vercel (static/SSR Next.js build). Backend and PostgreSQL on Railway or Render. Set `NEXT_PUBLIC_API_URL` to the backend's public URL and `CORS_ORIGINS` to the frontend's domain.

Full instructions: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

### Scaling considerations

- The API is stateless (JWT auth) and can be horizontally scaled behind a load balancer.
- PostgreSQL is the primary scaling bottleneck. Read replicas can serve analytics queries if volume grows.
- Aggregate endpoints (`/mission-control`, `/network`) reduce request volume but increase per-request computation. Cache headers or application-level caching can be added for high-traffic deployments.
- The ingestion pipeline is synchronous per request. High-volume file imports should move to background job processing (see Roadmap).

### Security considerations

- Change `JWT_SECRET_KEY` and database passwords before any production deployment.
- HTTPS is required in production. Configure TLS at the reverse proxy or platform level.
- RBAC gates write operations (shipment updates, alert management, data import, connector configuration). Executives have read access.
- Connector API keys are stored masked (last four characters only). This is appropriate for demonstration and pilot deployments; production deployments should use a secrets manager and encrypted storage.
- CORS is restricted to configured origins. Do not use wildcard origins in production.

### Data integration considerations

- File import (CSV, Excel) is the fastest path to connected operations for pilots.
- Connector templates demonstrate architecture; production SAP/Oracle/Salesforce integrations require customer-specific endpoint configuration, authentication flows, and schema mapping.
- Imported data uses the same domain tables as seeded data. Risk scoring and analytics recompute against the combined dataset.
- Pipeline jobs log every import and sync run for operational monitoring.

### Monitoring considerations

- Backend exposes `/health` for load balancer health checks.
- Application logs are written to stdout (Docker captures them).
- Pipeline Monitor in the UI tracks ingestion run success rates, duration, and failed records.
- Audit logs record user actions (authentication events, data changes) in the `audit_logs` table. An audit log explorer UI is planned (see Roadmap).

---

## Roadmap

Planned improvements reflect operational needs observed during design and deployment planning.

| Enhancement | Why it matters |
| --- | --- |
| **Operational ontology layer** | A formal entity-relationship model above raw tables would enable richer cross-entity queries, consistent naming across integrations, and a foundation for graph-based analysis. |
| **Workflow execution** | Recommended actions and alert responses currently inform operators but do not assign owners, track completion, or measure outcomes. Structured workflow with assignment and status tracking would close the loop from insight to action. |
| **KPI impact tracking** | Measuring whether recommended actions actually improved on-time delivery, reduced stockouts, or lowered risk scores would enable continuous improvement of the recommendation engine. |
| **Additional integrations** | Production-ready connectors for specific ERP, WMS, and TMS platforms with pre-built schema mappings, incremental sync, and webhook support. |
| **Advanced simulations** | Multi-scenario comparison, saved scenario portfolios, and simulation diffs would support quarterly business review and contingency planning workflows. |
| **Agentic investigations** | Multi-step Copilot workflows that autonomously gather context across modules (e.g., trace a delay from shipment → supplier → inventory impact) before presenting a conclusion. |
| **Real-time updates** | WebSocket push for alerts and shipment events would eliminate polling and reduce perceived latency during active operations. |
| **Geospatial basemap** | Vector tile basemap behind the Network View would provide geographic context (coastlines, borders) for international networks. |
| **Forecasting models** | Statistical demand forecasting (ARIMA, Prophet, or similar) replacing heuristic projections for inventory analytics. |
| **Multi-tenant + SSO** | Organization-level data isolation and SAML/OIDC authentication for enterprise identity provider integration. |

---

## Tradeoffs and Limitations

This section describes known constraints honestly. The platform is designed for operational intelligence, not as a replacement for ERP, WMS, or TMS systems.

### Current assumptions

- **Single-organization model.** There is no multi-tenant data isolation. All users share the same dataset. Multi-tenancy is a roadmap item.
- **Synchronous ingestion.** File imports and connector syncs run in the API request lifecycle. Large files (>10k rows) will block the request thread. Background job processing is not yet implemented.
- **Simulated connectors.** ERP, CRM, WMS, and TMS connector templates demonstrate architecture with mock sync behavior. Production deployments require customer-specific integration work.
- **Deterministic risk and simulation.** Risk scores and simulation impacts are computed from heuristic models, not machine learning. They are explainable and consistent but not predictive in the statistical sense.
- **No real-time event streaming.** Data is polled via REST API. Shipment status changes and alert generation are not pushed to clients in real time.

### Known constraints

- **Inventory at scale.** The full seed generates ~100,000 inventory records. Live queries filter on `is_current`, but analytics over the full historical series may slow on very large datasets without indexing or partitioning optimization.
- **Geographic coordinates.** Warehouse and supplier positions use reference coordinates with deterministic jitter, not precise geocoding. The Network View is an operational schematic, not a GIS.
- **AI scope.** The Copilot answers questions about operational state and ingestion status. It does not autonomously execute actions, modify records, or integrate with external communication tools.
- **Workflow gaps.** Alerts support acknowledge/resolve lifecycle, but there is no owner assignment, due date, or escalation path. Recommended actions are advisory, not tracked tasks.

### Design tradeoffs

| Decision | Rationale | Cost |
| --- | --- | --- |
| Deterministic insights over LLM-generated | Recommendations must be auditable and reproducible | Less natural-language variety in situation reports |
| Seeded data ships by default | Every surface is operational immediately without setup | Evaluators must understand seeded vs. imported data coexist |
| SQLite supported for local dev | Removes PostgreSQL dependency for evaluation | SQLite does not represent production concurrency characteristics |
| Monorepo (frontend + backend) | Single repository for coordinated development | Independent versioning and deployment cadence requires discipline |
| JWT in localStorage | Simple split-deployment auth | Vulnerable to XSS; httpOnly cookies would be more secure in production |

### Areas requiring future work

- Encrypted secrets storage for connector credentials
- Background job queue for ingestion and risk recomputation
- Audit log explorer UI
- Automated integration tests for the frontend
- Rate limiting and request throttling on public API endpoints
- Database migration strategy documentation for zero-downtime upgrades

---

## Closing Thoughts

Supply chain operations produce a large volume of data that is genuinely useful and genuinely hard to act on. The data exists across systems that were purchased, configured, and maintained for good reasons — but those systems were not designed to answer "what should we do next?" in a single conversation.

This project explores how operational data can be unified, interpreted, and connected to decision support: health scoring that reflects actual network conditions, risk assessments tied to specific entities, recommended actions with stated impact and cost, and simulations that let teams test responses before committing resources.

The platform is intended to support operators and decision makers, not replace them. Simulations inform; they do not execute. Recommendations suggest; they do not act. The Copilot assists investigation; it does not autonomously manage the supply chain. Human judgment remains central — the system's role is to make that judgment better informed, faster, and based on a shared operational picture.

---

## Documentation

| Document | Description |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture and component overview |
| [`docs/DATABASE.md`](docs/DATABASE.md) | ER diagram, tables, relationships, indexes |
| [`docs/API.md`](docs/API.md) | REST API reference |
| [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) | Data ingestion architecture and connector framework |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production deployment guide |
| [`docs/PRODUCT_POSITIONING.md`](docs/PRODUCT_POSITIONING.md) | Product positioning and value proposition |

## License

MIT
