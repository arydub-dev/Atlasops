#!/usr/bin/env bash
# ATLASOPS — single combined launcher (backend + frontend).
# Usage:  ./start.sh        then open http://127.0.0.1:3000
#
# Local defaults: SQLite + inline connector sync (Redis optional).
# Production: use Docker Compose / Render with Postgres + Redis + worker.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:3000"
DB_URL="sqlite:///./dev.db"
PY="$ROOT/backend/.venv/bin/python"

free_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "  freeing port $port (pids: $pids)"
    # shellcheck disable=SC2086
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

if [ ! -x "$PY" ]; then
  echo "ERROR: backend/.venv not found. Create it with:"
  echo "  cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Prefer python -m uvicorn so relocated checkouts work (venv script shebangs may
# still point at an old absolute path).
echo "  ensuring schema (Alembic)…"
DATABASE_URL="$DB_URL" "$PY" -m app.cli ensure-schema

echo "  ensuring sandbox seed…"
if [ ! -f "$ROOT/.local/private-demo-env.json" ]; then
  DATABASE_URL="$DB_URL" "$PY" -m app.cli seed-sandbox \
    --email "demo@example.com" --org "Demo Manufacturing Co" || true
fi

BACKEND_COMMAND=("$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000)
if [ -f "$ROOT/.local/private-demo-env.json" ]; then
  BACKEND_COMMAND=("$PY" "$ROOT/.local/run_private_demo.py")
fi

DATABASE_URL="$DB_URL" \
  ENVIRONMENT=development \
  CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000" \
  FRONTEND_URL="http://127.0.0.1:3000" \
  SEED_ON_STARTUP=false \
  CONNECTOR_SYNC_INLINE=true \
  ALLOW_CREATE_ALL_ON_STARTUP=false \
  nohup "${BACKEND_COMMAND[@]}" \
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
  NEXT_PUBLIC_DEV_LOGIN=true \
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
    echo "  Backend  : $BACKEND_URL  (docs: $BACKEND_URL/docs)"
    echo "  Frontend : $FRONTEND_URL"
    echo
    echo "  Open $FRONTEND_URL/login"
    if [ -f "$ROOT/.local/private-demo-env.json" ]; then
      echo "  Private demo: $FRONTEND_URL/demo-login"
      echo "  Credentials: .local/DEMO_ACCESS.txt (keep private)"
    else
      echo "  Sign in using the configured identity provider."
    fi
    echo "  Connector sync runs inline (Redis optional). For workers:"
    echo "    docker compose up redis worker -d"
    echo
    echo "  Logs:  .run/backend.log  .run/frontend.log"
    echo "  Stop:  ./stop.sh"
    exit 0
  fi
  sleep 1
done

echo "  Timed out waiting. Check .run/backend.log and .run/frontend.log"
exit 1
