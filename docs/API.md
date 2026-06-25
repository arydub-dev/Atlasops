# API Reference

Base URL: `http://localhost:8000`
All business endpoints are versioned under `/api/v1` and require a `Bearer` JWT unless noted.

Interactive docs (OpenAPI): **`/docs`** (Swagger UI) and **`/redoc`**. Machine-readable spec: **`/openapi.json`**.

## Authentication

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | public | OAuth2 password flow (`username`=email, `password`). Returns JWT. |
| GET | `/api/v1/auth/me` | any | Current user profile |
| GET | `/api/v1/auth/users` | admin | List users |
| POST | `/api/v1/auth/users` | admin | Create user |

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ops@atlasops.io&password=ops12345"

# Authenticated request
curl http://localhost:8000/api/v1/dashboard \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Dashboard

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/dashboard` | KPIs, trend series, critical alerts, top risks, recommended actions |

## Shipments

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/shipments` | any | List with `q`, `status`, `supplier_id`, `warehouse_id`, `sort_by`, `sort_dir`, `page`, `page_size` |
| GET | `/api/v1/shipments/{id}` | any | Shipment detail + tracking timeline |
| PATCH | `/api/v1/shipments/{id}/status` | ops_manager / admin | Update status (records an event) |

## Inventory

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/inventory/warehouses` | List warehouses |
| GET | `/api/v1/inventory/warehouses/{id}` | Warehouse detail |
| GET | `/api/v1/inventory/health` | Health buckets (ok/low_stock/overstock/stockout) |
| GET | `/api/v1/inventory/items` | Enriched inventory lines (`q`, `warehouse_id`, `status`, pagination) |
| GET | `/api/v1/inventory/reorders` | Reorder recommendations |

## Suppliers

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/suppliers` | List (`q`, `sort_by`, `sort_dir`) |
| GET | `/api/v1/suppliers/ranking` | Ranked scorecards |
| GET | `/api/v1/suppliers/{id}/scorecard` | Single scorecard + trend |
| GET | `/api/v1/suppliers/compare?ids=1,2,3` | Compare suppliers |

## Risk Center

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/risks/summary` | any | Overall score/level, by-category, counts, top risks |
| GET | `/api/v1/risks` | any | Risk register (`category`, `level`, `limit`) |
| POST | `/api/v1/risks/recompute` | ops_manager / analyst / admin | Recompute risk + regenerate alerts |

## Scenario Simulator

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/simulations/run` | ops_manager / analyst / executive / admin | Run a scenario |
| GET | `/api/v1/simulations` | any | Recent simulations |
| GET | `/api/v1/simulations/{id}` | any | Simulation detail |

Scenario `simulation_type`: `supplier_shutdown` · `port_closure` · `demand_spike` · `weather_disruption`.

```bash
curl -X POST http://localhost:8000/api/v1/simulations/run \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"simulation_type":"supplier_shutdown","severity":0.8,"duration_days":21}'
```

## Alert Center

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/alerts` | any | List (`status`, `priority`, `alert_type`, pagination) |
| GET | `/api/v1/alerts/stats` | any | Counts by status/priority/type |
| PATCH | `/api/v1/alerts/{id}` | ops_manager / analyst / admin | Acknowledge / resolve |
| POST | `/api/v1/alerts/generate` | ops_manager / analyst / admin | Regenerate alerts from state |

## Analytics

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/analytics/delivery` | Status breakdown, carrier performance, trends |
| GET | `/api/v1/analytics/suppliers` | Regional + top/bottom performers |
| GET | `/api/v1/analytics/inventory` | Health, utilization heatmap, by-category |
| GET | `/api/v1/analytics/forecast` | Demand forecast with confidence band (`horizon_weeks`) |

## AI Advisor

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/ai/status` | Provider (openai/local-engine) |
| GET | `/api/v1/ai/suggestions` | Suggested prompts |
| POST | `/api/v1/ai/chat` | Ask a question; answer grounded in live data |
| GET | `/api/v1/ai/reports` | Your past AI conversations |

## Health

| Method | Path | Description |
| --- | --- | --- |
| GET | `/` | Service metadata |
| GET | `/health` | Liveness probe |

## Errors

Standard HTTP semantics with a JSON body: `{ "detail": "..." }`.
`401` invalid/expired token · `403` insufficient role · `404` not found · `409` conflict · `422` validation error.
