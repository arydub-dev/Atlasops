"""Vercel serverless entrypoint for the ATLASOPS FastAPI backend.

Vercel's Python runtime imports this module and serves the ASGI ``app``.
The backend code uses absolute imports rooted at the ``app`` package, so we
ensure this directory is importable before re-exporting the application.

Locally and on container platforms (Render, Docker) the app is still served
via ``app.main:app`` — this file only exists to give Vercel a top-level
entrypoint inside ``backend/``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app  # noqa: E402  (path setup must run first)

__all__ = ["app"]
