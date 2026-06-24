"""Quick end-to-end smoke test against an in-file SQLite DB (not part of the app)."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./smoke.db"
os.environ["SEED_ON_STARTUP"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.cli import init_db  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import synthetic  # noqa: E402

init_db()
db = SessionLocal()
if not synthetic.is_seeded(db):
    synthetic.seed_all(
        db,
        n_suppliers=8,
        n_products=12,
        n_warehouses=4,
        n_shipments=120,
        inventory_history_snapshots=2,
        verbose=False,
    )
db.close()

client = TestClient(app)

# auth
r = client.post("/api/v1/auth/login", data={"username": "ops@scc.io", "password": "ops12345"})
assert r.status_code == 200, r.text
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

checks = [
    ("GET", "/api/v1/auth/me", None),
    ("GET", "/api/v1/dashboard", None),
    ("GET", "/api/v1/shipments?page=1&page_size=5", None),
    ("GET", "/api/v1/inventory/items?page=1&page_size=5", None),
    ("GET", "/api/v1/inventory/health", None),
    ("GET", "/api/v1/suppliers/ranking?limit=5", None),
    ("GET", "/api/v1/risks/summary", None),
    ("GET", "/api/v1/alerts?page=1&page_size=5", None),
    ("GET", "/api/v1/alerts/stats", None),
    ("GET", "/api/v1/analytics/delivery", None),
    ("GET", "/api/v1/analytics/inventory", None),
    ("GET", "/api/v1/analytics/forecast", None),
    ("GET", "/api/v1/ai/status", None),
]
for method, url, body in checks:
    resp = client.request(method, url, headers=h, json=body)
    assert resp.status_code == 200, f"{url} -> {resp.status_code}: {resp.text[:300]}"
    print(f"OK {url}")

# simulation
sim = client.post(
    "/api/v1/simulations/run",
    headers=h,
    json={"simulation_type": "supplier_shutdown", "severity": 0.8, "duration_days": 21},
)
assert sim.status_code == 200, sim.text
print("OK simulation:", sim.json()["results"]["scenario"])

# AI chat
ai = client.post("/api/v1/ai/chat", headers=h, json={"prompt": "Why are delays increasing this week?"})
assert ai.status_code == 200, ai.text
print("OK ai chat (model:", ai.json()["model"] + ")")

# shipment detail + status update
ship_id = client.get("/api/v1/shipments?page=1&page_size=1", headers=h).json()["items"][0]["id"]
det = client.get(f"/api/v1/shipments/{ship_id}", headers=h)
assert det.status_code == 200, det.text
upd = client.patch(
    f"/api/v1/shipments/{ship_id}/status",
    headers=h,
    json={"status": "at_warehouse", "current_location": "Test DC", "note": "smoke"},
)
assert upd.status_code == 200, upd.text
print("OK shipment status update")

# RBAC: analyst should NOT be able to update shipment status
r2 = client.post("/api/v1/auth/login", data={"username": "analyst@scc.io", "password": "analyst123"})
ha = {"Authorization": f"Bearer {r2.json()['access_token']}"}
forbidden = client.patch(
    f"/api/v1/shipments/{ship_id}/status", headers=ha, json={"status": "delivered"}
)
assert forbidden.status_code == 403, f"expected 403, got {forbidden.status_code}"
print("OK RBAC enforcement (analyst blocked from status update)")

print("\nALL SMOKE TESTS PASSED")
