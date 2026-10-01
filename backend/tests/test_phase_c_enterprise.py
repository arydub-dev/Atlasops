"""Phase C enterprise operations tests."""
from __future__ import annotations

from app.models import Connection
from app.models.enums import ConnectorStatus, ConnectorType, WorkflowTrigger
from app.services import connector_studio, data_quality, predictions, workflows


def test_data_quality_assess(db, org_a):
    org, _ = org_a
    result = data_quality.assess(db, org.id, persist=True)
    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 100
    assert result.get("snapshot_id")


def test_workflow_create_and_execute(db, org_a, owner_user):
    org, membership = org_a
    rule = workflows.create_rule(
        db,
        org.id,
        name="High risk incident",
        trigger=WorkflowTrigger.MANUAL,
        conditions=[{"field": "risk_score", "op": "gt", "value": 50}],
        actions=[{"type": "escalate", "level": "leadership"}],
        created_by_user_id=owner_user.id,
    )
    run = workflows.execute_rule(
        db, org.id, rule.id, payload={"risk_score": 90, "title": "Test"}
    )
    assert run is not None
    assert run.status.value in {"succeeded", "skipped", "failed"}


def test_predictions_generate(db, org_a):
    org, _ = org_a
    items = predictions.generate(db, org.id)
    assert isinstance(items, list)


def test_connector_studio_catalogue(owner_client):
    r = owner_client.get("/api/v1/connector-studio/catalogue")
    assert r.status_code == 200
    assert "items" in r.json()
    assert len(r.json()["items"]) >= 1


def test_connector_studio_detail(db, org_a, owner_client):
    org, _ = org_a
    conn = Connection(
        organization_id=org.id,
        name="Studio Conn",
        connector_type=ConnectorType.CSV_UPLOAD,
        status=ConnectorStatus.NOT_CONFIGURED,
        config={"field_mappings": [{"source": "a", "destination": "b"}]},
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    r = owner_client.get(f"/api/v1/connector-studio/connections/{conn.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Studio Conn"
    assert body["field_mappings"]


def test_workflows_api(owner_client):
    created = owner_client.post(
        "/api/v1/workflows",
        json={
            "name": "Notify on sync",
            "trigger": "manual",
            "conditions": [],
            "actions": [{"type": "escalate", "level": "ops"}],
        },
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    executed = owner_client.post(f"/api/v1/workflows/{rid}/execute", json={"payload": {}})
    assert executed.status_code == 200, executed.text


def test_data_quality_api(owner_client):
    r = owner_client.get("/api/v1/data-quality?refresh=true")
    assert r.status_code == 200, r.text
    assert "overall_score" in r.json()


def test_dashboards_api(owner_client):
    roles = owner_client.get("/api/v1/dashboards/roles")
    assert roles.status_code == 200
    assert len(roles.json()["roles"]) >= 5
    dash = owner_client.get("/api/v1/dashboards/ceo")
    assert dash.status_code == 200, dash.text
    assert "widgets" in dash.json()


def test_predictions_api(owner_client):
    gen = owner_client.post("/api/v1/predictions/generate")
    assert gen.status_code == 200, gen.text
    listed = owner_client.get("/api/v1/predictions")
    assert listed.status_code == 200


def test_customer_success_api(owner_client):
    r = owner_client.get("/api/v1/customer-success/onboarding")
    assert r.status_code == 200
    assert "steps" in r.json()


def test_security_center_api(owner_client):
    r = owner_client.get("/api/v1/security-center")
    assert r.status_code == 200, r.text
    assert "recommendations" in r.json()


def test_platform_ops_api(owner_client):
    r = owner_client.get("/api/v1/platform-ops")
    assert r.status_code == 200
    assert "workers" in r.json()


def test_mission_control_data_health(owner_client):
    r = owner_client.get("/api/v1/mission-control")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data_health" in body
    assert "predictions" in body


def test_documents_upload(owner_client, org_a):
    org, _ = org_a
    import base64
    from uuid import uuid4

    content = base64.b64encode(b"hello atlasops").decode()
    r = owner_client.post(
        "/api/v1/documents",
        json={
            "entity_type": "organization",
            "entity_id": str(org.id),
            "filename": "note.txt",
            "content_base64": content,
            "content_type": "text/plain",
        },
    )
    assert r.status_code == 201, r.text
    listed = owner_client.get(f"/api/v1/documents?entity_type=organization&entity_id={org.id}")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) >= 1
