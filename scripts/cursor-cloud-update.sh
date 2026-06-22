#!/usr/bin/env bash
# Cursor Cloud update script: sync deps without full venv rebuild (target: <60s).
# Postgres/migrations live in the VM snapshot.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VENV=".venv312"
PY="python3.12"

echo "[cursor-cloud-update] repo: $ROOT"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "python3.12 is required" >&2
  exit 1
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[cursor-cloud-update] creating $VENV"
  "$PY" -m venv "$VENV"
elif ! "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
  echo "[cursor-cloud-update] recreating $VENV (wrong python version)"
  rm -rf "$VENV"
  "$PY" -m venv "$VENV"
else
  echo "[cursor-cloud-update] reusing $VENV"
fi

"$VENV/bin/python" -m pip install -q --disable-pip-version-check --upgrade pip
echo "[cursor-cloud-update] syncing backend requirements"
"$VENV/bin/pip" install -q --disable-pip-version-check -r backend/requirements.txt
"$VENV/bin/pip" install -q --disable-pip-version-check 'fastapi==0.115.6' 'prometheus-fastapi-instrumentator==7.0.0'

if command -v npm >/dev/null 2>&1 && [[ -f hostflow-frontend/package.json ]]; then
  if [[ ! -d hostflow-frontend/node_modules ]]; then
    echo "[cursor-cloud-update] npm install (node_modules missing)"
    (cd hostflow-frontend && npm install --prefer-offline --no-audit --no-fund)
  else
    echo "[cursor-cloud-update] skipping npm install (node_modules present)"
  fi
fi

echo "[cursor-cloud-update] done"
"$VENV/bin/pip" show fastapi prometheus-fastapi-instrumentator | grep -E '^Name:|^Version:'
