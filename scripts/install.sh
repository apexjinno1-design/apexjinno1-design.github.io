#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.cache/uv}"
cd "$task_root/backend"
uv sync --frozen
cd "$task_root/frontend"
npm ci --cache /workspace/.cache/npm --no-fund
