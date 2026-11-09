#!/usr/bin/env bash
# One-time local setup. Safe to run again. Requires Docker, uv (or Python 3.12) and Node.js 20 or later.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Checking tools"
docker info >/dev/null 2>&1 || { echo "Docker is not running. Start Docker Desktop, then run this again."; exit 1; }
command -v node >/dev/null || { echo "Node.js is required."; exit 1; }
if ! command -v uv >/dev/null; then echo "uv is required: https://docs.astral.sh/uv/ (or: pip install uv)"; exit 1; fi

if [ ! -f .env ]; then
  echo "==> Creating .env with fresh local secrets"
  cp .env.example .env
  token=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
  invite=$(python3 -c 'import secrets; print("teach-" + secrets.token_hex(5))')
  python3 - "$token" "$invite" <<'PY'
import re, sys
text = open(".env").read()
text = re.sub(r"^RUNNER_TOKEN=.*$", "RUNNER_TOKEN=" + sys.argv[1], text, flags=re.M)
text = re.sub(r"^TEACHER_INVITE_CODE=.*$", "TEACHER_INVITE_CODE=" + sys.argv[2], text, flags=re.M)
open(".env", "w").write(text)
PY
  echo "    Teacher invite code for this machine: $invite"
fi

echo "==> Starting PostgreSQL"
docker compose up -d db
for _ in $(seq 1 40); do docker compose exec -T db pg_isready -U csmasf >/dev/null 2>&1 && break; sleep 1; done

echo "==> Building the code sandbox image"
docker build -q -t csmasf-sandbox:py312 runner/sandbox

echo "==> Installing the execution service"
(cd runner && uv venv --quiet --allow-existing --python 3.12 .venv && uv pip install --quiet --python .venv/bin/python -e '.[dev]')

echo "==> Installing the backend"
(cd backend && uv venv --quiet --allow-existing --python 3.12 .venv && uv pip install --quiet --python .venv/bin/python -e '.[dev]')

echo "==> Creating database tables and loading content"
(cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed)

echo "==> Installing the frontend"
(cd frontend && npm ci --no-audit --no-fund --silent)

echo
echo "Setup finished. Start everything with: ./scripts/dev.sh"
