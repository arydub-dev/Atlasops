from sqlalchemy import select
from app.core.config import settings
from app.models.models import SalesLead

PAYLOAD = dict(name='Pilot User', email='pilot@example.com', company='Example', role='Planner', company_size='20', problem='Inventory shortages across warehouses', consent=True)


def test_capture_disabled(client):
    assert client.post('/api/v1/leads', json=PAYLOAD).status_code == 503


def test_capture_encrypted_and_operator_only(client, owner_client, db, monkeypatch, owner_user):
    monkeypatch.setattr(settings, 'LEAD_CAPTURE_ENABLED', True)
    assert client.post('/api/v1/leads', json=PAYLOAD).status_code == 202
    row = db.scalar(select(SalesLead))
    assert b'pilot@example.com' not in row.details_encrypted
    assert owner_client.get('/api/v1/admin/leads').status_code == 403
    owner_user.is_platform_admin = True; db.commit()
    response = owner_client.get('/api/v1/admin/leads')
    assert response.status_code == 200
    assert response.json()[0]['email'] == PAYLOAD['email']
    assert owner_client.delete('/api/v1/admin/leads/' + str(row.id)).status_code == 204
    assert owner_client.get('/api/v1/admin/leads').json() == []


def test_honeypot_and_consent(client, db, monkeypatch):
    monkeypatch.setattr(settings, 'LEAD_CAPTURE_ENABLED', True)
    assert client.post('/api/v1/leads', json={**PAYLOAD, 'website':'bot.example'}).status_code == 202
    assert db.scalar(select(SalesLead)) is None
    assert client.post('/api/v1/leads', json={**PAYLOAD, 'consent':False}).status_code == 400
    assert client.get('/api/v1/admin/leads').status_code == 401


def test_personal_email_cannot_submit_enterprise_request(client, db, monkeypatch):
    monkeypatch.setattr(settings, 'LEAD_CAPTURE_ENABLED', True)
    response = client.post('/api/v1/leads', json={**PAYLOAD, 'email': 'person@gmail.com'})
    assert response.status_code == 400
    assert db.scalar(select(SalesLead)) is None
