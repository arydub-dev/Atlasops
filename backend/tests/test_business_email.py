import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock
from app.core.business_email import require_business_email
from app.api.routers.auth import _upsert_workos_user

@pytest.mark.parametrize("email", ["user@gmail.com", "user@GMAIL.COM", "user@outlook.com", "user@sub.mailinator.com", "user@proton.me"])
def test_personal_domains_rejected(email):
    with pytest.raises(HTTPException) as exc:
        require_business_email(email)
    assert exc.value.status_code == 400

@pytest.mark.parametrize("email", ["user@acme.com", "user@logistics.co.uk", "user@gmail.com.acme.com"])
def test_company_domains_accepted(email):
    require_business_email(email)

def test_callback_cannot_create_personal_account():
    db = MagicMock()
    db.scalar.return_value = None
    with pytest.raises(HTTPException):
        _upsert_workos_user(db, {"email": "new@gmail.com", "workos_user_id": "test", "email_verified": True})
    db.add.assert_not_called()
