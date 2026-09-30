"""HMAC signing for tenant-scoped ARQ job payloads.

Redis is a trust boundary. Unsigned jobs would let anyone who can reach Redis
enqueue work as an arbitrary organization. Signatures bind job name + tenant
ids using a key derived from CREDENTIALS_ENCRYPTION_KEY (or SESSION_SECRET).
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _signing_key() -> bytes:
    raw = (settings.CREDENTIALS_ENCRYPTION_KEY or settings.SESSION_SECRET or "").strip()
    if not raw:
        raw = "dev-only-job-signing-key-not-for-production"
    return hashlib.sha256(raw.encode("utf-8")).digest()


def sign_tenant_job(job_name: str, *parts: str) -> str:
    """Return hex HMAC-SHA256 over job_name and ordered string parts."""
    payload = "\n".join([job_name, *[str(p) for p in parts]])
    return hmac.new(_signing_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_tenant_job(job_name: str, signature: str | None, *parts: str) -> None:
    """Validate job signature.

    In hardened environments (staging/production) a valid signature is required.
    Development/test may omit signatures for simpler local runs.
    """
    expected = sign_tenant_job(job_name, *parts)
    if not signature:
        if settings.requires_secure_boot:
            raise PermissionError(f"Missing signature for job {job_name}")
        logger.debug("job_signature_skipped_dev job=%s", job_name)
        return
    if not hmac.compare_digest(expected, str(signature)):
        raise PermissionError(f"Invalid signature for job {job_name}")
