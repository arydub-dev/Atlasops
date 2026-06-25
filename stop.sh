#!/usr/bin/env bash
# Stop the ATLASOPS servers started by start.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"

stop_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "Stopping port $port (pids: $pids)"
    kill -9 $pids 2>/dev/null || true
  else
    echo "Port $port already free"
  fi
}

stop_port 3000
stop_port 8000
rm -f "$RUN_DIR/backend.pid" "$RUN_DIR/frontend.pid" 2>/dev/null || true
echo "Done."
