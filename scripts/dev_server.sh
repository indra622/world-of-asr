#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH=backend:$PYTHONPATH

if [ -f backend/.env ]; then
  set -a
  # shellcheck disable=SC1091
  . backend/.env
  set +a
fi

echo "Starting backend on http://0.0.0.0:8000"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

