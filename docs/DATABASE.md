# Database Schema

PostgreSQL 16, modeled with SQLAlchemy 2.0. Migrations are managed with Alembic (`backend/alembic`), and `app.cli init-db` can create the schema directly from the ORM metadata for local development.

## Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ AI_REPORTS : requests
    USERS ||--o{ SIMULATIONS : creates
    USERS ||--o{ IMPORT_JOBS : runs
    DATA_SOURCES ||--o{ IMPORT_JOBS : produces

    SUPPLIERS ||--o{ PRODUCTS : supplies
    SUPPLIERS ||--o{ SHIPMENTS : fulfills

    WAREHOUSES ||--o{ INVENTORY : stocks
    WAREHOUSES ||--o{ SHIPMENTS : receives

    PRODUCTS ||--o{ INVENTORY : tracked_as
    PRODUCTS ||--o{ SHIPMENTS : shipped_in

    SHIPMENTS ||--o{ SHIPMENT_EVENTS : has

    USERS {
        int id PK
        string email UK
        string full_name
        string hashed_password
        enum role
        bool is_active
        datetime created_at
    }
    SUPPLIERS {
        int id PK
        string name
        string country
        string region
        string category
        float supplier_score
        float delivery_reliability
        float average_delay_days
        float order_fulfillment_rate
        float defect_rate
        bool is_active
    }
    WAREHOUSES {
        int id PK
        string name
        string location
        string region
        float latitude
        float longitude
        int capacity
        int current_inventory
        enum risk_level
    }
    PRODUCTS {
        int id PK
        string sku UK
        string name
        string category
        float unit_cost
        float unit_price
        int lead_time_days
        int supplier_id FK
    }
    INVENTORY {
        int id PK
        int warehouse_id FK
        int product_id FK
        int quantity
        int reorder_point
        int safety_stock
        int max_stock
        float avg_daily_demand
        datetime snapshot_date
        bool is_current
    }
    SHIPMENTS {
        int id PK
        string reference UK
        string origin
        string destination
        string carrier
        string current_location
        enum status
        float delay_risk_score
        int units
        float value_usd
        datetime shipped_at
        datetime eta
        datetime delivered_at
        float delay_days
        int supplier_id FK
        int warehouse_id FK
        int product_id FK
    }
    SHIPMENT_EVENTS {
        int id PK
        int shipment_id FK
        enum status
        string location
        string note
        datetime occurred_at
    }
    ALERTS {
        int id PK
        enum alert_type
        enum priority
        enum status
        string title
        string message
        string entity_type
        int entity_id
        datetime resolved_at
        string resolution_note
    }
    RISK_ASSESSMENTS {
        int id PK
        enum category
        enum level
        float score
        string title
        string description
        string recommendation
        string entity_type
        int entity_id
        json factors
    }
    SIMULATIONS {
        int id PK
        string name
        enum simulation_type
        json parameters
        json results
        float inventory_impact
        float shipment_impact
        float revenue_impact_usd
        int created_by FK
    }
    AI_REPORTS {
        int id PK
        string prompt
        string response
        string report_type
        string model
        json context_snapshot
        int user_id FK
    }
    AUDIT_LOGS {
        int id PK
        int user_id FK
        string action
        string resource
        string detail
        string ip_address
        datetime created_at
    }
    DATA_SOURCES {
        int id PK
        string name
        enum connector_type
        enum status
        enum health
        string base_url
        string auth_method
        string api_key_masked
        string sync_frequency
        int record_count
        datetime last_sync_at
        bool is_active
    }
    IMPORT_JOBS {
        int id PK
        string source_name
        string source_type
        string entity_type
        enum status
        int rows_processed
        int rows_imported
        int rows_rejected
        int duration_ms
        json error_summary
        int user_id FK
        datetime created_at
    }
    APP_SETTINGS {
        string key PK
        string value
    }
```

## Tables

| Table | Purpose |
| --- | --- |
| `users` | Authentication & RBAC (admin / operations_manager / analyst / executive) |
| `suppliers` | Supplier master + performance metrics |
| `warehouses` | Distribution centers with capacity & geo coordinates |
| `products` | Product catalog (SKU, cost/price, lead time) |
| `inventory` | Per-warehouse/product stock; `is_current=true` is live state, historical snapshots are `false` |
| `shipments` | Shipments with status, ETA, delay risk and value |
| `shipment_events` | Tracking timeline per shipment |
| `alerts` | Generated operational alerts with lifecycle (open → acknowledged → resolved) |
| `risk_assessments` | Risk-engine output (0–100 score, level, recommendation, factors) |
| `simulations` | Saved scenario simulations and their computed impacts |
| `ai_reports` | Operations Copilot conversations + the data context used |
| `audit_logs` | Audit trail of sensitive actions |
| `data_sources` | Connected Mode connectors: type, status, health, sync metadata |
| `import_jobs` | History of CSV/Excel/connector ingestion runs and outcomes |
| `app_settings` | Key/value application settings (e.g. operating mode) |

## Constraints & indexes (highlights)

- **Check constraints:** score columns bounded `0–100` (`supplier_score`, `delay_risk_score`, risk `score`); `capacity > 0`; `quantity >= 0`.
- **Unique:** `users.email`, `products.sku`, `shipments.reference`.
- **Foreign keys** with sensible `ON DELETE` behavior (`CASCADE` for inventory/events, `SET NULL` for soft references).
- **Indexes:** shipment `status`/`eta`/`supplier`, inventory `(warehouse_id, product_id)` and `is_current`, alerts `(status, priority)`, risk `(category, level)`, audit `(user_id, created_at)`.

## Migrations

```bash
cd backend
# autogenerate a new migration after model changes
alembic revision --autogenerate -m "describe change"
# apply migrations
alembic upgrade head
```

> For convenience in local/dev and the Docker entrypoint, `python -m app.cli init-db` creates the schema directly from ORM metadata. Use Alembic for controlled, versioned changes in production.
