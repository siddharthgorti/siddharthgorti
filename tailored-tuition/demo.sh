#!/usr/bin/env bash
# One-command local demo (macOS / Linux): sets up, builds and runs Tailored Tuition.
# Phones on the same Wi-Fi can open the printed "phone" URL.
# Usage: ./demo.sh          Stop with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1. $2"; exit 1; }; }
need python3 "Install Python 3.12+ from https://www.python.org/downloads/"
need node "Install Node.js 22 LTS from https://nodejs.org/"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || { echo "Python 3.12+ is required."; exit 1; }

in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
for port in 3000 8000; do
  if in_use "$port"; then
    echo "Port $port is already in use (is the demo already running in another window?)."
    echo "Close that window, or find the process with: lsof -i :$port"
    exit 1
  fi
done

echo "==> Backend setup"
if [ ! -d backend/.venv ]; then python3 -m venv backend/.venv; fi
backend/.venv/bin/pip install -q -r backend/requirements.txt
if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; fi
if ! grep -qE '^ANTHROPIC_API_KEY=.+' backend/.env; then
  echo "    No API key in backend/.env: running in OFFLINE DEMO MODE (canned replies)."
  echo "    For real tutoring, add ANTHROPIC_API_KEY=sk-ant-... to backend/.env and re-run."
fi

echo "==> Frontend setup (first run takes a few minutes)"
(cd frontend && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && npm run build >/dev/null)

echo "==> Starting"
(cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT INT TERM

for _ in $(seq 1 30); do
  curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
  sleep 1
done

IP=$( (ipconfig getifaddr en0 || ipconfig getifaddr en1 || hostname -I | awk '{print $1}') 2>/dev/null || true)
echo
echo "  On this computer:  http://localhost:3000"
[ -n "$IP" ] && echo "  On a phone (same Wi-Fi):  http://$IP:3000"
echo "  Stop with Ctrl+C"
echo
cd frontend && npx next start -H 0.0.0.0 -p 3000
