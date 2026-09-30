#!/usr/bin/env python3
"""Lightweight API latency benchmark (avg / p95 / p99).

Usage (API must be running, session cookie optional for public health):

  python scripts/benchmark_api.py --base-url http://127.0.0.1:8000

Authenticated routes require SUPPLY_SESSION cookie + X-Organization-Id:

  SUPPLY_SESSION=... ORG_ID=... python scripts/benchmark_api.py --auth

Writes docs/reports/RC2_BENCHMARK.md when --write-report is set.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def timed_get(url: str, headers: dict[str, str], timeout: float = 30.0) -> tuple[int, float]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return status, elapsed_ms


def run_case(name: str, url: str, headers: dict[str, str], iterations: int) -> dict:
    samples: list[float] = []
    statuses: list[int] = []
    for _ in range(iterations):
        status, ms = timed_get(url, headers)
        samples.append(ms)
        statuses.append(status)
    samples.sort()
    return {
        "name": name,
        "url": url,
        "iterations": iterations,
        "avg_ms": round(statistics.fmean(samples), 2),
        "p50_ms": round(percentile(samples, 50), 2),
        "p95_ms": round(percentile(samples, 95), 2),
        "p99_ms": round(percentile(samples, 99), 2),
        "ok_rate": round(sum(1 for s in statuses if 200 <= s < 400) / len(statuses), 3),
        "statuses": sorted(set(statuses)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--auth", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    headers = {"Accept": "application/json"}
    cases = [
        ("health_live", f"{args.base_url.rstrip('/')}/health/live"),
        ("health_ready", f"{args.base_url.rstrip('/')}/health/ready"),
    ]

    if args.auth:
        session = os.environ.get("SUPPLY_SESSION", "")
        org_id = os.environ.get("ORG_ID", "")
        if not session or not org_id:
            raise SystemExit("SUPPLY_SESSION and ORG_ID required with --auth")
        headers["Cookie"] = f"supply_session={session}"
        headers["X-Organization-Id"] = org_id
        api = f"{args.base_url.rstrip('/')}/api/v1"
        cases.extend(
            [
                ("auth_me", f"{api}/auth/me"),
                ("shipments_list", f"{api}/shipments?limit=25"),
                ("mission_control", f"{api}/mission-control"),
            ]
        )

    results = [run_case(name, url, headers, args.iterations) for name, url in cases]
    print(json.dumps(results, indent=2))

    if args.write_report:
        out = Path(__file__).resolve().parents[1] / "docs" / "reports" / "RC2_BENCHMARK.md"
        lines = [
            "# RC2 API benchmark",
            "",
            f"Base URL: `{args.base_url}` · iterations/case: **{args.iterations}**",
            "",
            "| Case | Avg ms | P50 | P95 | P99 | OK rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in results:
            lines.append(
                f"| {r['name']} | {r['avg_ms']} | {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['ok_rate']} |"
            )
        lines.extend(
            [
                "",
                "Optimizations should only follow measurements that exceed SLO targets.",
                "Default advisory SLO (design partners): health P95 < 100ms; authenticated list P95 < 500ms.",
                "",
            ]
        )
        out.write_text("\n".join(lines))
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
