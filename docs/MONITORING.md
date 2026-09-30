# Monitoring & alerting (RC3)

## What exists in the platform

| Signal | Endpoint / metric | Notes |
| --- | --- | --- |
| Liveness | `GET /health/live` | Process up |
| Readiness | `GET /health/ready` | DB + Redis (when queue sync required) |
| HTTP | `http_requests_total`, `http_request_duration_seconds` | Prometheus |
| Connectors | `connector_sync_total`, `connector_sync_duration_seconds`, `connector_enqueue_total` | Prometheus |
| Billing | `stripe_webhook_total{result=}` | Prometheus |
| Request correlation | `X-Request-ID` request/response header | Structured JSON logs |
| Tracing | OpenTelemetry FastAPI instrumentation | Export only if `OTEL_EXPORTER_OTLP_ENDPOINT` set |

**Not shipped in-repo:** Grafana dashboards, Alertmanager, PagerDuty. Operators must scrape `/metrics` with `Authorization: Bearer $METRICS_TOKEN` and wire alerts in their host.

## Soak sampling

```bash
export METRICS_TOKEN=...
# cron every 5 minutes during 7–14 day soak
python scripts/soak_snapshot.py --base-url https://staging-api.example.com
```

Samples append to `docs/reports/soak_samples.jsonl`.

## Recommended Prometheus alert rules

```yaml
groups:
  - name: supply
    rules:
      - alert: SupplyNotReady
        expr: up{job="supply-api"} == 0
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: Supply API scrape/up failed

      - alert: SupplyHigh5xx
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 10m
        labels: { severity: high }
        annotations:
          summary: API 5xx ratio > 5%

      - alert: SupplySyncEnqueueErrors
        expr: increase(connector_enqueue_total{result="error"}[15m]) > 0
        for: 5m
        labels: { severity: high }
        annotations:
          summary: Connector enqueue failing (Redis/worker path)

      - alert: SupplyStripeWebhookErrors
        expr: increase(stripe_webhook_total{result="error"}[15m]) > 0
        for: 5m
        labels: { severity: high }
        annotations:
          summary: Stripe webhook handler errors
```

## Grafana (operator-owned)

Suggested panels: request P95, ready status, connector sync rate, enqueue errors, Stripe webhook results, Postgres connections (from managed DB metrics), Redis memory (managed Redis).

Until these alerts are wired on a live staging/production scrape target, **operational monitoring remains an open gate**.

## Launch audit additions (2026-09-22)

`deploy/alerts.yml` contains proposed Prometheus rules for API availability/error rate/latency, Stripe processing failures and queue enqueue failures. Wire the API scrape to the private `/metrics` endpoint with METRICS_TOKEN. No alert receiver has been configured or tested. Load the rules in staging and induce one controlled failure per rule; record delivery to a staffed responder.

Monitor ARQ health and queue lag separately; API readiness does not prove a worker is consuming jobs. Add host/database disk and backup-age alerts through the chosen hosting service. Persist logs off-host with access restrictions and a defined retention period. Unmatched API paths now share one metric label to prevent arbitrary URL cardinality growth. SQLAlchemy hides bind parameters in database exceptions.
