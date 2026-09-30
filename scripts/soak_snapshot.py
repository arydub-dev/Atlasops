#!/usr/bin/env python3
"""Capture a soak snapshot from /metrics + /health/ready.

Usage:
  METRICS_TOKEN=... python scripts/soak_snapshot.py --base-url https://staging-api.example.com

Appends one JSON line to docs/reports/soak_samples.jsonl for 7–14 day soak evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def fetch(url: str, headers: dict[str, str]) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def parse_prom(body: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                out[parts[0]] = float(parts[-1])
            except ValueError:
                continue
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--out",
        default=str(
            Path(__file__).resolve().parents[1]
            / "docs"
            / "reports"
            / "soak_samples.jsonl"
        ),
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    token = os.environ.get("METRICS_TOKEN", "")
    headers = {"Accept": "text/plain"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ready_status, ready_body = fetch(f"{base}/health/ready", {"Accept": "application/json"})
    metrics_status, metrics_body = fetch(f"{base}/metrics", headers)
    prom = parse_prom(metrics_body) if metrics_status == 200 else {}

    sample = {
        "ts": int(time.time()),
        "base_url": base,
        "ready_status": ready_status,
        "ready_body": ready_body[:500],
        "metrics_status": metrics_status,
        "http_requests_total_sum": sum(
            v for k, v in prom.items() if k.startswith("http_requests_total")
        ),
        "connector_sync_samples": {
            k: v for k, v in prom.items() if k.startswith("connector_")
        },
        "stripe_webhook_samples": {
            k: v for k, v in prom.items() if k.startswith("stripe_webhook")
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(sample) + "\n")
    print(json.dumps(sample, indent=2))


if __name__ == "__main__":
    main()
