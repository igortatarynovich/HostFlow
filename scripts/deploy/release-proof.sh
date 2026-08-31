#!/usr/bin/env bash
# Fresh-DB deployment proof used by CI and RB-2 (OL-2C).
#
# Identity is a commit SHA supplied by the caller (GITHUB_SHA / GIT_SHA),
# never `git rev-parse` at request time. A dirty tree is refused so a
# bind-mount working tree cannot pretend to be a release.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" && "${HOSTFLOW_PROOF_ALLOW_DIRTY:-}" != "1" ]]; then
  echo "release-proof: refusing dirty working tree" >&2
  git status --short >&2
  exit 2
fi

HEAD_SHA="$(git rev-parse HEAD)"
CLAIMED="${GIT_SHA:-${GITHUB_SHA:-}}"
if [[ -z "$CLAIMED" ]]; then
  echo "release-proof: GIT_SHA or GITHUB_SHA is required (do not default to the working tree)" >&2
  exit 2
fi
if [[ "$CLAIMED" != "$HEAD_SHA" ]]; then
  echo "release-proof: claimed SHA $CLAIMED does not match HEAD $HEAD_SHA" >&2
  exit 2
fi

export GIT_SHA="$HEAD_SHA"
export HOSTFLOW_REVISION="$HEAD_SHA"
export HOSTFLOW_VERSION="${GIT_REF:-unknown}"
export HOSTFLOW_BUILT_AT="${BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"

: "${DATABASE_URL:?DATABASE_URL is required}"
export ASYNC_DATABASE_URL="${ASYNC_DATABASE_URL:-$DATABASE_URL}"
export ALEMBIC_DATABASE_URL="${ALEMBIC_DATABASE_URL:-${SYNC_DATABASE_URL:-}}"
if [[ -z "${ALEMBIC_DATABASE_URL}" ]]; then
  # asyncpg URL → psycopg for Alembic
  ALEMBIC_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql+psycopg:}"
  export ALEMBIC_DATABASE_URL
fi
export SYNC_DATABASE_URL="${SYNC_DATABASE_URL:-$ALEMBIC_DATABASE_URL}"
export JWT_SECRET="${JWT_SECRET:-ol2c-ci-not-a-production-secret}"
export PYTHONPATH="${repo_root}/backend${PYTHONPATH:+:$PYTHONPATH}"

echo "release-proof: identity $HEAD_SHA"
echo "release-proof: alembic -c alembic.ini upgrade heads"
alembic -c "$repo_root/alembic.ini" upgrade heads

PROOF_PORT="${HOSTFLOW_PROOF_PORT:-8099}"
PROOF_HOST="${HOSTFLOW_PROOF_HOST:-127.0.0.1}"
base="http://${PROOF_HOST}:${PROOF_PORT}"

export HOSTFLOW_AUTH_SEED_ENABLED="${HOSTFLOW_AUTH_SEED_ENABLED:-1}"

echo "release-proof: starting application HOSTFLOW_REVISION=$HEAD_SHA"
uvicorn app.main:app --host "$PROOF_HOST" --port "$PROOF_PORT" &
app_pid=$!
cleanup() {
  kill "$app_pid" 2>/dev/null || true
  wait "$app_pid" 2>/dev/null || true
}
trap cleanup EXIT

ok=0
for _ in $(seq 1 60); do
  if curl -fsS "$base/healthz" >/tmp/ol2c-healthz.json 2>/dev/null; then
    ok=1
    break
  fi
  sleep 1
done
if [[ "$ok" -ne 1 ]]; then
  echo "release-proof: /healthz did not become ready" >&2
  exit 1
fi
echo "release-proof: /healthz $(cat /tmp/ol2c-healthz.json)"

code="$(curl -sS -o /tmp/ol2c-build.body -w '%{http_code}' "$base/build" || true)"
if [[ -f "$repo_root/backend/app/core/build_info.py" ]]; then
  if [[ "$code" != "200" ]]; then
    echo "release-proof: /build required (OL-2A on tree) but HTTP $code" >&2
    exit 1
  fi
  python3 - "$HEAD_SHA" /tmp/ol2c-build.body <<'PY'
import json, sys
claimed, path = sys.argv[1], sys.argv[2]
body = json.loads(open(path).read())
got = body.get("revision")
if got != claimed:
    raise SystemExit(f"/build revision {got!r} != {claimed}")
print(f"release-proof: /build revision {got}")
PY
else
  echo "release-proof: residual — /build not asserted (needs OL-2A #332 on the tree); HTTP $code"
fi

if [[ -f "$repo_root/backend/alembic/versions/202608310001_bootstrap_admin_schema.py" ]]; then
  login_code="$(curl -sS -o /tmp/ol2c-login.body -w '%{http_code}' \
    -H 'Content-Type: application/json' \
    -H 'X-Tenant-Id: 11111111-1111-1111-1111-111111111111' \
    -d '{"email":"admin@hostflow.dev","password":"Admin@025"}' \
    "$base/api/v1/auth/login" || true)"
  if [[ "$login_code" != "200" ]]; then
    echo "release-proof: admin login required (OL-2B first-admin on tree) but HTTP $login_code" >&2
    cat /tmp/ol2c-login.body >&2 || true
    exit 1
  fi
  echo "release-proof: admin login 200"
else
  echo "release-proof: residual — admin login not asserted (needs OL-2B #336 on the tree)"
fi

echo "release-proof: PASS identity=$HEAD_SHA"
