#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"

cd "$ROOT"

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:8501}"
exec uvicorn backend.app:app --host 0.0.0.0 --port 9000 --reload --no-server-header


