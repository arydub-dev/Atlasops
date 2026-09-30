/**
 * Light CSV import load — use sparingly on shared staging.
 * Requires SUPPLY_SESSION, ORG_ID, and a small CSV fixture.
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";
const SESSION = __ENV.SUPPLY_SESSION || "";
const ORG_ID = __ENV.ORG_ID || "";

const csvRows = new SharedArray("suppliers", () => {
  return [
    "name,country,region,category\nLoad Test Supplier,USA,West,Components\n",
  ];
});

export const options = {
  vus: Number(__ENV.K6_VUS || 2),
  iterations: Number(__ENV.K6_ITERATIONS || 5),
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<3000"],
  },
};

export function setup() {
  if (!SESSION || !ORG_ID) {
    throw new Error("SUPPLY_SESSION and ORG_ID are required");
  }
}

export default function () {
  const headers = {
    Cookie: `supply_session=${SESSION}`,
    "X-Organization-Id": ORG_ID,
  };
  const fd = {
    entity: "suppliers",
    file: http.file(csvRows[0], "suppliers.csv", "text/csv"),
  };
  const preview = http.post(`${API_BASE}/api/v1/data/import/preview`, fd, {
    headers,
  });
  check(preview, { "preview 200": (r) => r.status === 200 });
  sleep(1);
}
