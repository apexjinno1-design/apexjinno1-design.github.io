#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_runtime=/workspace/.stock-runtime
mkdir -p "$task_runtime"
export DATABASE_URL="sqlite:///$task_runtime/demo.db"
export DEMO_MODE=true
export SCHEDULER_ENABLED=false
cd "$task_root/backend"
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli demo
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
