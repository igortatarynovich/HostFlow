#!/usr/bin/env bash
# Cursor Cloud update script: refresh Python venv + frontend deps.
# Postgres/migrations live in the VM snapshot; this only reinstalls packages.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[cursor-cloud-update] repo: $ROOT"

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "python3.12 is required" >&2
  exit 1
fi

echo "[cursor-cloud-update] recreating .venv312"
rm -rf .venv312
python3.12 -m venv .venv312
.venv312/bin/python -m pip install --upgrade pip

echo "[cursor-cloud-update] installing backend requirements (pinned fastapi/prometheus)"
.venv312/bin/pip install -r backend/requirements.txt
.venv312/bin/pip install 'fastapi==0.115.6' 'prometheus-fastapi-instrumentator==7.0.0'

if command -v npm >/dev/null 2>&1; then
  echo "[cursor-cloud-update] npm install (hostflow-frontend)"
  (cd hostflow-frontend && npm install)
else
  echo "[cursor-cloud-update] npm not found, skipping frontend install"
fi

echo "[cursor-cloud-update] done"
.venv312/bin/pip show fastapi prometheus-fastapi-instrumentator | grep -E '^Name:|^Version:'
