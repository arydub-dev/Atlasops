"""Public inquiry intake; reading/deletion is restricted to platform operators."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_platform_admin
from app.core.config import settings
from app.core.business_email import require_business_email
from app.core.database import get_db
from app.core.rate_limit import rate_limit_auth
from app.connectors.credentials import encrypt_credentials, decrypt_credentials
from app.models.models import SalesLead

router = APIRouter(tags=['Sales inquiries'])


class Inquiry(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    company: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=100)
    company_size: str = Field(min_length=1, max_length=50)
    problem: str = Field(min_length=10, max_length=2000)
    phone: str = Field(default='', max_length=40)
    website: str = Field(default='', max_length=200)  # honeypot
    consent: bool


@router.post('/leads', status_code=202, dependencies=[Depends(rate_limit_auth)])
def create_inquiry(body: Inquiry, db: Session = Depends(get_db)):
    if not settings.LEAD_CAPTURE_ENABLED:
        raise HTTPException(503, 'Enterprise inquiries are not open yet. Please try again later.')
    if body.website:
        return {'accepted': True}
    require_business_email(str(body.email))
    if not body.consent:
        raise HTTPException(400, 'Please agree to be contacted about your request')
    details = body.model_dump(exclude={'website', 'consent'})
    db.add(SalesLead(details_encrypted=encrypt_credentials(details)))
    db.commit()
    return {'accepted': True}


@router.get('/admin/leads', dependencies=[Depends(require_platform_admin)])
def list_inquiries(db: Session = Depends(get_db)):
    rows = db.scalars(select(SalesLead).order_by(SalesLead.created_at.desc()).limit(100)).all()
    return [{'id': str(r.id), 'created_at': r.created_at.isoformat(), **decrypt_credentials(r.details_encrypted)} for r in rows]


@router.delete('/admin/leads/{lead_id}', status_code=204, dependencies=[Depends(require_platform_admin)])
def delete_inquiry(lead_id: UUID, db: Session = Depends(get_db)):
    row = db.get(SalesLead, lead_id)
    if row is None:
        raise HTTPException(404, 'Inquiry not found')
    db.delete(row)
    db.commit()
