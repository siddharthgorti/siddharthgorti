#!/usr/bin/env bash
# Replace the database with a backup made by deploy/backup.sh.
#   ./deploy/restore.sh deploy/backups/tuition-20261117T021500Z.sql.gz
# A safety backup of the current data is taken first.
set -euo pipefail
cd "$(dirname "$0")/.."

file="${1:-}"
if [[ -z "$file" || ! -f "$file" ]]; then
  echo "Usage: $0 deploy/backups/tuition-<timestamp>.sql.gz" >&2
  exit 1
fi
gzip -t "$file" || { echo "$file is not a valid gzip file." >&2; exit 1; }

echo "This will REPLACE ALL CURRENT DATA (every account, student and session) with:"
echo "  $file"
read -r -p "Type RESTORE to continue: " answer
if [[ "$answer" != "RESTORE" ]]; then
  echo "Cancelled. Nothing was changed."
  exit 1
fi

echo "==> Safety backup of the current data"
./deploy/backup.sh

echo "==> Stopping the backend"
./deploy/compose.sh stop backend
trap 'echo "Restore did not finish. The backend is stopped; fix the problem, then run: ./deploy/compose.sh start backend" >&2' ERR

echo "==> Recreating the database"
# shellcheck disable=SC2016
./deploy/compose.sh exec -T db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'

echo "==> Loading $file"
# shellcheck disable=SC2016
gunzip -c "$file" | ./deploy/compose.sh exec -T db sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

trap - ERR
echo "==> Starting the backend"
./deploy/compose.sh start backend
echo "Restore complete."
