import http from "k6/http";
import { check, sleep } from "k6";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";
const SESSION = __ENV.SUPPLY_SESSION || "";
const ORG_ID = __ENV.ORG_ID || "";

export const options = {
  vus: Number(__ENV.K6_VUS || 10),
  duration: __ENV.K6_DURATION || "2m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:auth_me}": ["p(95)<300"],
    "http_req_duration{name:shipments}": ["p(95)<500"],
    "http_req_duration{name:mission}": ["p(95)<800"],
  },
};

function headers() {
  return {
    Accept: "application/json",
    Cookie: `supply_session=${SESSION}`,
    "X-Organization-Id": ORG_ID,
  };
}

export function setup() {
  if (!SESSION || !ORG_ID) {
    throw new Error("SUPPLY_SESSION and ORG_ID are required");
  }
}

export default function () {
  const h = headers();

  const me = http.get(`${API_BASE}/api/v1/auth/me`, {
    headers: h,
    tags: { name: "auth_me" },
  });
  check(me, { "auth/me 200": (r) => r.status === 200 });

  const shipments = http.get(`${API_BASE}/api/v1/shipments?limit=25`, {
    headers: h,
    tags: { name: "shipments" },
  });
  check(shipments, { "shipments 200": (r) => r.status === 200 });

  const mission = http.get(`${API_BASE}/api/v1/mission-control`, {
    headers: h,
    tags: { name: "mission" },
  });
  check(mission, { "mission-control 200": (r) => r.status === 200 });

  sleep(1);
}
