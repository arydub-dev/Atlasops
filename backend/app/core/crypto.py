"""Field-level encryption for connector credentials and webhook secrets."""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    raw = settings.CREDENTIALS_ENCRYPTION_KEY
    if not raw:
        # Deterministic dev-only key — refuse on any hardened environment.
        if settings.requires_secure_boot:
            raise RuntimeError(
                "CREDENTIALS_ENCRYPTION_KEY is required in staging/production"
            )
        digest = hashlib.sha256(settings.SESSION_SECRET.encode("utf-8")).digest()
        raw = base64.urlsafe_b64encode(digest).decode("ascii")
    if len(raw) == 44 and raw.endswith("="):
        key = raw.encode("ascii")
    else:
        key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_bytes(plaintext: bytes) -> bytes:
    return _fernet().encrypt(plaintext)


def decrypt_bytes(ciphertext: bytes) -> bytes:
    try:
        return _fernet().decrypt(ciphertext)
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt credentials") from exc


def encrypt_str(value: str) -> bytes:
    return encrypt_bytes(value.encode("utf-8"))


def decrypt_str(value: bytes) -> str:
    return decrypt_bytes(value).decode("utf-8")


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_token(prefix: str = "sup", nbytes: int = 32) -> tuple[str, str, str]:
    """Return (full_token, prefix_for_display, hash)."""
    secret = base64.urlsafe_b64encode(os.urandom(nbytes)).decode("ascii").rstrip("=")
    full = f"{prefix}_{secret}"
    display_prefix = full[:12]
    return full, display_prefix, hash_token(full)
