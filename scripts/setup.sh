#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
docker compose -f infrastructure/docker-compose.yml up -d --wait db redis
python3.12 -m venv backend/.venv
(
  cd backend
  .venv/bin/python -m pip install -r requirements-dev.lock -e '.[dev]'
  .venv/bin/python -m alembic upgrade head
  if [ "${1:-}" = "--seed" ]; then .venv/bin/python -m app.db.seed; fi
)
npm --prefix frontend ci
printf '%s\n' 'Ready. Run npm run dev; run backend worker separately. See README.md.'
