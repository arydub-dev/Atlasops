#!/usr/bin/env bash
# SupplyChain Command Center — single combined launcher (backend + frontend).
# Usage:  ./start.sh        then open http://127.0.0.1:3000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:3000"
DB_URL="sqlite:///./dev.db"

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "  freeing port $port (pids: $pids)"
    kill -9 $pids 2>/dev/null || true
    sleep 1
  fi
}

echo "==> Stopping anything on ports 3000 / 8000"
free_port 8000
free_port 3000

# ---------------------------------------------------------------- backend ----
echo "==> Starting backend"
cd "$ROOT/backend"

if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "ERROR: backend/.venv not found. Create it with:"
  echo "  cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Seed a local SQLite DB on first run.
if [ ! -f "dev.db" ]; then
  echo "  seeding demo dataset (first run)…"
  DATABASE_URL="$DB_URL" .venv/bin/python -m app.cli init-db
  DATABASE_URL="$DB_URL" .venv/bin/python -m app.cli seed --scale demo --if-empty
fi

DATABASE_URL="$DB_URL" CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000" \
  nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  > "$RUN_DIR/backend.log" 2>&1 &
echo $! > "$RUN_DIR/backend.pid"

# --------------------------------------------------------------- frontend ----
echo "==> Starting frontend"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "  installing frontend dependencies (first run)…"
  npm install
fi

NEXT_PUBLIC_API_URL="$BACKEND_URL" \
  nohup npm run dev -- -H 0.0.0.0 -p 3000 \
  > "$RUN_DIR/frontend.log" 2>&1 &
echo $! > "$RUN_DIR/frontend.pid"

# ------------------------------------------------------------- wait + report -
echo "==> Waiting for services to come up…"
for i in $(seq 1 60); do
  b=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" 2>/dev/null || echo 000)
  f=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/login" 2>/dev/null || echo 000)
  if [ "$b" = "200" ] && [ "$f" = "200" ]; then
    echo
    echo "  ✅ Backend  : $BACKEND_URL  (docs: $BACKEND_URL/docs)"
    echo "  ✅ Frontend : $FRONTEND_URL"
    echo
    echo "  Open $FRONTEND_URL and sign in:"
    echo "    ops@scc.io / ops12345   (Operations Manager)"
    echo
    echo "  Logs:  .run/backend.log  .run/frontend.log"
    echo "  Stop:  ./stop.sh"
    exit 0
  fi
  sleep 1
done

echo "  ⚠ Timed out waiting. Check .run/backend.log and .run/frontend.log"
exit 1
