"""Observability: structured JSON logs, optional OpenTelemetry, Prometheus, request IDs."""
from __future__ import annotations

import logging
import sys
import time
import re
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# --------------------------------------------------------------------------- #
# Structured JSON logging
# --------------------------------------------------------------------------- #
try:
    from pythonjsonlogger.json import JsonFormatter  # type: ignore
except ImportError:  # pragma: no cover — fallback without extra dep
    JsonFormatter = None  # type: ignore


class _FallbackJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import json

        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("request_id", "organization_id", "path", "method", "status_code"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(level: str | int = logging.INFO) -> None:
    """Configure root + uvicorn loggers for structured JSON output."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if JsonFormatter is not None:
        handler.setFormatter(
            JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
            )
        )
    else:
        handler.setFormatter(_FallbackJsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.propagate = True


# --------------------------------------------------------------------------- #
# OpenTelemetry (optional)
# --------------------------------------------------------------------------- #
def setup_opentelemetry(app: FastAPI) -> bool:
    """Instrument FastAPI with OTel if packages are installed. Returns True if enabled.

    Exporter is only attached when ``OTEL_EXPORTER_OTLP_ENDPOINT`` (or
    ``OTEL_ENABLE=true``) is set, so local/test runs stay quiet.
    """
    import os

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError:
        logging.getLogger(__name__).info("OpenTelemetry packages not installed; skipping OTel setup")
        return False

    resource = Resource.create(
        {
            "service.name": settings.APP_NAME.lower(),
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("OTEL_ENABLE")
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("OTLP exporter unavailable: %s", exc)

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    return True


# --------------------------------------------------------------------------- #
# Prometheus metrics
# --------------------------------------------------------------------------- #
_PROM_AVAILABLE = False
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )
    CONNECTOR_SYNC_TOTAL = Counter(
        "connector_sync_total",
        "Connector sync jobs completed",
        ["connector_type", "status"],
    )
    CONNECTOR_SYNC_DURATION = Histogram(
        "connector_sync_duration_seconds",
        "Connector sync duration",
        ["connector_type"],
    )
    CONNECTOR_ENQUEUE_TOTAL = Counter(
        "connector_enqueue_total",
        "Connector sync enqueue attempts",
        ["result"],
    )
    AI_PROVIDER_TOTAL = Counter(
        "ai_provider_requests_total", "AI provider outcomes", ["provider", "result"]
    )
    STRIPE_WEBHOOK_TOTAL = Counter(
        "stripe_webhook_total",
        "Stripe webhook events processed",
        ["result"],
    )
    _PROM_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUEST_COUNT = None  # type: ignore
    REQUEST_LATENCY = None  # type: ignore
    CONNECTOR_SYNC_TOTAL = None  # type: ignore
    CONNECTOR_SYNC_DURATION = None  # type: ignore
    CONNECTOR_ENQUEUE_TOTAL = None  # type: ignore
    STRIPE_WEBHOOK_TOTAL = None  # type: ignore
    AI_PROVIDER_TOTAL = None  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain"
    generate_latest = None  # type: ignore


def metrics_endpoint() -> tuple[bytes, str]:
    """Return (body, content_type) for a Prometheus scrape endpoint."""
    if not _PROM_AVAILABLE or generate_latest is None:
        return b"# prometheus-client not installed\n", "text/plain; charset=utf-8"
    return generate_latest(), CONTENT_TYPE_LATEST


def mount_metrics(app: FastAPI, path: str = "/metrics") -> None:
    @app.get(path, include_in_schema=False)
    def _metrics():
        body, content_type = metrics_endpoint()
        return Response(content=body, media_type=content_type)


# --------------------------------------------------------------------------- #
# Request ID middleware
# --------------------------------------------------------------------------- #
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        supplied_id = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
        finally:
            elapsed = time.perf_counter() - start
            if _PROM_AVAILABLE and REQUEST_COUNT is not None and REQUEST_LATENCY is not None:
                route = request.scope.get("route")
                label_path = getattr(route, "path", "unmatched") if route else "unmatched"
                REQUEST_COUNT.labels(request.method, label_path, str(status_code)).inc()
                REQUEST_LATENCY.labels(request.method, label_path).observe(elapsed)

        return response


def install_request_id_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
