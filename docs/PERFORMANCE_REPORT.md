> Updated local synthetic measurements: [September 30 validation](reports/2026-09-30-pilot-validation.md). Staging concurrent load remains NOT VERIFIED.

# Performance report

Date: 2026-09-22. Hosted performance: NOT TESTED. Local functional suite duration is not a latency benchmark.

Proposed pilot targets (not measured guarantees): p95 ordinary reads <1s, error rate <1%, dashboard useful content <3s on the agreed network, bounded 10,000-row imports with no API memory exhaustion. AI and exports require separate latency budgets.

Test 10, 50 and 100 concurrent users with a documented realistic tenant dataset. Use `scripts/benchmark_api.py` and `load/k6` against isolated staging with synthetic data and scoped test credentials. Record CPU/memory, DB connections, query latency, request p50/p95/p99, error rates and queue lag. Exercise imports and workers concurrently; simulate provider timeouts and worker restarts.

Run at least seven days of representative soak. Inspect leaks, retry storms, abandoned jobs and backup effects. Optimize only measured bottlenecks; do not claim 10,000-user scale from unit tests. Actual hosted measurements and acceptance sign-off are pending infrastructure.
