"""API integration tests covering auth, RBAC, and each module."""


def test_login_and_me(client, ops_headers):
    r = client.get("/api/v1/auth/me", headers=ops_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "operations_manager"


def test_login_rejects_bad_password(client):
    r = client.post("/api/v1/auth/login", data={"username": "ops@scc.io", "password": "wrong"})
    assert r.status_code == 401


def test_protected_requires_token(client):
    assert client.get("/api/v1/dashboard").status_code == 401


def test_dashboard(client, ops_headers):
    body = client.get("/api/v1/dashboard", headers=ops_headers).json()
    assert "kpis" in body
    assert body["kpis"]["total_shipments"] > 0
    assert isinstance(body["shipment_trend"], list)


def test_shipment_filters_and_detail(client, ops_headers):
    page = client.get("/api/v1/shipments?status=delivered&page=1&page_size=5", headers=ops_headers).json()
    assert page["page"] == 1
    for item in page["items"]:
        assert item["status"] == "delivered"
    if page["items"]:
        sid = page["items"][0]["id"]
        detail = client.get(f"/api/v1/shipments/{sid}", headers=ops_headers).json()
        assert detail["id"] == sid


def test_inventory_and_reorders(client, ops_headers):
    items = client.get("/api/v1/inventory/items?page=1&page_size=10", headers=ops_headers).json()
    assert items["total"] >= 0
    health = client.get("/api/v1/inventory/health", headers=ops_headers).json()
    assert set(health) == {"ok", "low_stock", "overstock", "stockout"}


def test_supplier_scorecard(client, ops_headers):
    ranking = client.get("/api/v1/suppliers/ranking?limit=5", headers=ops_headers).json()
    assert ranking
    assert ranking[0]["rank"] == 1


def test_risk_summary(client, ops_headers):
    summary = client.get("/api/v1/risks/summary", headers=ops_headers).json()
    assert 0 <= summary["overall_score"] <= 100
    assert "by_category" in summary


def test_simulation_run(client, ops_headers):
    r = client.post(
        "/api/v1/simulations/run",
        headers=ops_headers,
        json={"simulation_type": "demand_spike", "demand_multiplier": 2.0, "duration_days": 14},
    )
    assert r.status_code == 200
    assert "impacts" in r.json()["results"]


def test_ai_chat(client, ops_headers):
    r = client.post("/api/v1/ai/chat", headers=ops_headers, json={"prompt": "Summarize status"})
    assert r.status_code == 200
    assert len(r.json()["response"]) > 0


def test_rbac_analyst_cannot_update_shipment(client, ops_headers, analyst_headers):
    sid = client.get("/api/v1/shipments?page=1&page_size=1", headers=ops_headers).json()["items"][0]["id"]
    blocked = client.patch(
        f"/api/v1/shipments/{sid}/status", headers=analyst_headers, json={"status": "delivered"}
    )
    assert blocked.status_code == 403


def test_alerts_lifecycle(client, ops_headers):
    page = client.get("/api/v1/alerts?page=1&page_size=1", headers=ops_headers).json()
    if page["items"]:
        aid = page["items"][0]["id"]
        upd = client.patch(
            f"/api/v1/alerts/{aid}",
            headers=ops_headers,
            json={"status": "resolved", "resolution_note": "handled"},
        )
        assert upd.status_code == 200
        assert upd.json()["status"] == "resolved"
