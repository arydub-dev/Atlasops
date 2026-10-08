import pytest
from app.core.config import settings
from app.core.security import hash_password
from app.models import User, Membership
from app.models.enums import MembershipStatus


@pytest.fixture
def demo(db, org_a, monkeypatch):
    org = org_a[0]
    org.settings = {**(org.settings or {}), 'private_demo':True}
    user = User(email='private-demo@example.com',full_name='Demo visitor',is_active=True)
    db.add(user); db.flush()
    member = Membership(organization_id=org.id,user_id=user.id,role_slug='viewer',status=MembershipStatus.ACTIVE)
    db.add(member); db.commit()
    for key,value in {'DEMO_LOGIN_ID':'private-review','DEMO_LOGIN_PASSWORD_HASH':hash_password('test-only-strong-password'),
                      'DEMO_LOGIN_USER_ID':str(user.id),'DEMO_LOGIN_ORG_ID':str(org.id)}.items():
        monkeypatch.setattr(settings,key,value)
    return user,member


def login(client,password='test-only-strong-password',login_id='private-review'):
    return client.post('/api/v1/auth/demo-login',json={'login_id':login_id,'password':password})


def test_private_demo_session_and_write_denial(client,demo):
    response=login(client)
    assert response.status_code==200, response.text
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert client.get('/api/v1/auth/me').json()['current_membership']['role_slug']=='viewer'
    assert client.get('/api/v1/inventory/items').status_code==200
    assert client.post('/api/v1/incidents',json={'title':'Cannot create','severity':'high'}).status_code==403
    assert client.post('/api/v1/auth/dev-login',json={'email':'demo@example.com'}).status_code==404


def test_wrong_credentials_and_disabled(client,demo,monkeypatch):
    assert login(client,password='incorrect').status_code==401
    assert login(client,login_id='incorrect').status_code==401
    monkeypatch.setattr(settings,'DEMO_LOGIN_PASSWORD_HASH','')
    assert login(client).status_code==404


def test_password_rotation_revokes_existing_session(client,demo,monkeypatch):
    assert login(client).status_code==200
    monkeypatch.setattr(settings,'DEMO_LOGIN_PASSWORD_HASH',hash_password('rotated-test-password'))
    assert client.get('/api/v1/auth/me').status_code==401


def test_role_change_invalidates_demo_session(client,demo,db):
    assert login(client).status_code==200
    demo[1].role_slug='admin'; db.commit()
    assert client.get('/api/v1/auth/me').status_code==401
    assert login(client).status_code==401


def test_another_membership_blocks_login(client,demo,db,org_b):
    db.add(Membership(organization_id=org_b[0].id,user_id=demo[0].id,role_slug='viewer',status=MembershipStatus.ACTIVE))
    db.commit()
    assert login(client).status_code==401
