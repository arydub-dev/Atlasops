# k6 load tests for Supply v2 staging

## Prerequisites

```bash
# macOS
brew install k6

export API_BASE=https://staging-api.example.com
export SUPPLY_SESSION='paste-supply_session-cookie-value'
export ORG_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

Obtain the session cookie by logging into staging in a browser and copying
`supply_session` from DevTools → Application → Cookies.

## Scripts

| File | Purpose |
| --- | --- |
| `health.js` | `/health/ready` smoke |
| `authenticated_api.js` | `/auth/me`, shipments list, mission-control |
| `csv_import.js` | Light import preview load (gated) |

## Run

```bash
k6 run load/k6/health.js
k6 run load/k6/authenticated_api.js
K6_VUS=2 K6_ITERATIONS=5 k6 run load/k6/csv_import.js
```

Pass/fail thresholds are embedded in each script and documented in
`docs/OPERATIONS_MANUAL.md` Part 6.

Do **not** point these at production without an approved change window.
