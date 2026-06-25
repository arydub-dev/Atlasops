# ATLASOPS — Architecture

This document describes the system architecture of ATLASOPS: its major components, how
data flows through the platform, the deployment model, the data model, the request
lifecycle, and the data integration pipeline.

ATLASOPS is a three-tier application:

- **Frontend** — Next.js 15 (App Router, TypeScript, Tailwind CSS).
- **Backend** — FastAPI exposing a versioned REST API (`/api/v1`), organized into thin
  controllers over a set of domain services.
- **Database** — PostgreSQL, modeled with SQLAlchemy 2.0 and migrated with Alembic.

An optional OpenAI integration powers the Operations Copilot; when no key is configured,
a deterministic local engine produces grounded answers from the same data context.

---

## 1. System architecture

```mermaid
flowchart TB
    subgraph Client["Browser"]
        UI["Next.js 15 App Router<br/>TypeScript · Tailwind · Recharts"]
    end

    subgraph Edge["API Gateway / Reverse Proxy"]
        GW["TLS termination · routing · CORS"]
    end

    subgraph Backend["FastAPI application"]
        API["REST API<br/>/api/v1/*"]
        AUTH["JWT auth + RBAC"]
        subgraph Services["Domain services"]
            METRICS["Metrics / Analytics"]
            RISK["Risk Engine"]
            ALERT["Alert Engine"]
            SIM["Simulation Engine"]
            INGEST["Ingestion Service"]
            AI["Operations Copilot"]
        end
    end

    DB[("PostgreSQL")]
    OPENAI["OpenAI API<br/>(optional)"]
    EXT["External systems<br/>ERP · WMS · TMS · CRM · CSV · Excel"]

    UI -->|HTTPS JSON + Bearer JWT| GW --> API
    API --> AUTH
    API --> Services
    Services --> DB
    AUTH --> DB
    EXT -->|files / API| INGEST
    AI -.->|when key set| OPENAI
```

**Design principles**

- **Thin controllers, rich services.** Routers validate input and delegate; all domain
  logic lives in `services/` and is unit-testable without HTTP.
- **Single source of truth for the schema.** ORM models drive both `create_all` (dev) and
  Alembic autogenerate (migrations).
- **Deterministic engines.** Risk, simulation and the local Copilot engine are
  deterministic, so results are explainable and reproducible.
- **Graceful AI degradation.** If OpenAI is unavailable, the Copilot transparently falls
  back to the local engine.
- **Stateless backend.** JWT-based auth avoids server-side sessions, enabling horizontal
  scaling behind a load balancer.

---

## 2. Data flow

How operational data becomes decisions:

```mermaid
flowchart LR
    SRC["Operational data<br/>seeded demo or connected sources"] --> NORM["Normalize & validate"]
    NORM --> MODEL[("Unified operational model<br/>PostgreSQL")]
    MODEL --> METRICS["Metrics & analytics"]
    MODEL --> RISK["Risk scoring"]
    METRICS --> MC["Mission Control"]
    RISK --> MC
    RISK --> ALERTS["Alerts"]
    MC --> ACT["Recommended actions"]
    ALERTS --> ACT
    MODEL --> COPILOT["Operations Copilot"]
    ACT --> BRIEF["Executive briefs"]
```

---

## 3. Deployment architecture

ATLASOPS is cloud-native and containerized. The default deployment runs the full stack
with Docker Compose; a split deployment (managed frontend + backend host + managed
Postgres) is also supported.

```mermaid
flowchart TB
    subgraph Single["Single-host deployment (Docker Compose)"]
        PX["Reverse proxy<br/>(TLS)"]
        FE["frontend container<br/>Next.js"]
        BE["backend container<br/>FastAPI + Uvicorn"]
        PG[("postgres container")]
        PX --> FE
        PX --> BE
        BE --> PG
    end

    subgraph Split["Split deployment (managed services)"]
        VFE["Managed frontend host"]
        VBE["Managed backend host"]
        MPG[("Managed PostgreSQL")]
        VFE -->|NEXT_PUBLIC_API_URL| VBE --> MPG
    end
```

**Notes**

- Place a reverse proxy (Caddy, Nginx, Traefik) in front for TLS termination.
- Set strong values for `JWT_SECRET_KEY` and the database password before any non-local
  deployment.
- Configuration is environment-driven; no secrets are committed to the repository.

---

## 4. Database / ER model

The full entity-relationship diagram, column definitions, constraints and indexes are
documented in [`docs/DATABASE.md`](docs/DATABASE.md). Summary of the core entities:

```mermaid
erDiagram
    USERS ||--o{ SIMULATIONS : creates
    USERS ||--o{ AI_REPORTS : requests
    USERS ||--o{ IMPORT_JOBS : runs
    SUPPLIERS ||--o{ PRODUCTS : supplies
    SUPPLIERS ||--o{ SHIPMENTS : fulfills
    WAREHOUSES ||--o{ INVENTORY : stocks
    WAREHOUSES ||--o{ SHIPMENTS : receives
    PRODUCTS ||--o{ INVENTORY : tracked_as
    PRODUCTS ||--o{ SHIPMENTS : shipped_in
    SHIPMENTS ||--o{ SHIPMENT_EVENTS : has
    DATA_SOURCES ||--o{ IMPORT_JOBS : produces
```

Core domain tables: `users`, `suppliers`, `warehouses`, `products`, `inventory`,
`shipments`, `shipment_events`, `alerts`, `risk_assessments`, `simulations`,
`ai_reports`, `audit_logs`. Connected Mode adds `data_sources`, `import_jobs` and
`app_settings`.

---

## 5. Request lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant F as Next.js (client)
    participant A as FastAPI
    participant D as PostgreSQL

    U->>F: Enter credentials
    F->>A: POST /api/v1/auth/login (OAuth2 form)
    A->>D: Verify user, check bcrypt hash
    A-->>F: JWT access token
    F->>F: Store token, attach as Bearer
    U->>F: Open Mission Control
    F->>A: GET /api/v1/mission (Bearer JWT)
    A->>A: Validate JWT + role (RBAC)
    A->>D: Aggregate KPIs, trends, risks, alerts
    A-->>F: JSON response
    F-->>U: Rendered cockpit
```

---

## 6. Integration flow

External systems flow through a consistent ingestion pipeline before reaching the unified
model. CSV and Excel ingestion are fully implemented; enterprise connectors are provided
as configurable templates. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) for detail.

```mermaid
flowchart LR
    EXT["External systems<br/>SAP · Oracle · Salesforce · Dynamics<br/>WMS · TMS · REST · CSV · Excel"]
    EXT --> CONN["Connector layer"]
    CONN --> VAL["Validation layer<br/>type checks · required fields"]
    VAL --> XFORM["Transformation layer<br/>field mapping · FK resolution"]
    XFORM --> DB[("Unified model")]
    DB --> RISK["Risk engine"]
    DB --> AN["Analytics engine"]
    DB --> AI["Operations Copilot"]
```

---

## 7. Backend layering

```
backend/app/
├── core/        config (env), database (engine/session), security (JWT, hashing)
├── models/      SQLAlchemy ORM models + enums — the source of truth for the schema
├── schemas/     Pydantic request/response contracts
├── services/    business logic (no HTTP):
│                  • metrics.py            KPI + trend aggregation
│                  • risk_engine.py        0–100 scoring per category/entity
│                  • alert_engine.py       state → alert generation
│                  • simulation_engine.py  disruption scenarios → impacts
│                  • ingestion.py          connectors, parsing, validation, import
│                  • ai_advisor.py         context builder + OpenAI/local answer
│                  • inventory_logic.py    pure inventory math
├── api/
│   ├── deps.py   get_current_user + require_roles(...) RBAC dependency factory
│   └── routers/  one router per module, thin controllers over services
├── seed/        synthetic data engine
├── cli.py       operational commands (init-db, seed, reset, create-user)
└── main.py      app assembly + CORS + router mounting
```

---

## 8. Frontend architecture

- **Route groups.** A public marketing site (`app/(marketing)`), authenticated
  application (`app/(app)`), and a standalone `/login` route.
- **Auth context** (`lib/auth.tsx`) holds the user, hydrates from `/auth/me`, and
  redirects unauthenticated users.
- **Typed API client** (`lib/api.ts`) attaches the Bearer token, centralizes error
  handling, supports multipart uploads, and auto-redirects on 401.
- **`useFetch` hook** for declarative data loading with loading/error states.
- **Composable UI**: primitives in `components/ui`, chart wrappers in `components/charts`,
  marketing components in `components/marketing`, and shared widgets in `components/shared`.
- **Theming** via `next-themes` with CSS variables (light default; dark mode available in
  the application).

---

## 9. Scaling considerations

- The backend is stateless and horizontally scalable behind a load balancer.
- Database connection pooling is configured in `core/database.py`.
- Heavy aggregation endpoints (mission control, analytics) are read-only and
  cache-friendly; a read replica and an HTTP caching layer are natural next steps.
- The risk and alert engines are designed to run on a schedule (worker/cron) in
  production rather than on demand.
