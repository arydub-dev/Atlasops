"""Object storage via S3-compatible APIs (AWS S3 or Cloudflare R2)."""
from __future__ import annotations

import logging
from typing import BinaryIO

from app.core.config import settings

logger = logging.getLogger("supply.storage")


def storage_configured() -> bool:
    return bool(
        settings.S3_BUCKET
        and settings.S3_ACCESS_KEY_ID
        and settings.S3_SECRET_ACCESS_KEY
    )


def upload_bytes(*, key: str, data: bytes, content_type: str = "application/octet-stream") -> str | None:
    """Upload bytes; returns object key or None if storage unset / failure."""
    if not storage_configured():
        logger.info("storage_skipped reason=unset key=%s", key)
        return None
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION or "auto",
        )
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key
    except Exception:  # noqa: BLE001
        logger.exception("storage_upload_failed key=%s", key)
        return None


def upload_fileobj(*, key: str, fileobj: BinaryIO, content_type: str = "application/octet-stream") -> str | None:
    return upload_bytes(key=key, data=fileobj.read(), content_type=content_type)
