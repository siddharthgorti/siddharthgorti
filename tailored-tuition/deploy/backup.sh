#!/usr/bin/env bash
# Dump the Postgres database to deploy/backups/tuition-<UTC timestamp>.sql.gz and
# delete backups older than KEEP_DAYS (default 14).
# Cron example (daily at 02:15): 15 2 * * * cd /opt/tailored-tuition && ./deploy/backup.sh >> deploy/backups/backup.log 2>&1
# These files contain personal data about children: keep them private, and copy
# them off this server (see docs/DEPLOY.md).
set -euo pipefail
cd "$(dirname "$0")/.."

backup_dir="${BACKUP_DIR:-./deploy/backups}"
keep_days="${KEEP_DAYS:-14}"
umask 077
mkdir -p "$backup_dir"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$backup_dir/tuition-$stamp.sql.gz"
tmp="$out.partial"
trap 'rm -f "$tmp"' EXIT

# Single quotes: the variables expand inside the db container.
# shellcheck disable=SC2016
./deploy/compose.sh exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' \
  | gzip -9 > "$tmp"
mv "$tmp" "$out"

find "$backup_dir" -maxdepth 1 -type f -name 'tuition-*.sql.gz' -mtime +"$keep_days" -delete
echo "$(date -u +%FT%TZ) backup written: $out ($(du -h "$out" | cut -f1))"
