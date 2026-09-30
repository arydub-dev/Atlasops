"""Upload validation helpers — size, extension, and content-type allowlists."""
from __future__ import annotations

import os

from fastapi import HTTPException, status

# Documents / attachments (non-executable business files only)
ALLOWED_DOCUMENT_EXTENSIONS = frozenset(
    {
        ".csv",
        ".txt",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".xlsx",
        ".xls",
        ".xlsm",
        ".docx",
        ".doc",
        ".json",
    }
)
ALLOWED_DOCUMENT_CONTENT_TYPES = frozenset(
    {
        "text/csv",
        "text/plain",
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/json",
        "application/octet-stream",  # browsers often send this; extension still required
    }
)

ALLOWED_IMPORT_EXTENSIONS = frozenset({".csv", ".xlsx"})


def assert_safe_upload(
    *,
    filename: str,
    content_type: str | None,
    size: int,
    max_bytes: int,
    allowed_extensions: frozenset[str],
    allowed_content_types: frozenset[str] | None = None,
) -> str:
    """Validate upload metadata. Returns sanitized basename.

    Raises HTTPException on violation.
    """
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {max_bytes // (1024 * 1024)}MB limit",
        )
    base = os.path.basename((filename or "file").replace("\\", "/"))
    if not base or base in {".", ".."} or "/" in base or "\\" in base:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = os.path.splitext(base)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext or '(none)'}' is not allowed",
        )
    if allowed_content_types is not None and content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct and ct not in allowed_content_types:
            raise HTTPException(
                status_code=400,
                detail=f"Content type '{ct}' is not allowed",
            )
    return base
