#!/usr/bin/env bash
# Staging Postgres restore drill (executable runbook).
# Usage:
#   ./scripts/restore_drill.sh dump.sql postgresql://user:pass@host:5432/supply_restore
#
# Proves: dump restore → alembic upgrade → /health/ready smoke (API must be pointed at restore DB).
set -euo pipefail

DUMP_FILE="${1:-}"
RESTORE_URL="${2:-}"

if [[ -z "$DUMP_FILE" || -z "$RESTORE_URL" ]]; then
  echo "Usage: $0 <dump.sql|dump.dump> <RESTORE_DATABASE_URL>" >&2
  exit 2
fi

if [[ ! -f "$DUMP_FILE" ]]; then
  echo "Dump file not found: $DUMP_FILE" >&2
  exit 1
fi

# An existing database is never overwritten by this helper.
TABLE_COUNT=$(psql "$RESTORE_URL" -At -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
if [[ "$TABLE_COUNT" != "0" ]]; then
  echo "Restore target must be an empty, isolated database" >&2
  exit 1
fi
echo "==> Restoring backup into an empty target database"
if [[ "$DUMP_FILE" == *.sql ]]; then
  psql "$RESTORE_URL" -v ON_ERROR_STOP=1 -f "$DUMP_FILE"
else
  pg_restore --exit-on-error --no-owner --dbname="$RESTORE_URL" "$DUMP_FILE"
fi

echo "==> Running alembic upgrade head against restore DB"
cd "$(dirname "$0")/../backend"
export DATABASE_URL="$RESTORE_URL"
export ALLOW_CREATE_ALL_ON_STARTUP=false
alembic upgrade head

echo "==> Schema restore drill complete."
echo "Next: point an isolated staging API at the restored database and verify /health/ready"
echo "Record result in docs/reports/RC3_RESTORE_DRILL.md"
