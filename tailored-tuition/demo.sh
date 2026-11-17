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
# Which AI the tutor will use: Claude (API key), else a local Ollama model, else canned demo replies.
if grep -qE '^ANTHROPIC_API_KEY=.+' backend/.env; then
  AI_MODE="Claude (Anthropic API key found)"
elif curl -s --max-time 2 --noproxy localhost http://localhost:11434/api/tags >/dev/null 2>&1; then
  AI_MODE="LOCAL model via Ollama (free; weaker at maths and slower than Claude)"
else
  AI_MODE="OFFLINE DEMO - canned replies, no real tutoring"
  echo "    No API key and Ollama isn't running, so the tutor will NOT really tutor."
  echo "    For real tutoring, either:"
  echo "      - free: install Ollama (https://ollama.com), run: ollama pull qwen2.5:7b , then re-run this"
  echo "      - best: add ANTHROPIC_API_KEY=sk-ant-... to backend/.env and re-run this"
fi

echo "==> Frontend setup (first run takes a few minutes)"
# Reinstall when the lockfile changed since the last install (e.g. after git pull),
# so security updates to frontend packages actually reach this machine.
(cd frontend && { [ node_modules/.package-lock.json -nt package-lock.json ] || npm ci --no-audit --no-fund; } && npm run build >/dev/null)

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
echo "  Tutor AI: $AI_MODE"
echo "  On this computer:  http://localhost:3000"
[ -n "$IP" ] && echo "  On a phone (same Wi-Fi):  http://$IP:3000"
echo "  Stop with Ctrl+C"
echo
cd frontend && npx next start -H 0.0.0.0 -p 3000
