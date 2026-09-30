# Integrations (Supply v2)

How tenant data enters Supply. There is **no** Demo/Connected mode toggle that mixes
seeded ERP simulation with live connectors. CSV import and the Connector SDK are the
supported paths.

---

## 1. CSV / Excel import

Flow: upload → parse → validate → preview → commit.

| Step | Endpoint |
| --- | --- |
| Preview | `POST /api/v1/data/import/preview` |
| Commit | `POST /api/v1/data/import/commit` |
| History | `GET /api/v1/data/imports` |

Entities: suppliers, warehouses, products, shipments, inventory (see
`app.services.ingestion.ENTITY_SPECS`). Commit creates domain rows, an `ImportJob`, and an
audit log entry (`action=import`).

---

## 2. Connector SDK

Location: `backend/app/connectors/`.

| Connector | Auth | Purpose |
| --- | --- | --- |
| Dynamics 365 Business Central | OAuth2 (Microsoft) | ERP entities |
| Salesforce | OAuth2 / refresh | CRM / operational objects |
| UPS | OAuth2 client credentials | Carrier tracking |

All connectors implement the shared base (connect, test, sync, health). Credentials are
encrypted (`CREDENTIALS_ENCRYPTION_KEY`). API responses never return secrets in
plaintext.

**SSRF:** outbound URLs must be HTTPS and match the per-connector host allowlist
(`app.connectors.ssrf`). Arbitrary `base_url` / `token_url` / `api_base` values are rejected.

**Sync:** `POST /data/sources/{id}/sync` enqueues an ARQ job (`status: queued`). Long-running
work runs in the worker — never inline in staging/production (`CONNECTOR_SYNC_INLINE=false`).

**Requirements for production use of connectors**

- Redis + ARQ worker running
- Staging validation against vendor sandboxes
- Allowlisted hosts only (see `ssrf.py`)

---

## 3. What is not shipped

- SAP ERP / Oracle ERP production connectors
- Simulated “fake sync” that invents ERP data
- Unauthenticated webhook receivers for carriers

---

## 4. Pipeline visibility

Import jobs and connector runs are listed via data/pipeline APIs for operators. Metrics
and structured logs include connector health where instrumented.

See also: `docs/CONNECTOR_SDK.md` (if present), `docs/API.md`, `docs/MIGRATION_V2.md`.
