import http from "k6/http";
import { check, sleep } from "k6";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  vus: Number(__ENV.K6_VUS || 5),
  duration: __ENV.K6_DURATION || "1m",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<100"],
  },
};

export default function () {
  const res = http.get(`${API_BASE}/health/ready`);
  check(res, {
    "ready status 200": (r) => r.status === 200,
    "ready body ok": (r) => String(r.body).includes("ready"),
  });
  sleep(0.5);
}
