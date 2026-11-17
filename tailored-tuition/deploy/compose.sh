#!/usr/bin/env bash
# Run docker compose for the production stack with the production env file.
#   ./deploy/compose.sh up -d --build      start / update
#   ./deploy/compose.sh ps                 status
#   ./deploy/compose.sh logs -f backend    follow logs
set -euo pipefail
cd "$(dirname "$0")/.."

env_file="deploy/.env.production"
if [[ ! -f "$env_file" ]]; then
  echo "Missing $env_file. Copy deploy/.env.production.example to it and fill it in." >&2
  exit 1
fi
if grep -q 'CHANGE_ME' "$env_file"; then
  echo "$env_file still contains CHANGE_ME placeholders. Fill them in first." >&2
  exit 1
fi

exec docker compose --env-file "$env_file" -f docker-compose.prod.yml "$@"
