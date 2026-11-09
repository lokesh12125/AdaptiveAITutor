#!/usr/bin/env bash
# Starts the execution service, API and web app together. Press Ctrl+C to stop them all.
set -euo pipefail
cd "$(dirname "$0")/.."

# Starting a second copy would only fail with confusing port errors, so check first.
busy=()
for port in 5173 8101 8102; do
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then busy+=("$port"); fi
done
if [ "${#busy[@]}" -eq 3 ]; then
  echo "Trellis is already running. Open http://127.0.0.1:5173"
  exit 0
fi
if [ "${#busy[@]}" -gt 0 ]; then
  echo "Cannot start: port(s) ${busy[*]} already in use, while the rest of the app is not running."
  echo "Stop whatever is using them, then run this again. To see what it is: lsof -nP -iTCP:${busy[0]} -sTCP:LISTEN"
  exit 1
fi

docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop, then run this again."; exit 1; }
docker compose up -d db >/dev/null

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd runner && exec .venv/bin/uvicorn runner_service.main:app --host 127.0.0.1 --port 8102 --log-level warning) & pids+=($!)
(cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8101 --log-level info) & pids+=($!)
(cd frontend && exec npx vite --host 127.0.0.1 --port 5173 --strictPort) & pids+=($!)

echo
echo "Open http://127.0.0.1:5173"
echo
wait
