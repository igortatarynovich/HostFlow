#!/usr/bin/env bash
# Live-host deploy for docker-compose.yml (bind-mounted working tree on hostflow.cc).
#
# This is NOT RB-1 / OL-2 immutable artefacts. Production still executes the
# checkout. This script makes that path actually publish what operators think
# they deployed:
#   - frontend is built outside the live root, then rsynced into the Caddy
#     bind-mount (./hostflow-frontend/dist → container /var/www/hostflow-frontend)
#   - backend/arq-worker are recreated so uvicorn/arq reload bind-mounted Python
#     (the live command has no --reload)
#   - HOSTFLOW_* is baked into the process env and into dist/build.json
#
# Host path /var/www/hostflow-frontend is a decoy: Caddy does not serve it.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

usage() {
  cat <<'EOF'
Usage: scripts/deploy/deploy-live.sh [options]

Deploy the current checkout through the live compose stack (hostflow.cc).

Options:
  --pull            Fast-forward from origin (refused if the tree is dirty)
  --no-pull         Do not fetch/merge (default)
  --frontend-only   Rebuild and publish SPA only; do not recreate API/worker
  --skip-frontend   Recreate API/worker and migrate; do not rebuild SPA
  --skip-migrate    Do not run alembic
  --build-backend   docker compose build backend/arq-worker before recreate
  -h, --help        Show this help

This is the live working-tree path, not RB-1 (retained artefacts).
EOF
}

pull=0
frontend_only=0
skip_frontend=0
skip_migrate=0
build_backend=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull) pull=1 ;;
    --no-pull) pull=0 ;;
    --frontend-only) frontend_only=1 ;;
    --skip-frontend) skip_frontend=1 ;;
    --skip-migrate) skip_migrate=1 ;;
    --build-backend) build_backend=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$frontend_only" -eq 1 && "$skip_frontend" -eq 1 ]]; then
  echo "refusing: --frontend-only and --skip-frontend cannot be combined" >&2
  exit 2
fi

compose() {
  docker compose "$@"
}

dirty="$(git status --porcelain)"
branch="$(git rev-parse --abbrev-ref HEAD)"
remote_ref="origin/integration/release-product-a-b"

if [[ "$pull" -eq 1 ]]; then
  if [[ -n "$dirty" ]]; then
    echo "refusing --pull: working tree is dirty. Commit, stash, or omit --pull." >&2
    git status --short >&2
    exit 2
  fi
  git fetch origin
  git merge --ff-only "$remote_ref"
fi

GIT_SHA="$(git rev-parse HEAD)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
GIT_REF="$(git describe --tags --exact-match 2>/dev/null || true)"
if [[ -n "$dirty" ]]; then
  HOSTFLOW_VERSION="${GIT_REF:-working-tree}+dirty"
else
  HOSTFLOW_VERSION="${GIT_REF:-$branch}"
fi

export HOSTFLOW_REVISION="$GIT_SHA"
export HOSTFLOW_VERSION
export HOSTFLOW_BUILT_AT="$BUILD_TIME"

echo "live deploy"
echo "  branch:   $branch"
echo "  revision: $GIT_SHA"
echo "  version:  $HOSTFLOW_VERSION"
echo "  built_at: $BUILD_TIME"
if [[ -n "$dirty" ]]; then
  echo "  warning:  dirty working tree will be published (not just HEAD)"
  git status --short
fi

publish_frontend() {
  local staging
  staging="$(mktemp -d /tmp/hostflow-frontend-build.XXXXXX)"
  trap 'rm -rf "$staging"' RETURN

  echo "building frontend outside the live document root → $staging"
  (
    cd hostflow-frontend
    if [[ ! -d node_modules ]] || [[ -f package-lock.json && package-lock.json -nt node_modules ]]; then
      echo "npm ci (lockfile newer than node_modules or modules missing)"
      npm ci --prefer-offline --no-audit --no-fund
    fi
    HOSTFLOW_REVISION="$HOSTFLOW_REVISION" \
    HOSTFLOW_VERSION="$HOSTFLOW_VERSION" \
    HOSTFLOW_BUILT_AT="$HOSTFLOW_BUILT_AT" \
    npm run build -- --outDir "$staging" --emptyOutDir
  )

  if [[ ! -f "$staging/index.html" || ! -f "$staging/build.json" ]]; then
    echo "refusing to publish: staging tree is missing index.html or build.json" >&2
    exit 1
  fi

  mkdir -p hostflow-frontend/dist
  echo "publishing into Caddy bind-mount hostflow-frontend/dist (not host /var/www)"
  rsync -a --delete "$staging"/ hostflow-frontend/dist/
}

if [[ "$skip_frontend" -eq 0 ]]; then
  publish_frontend
  compose restart caddy
fi

if [[ "$frontend_only" -eq 0 ]]; then
  backend_args=(up -d --force-recreate --no-deps)
  if [[ "$build_backend" -eq 1 ]]; then
    backend_args+=(--build)
  fi
  echo "recreating backend so bind-mounted Python is loaded (uvicorn has no --reload)"
  compose "${backend_args[@]}" backend
  if compose ps --status running --services 2>/dev/null | grep -qx arq-worker; then
    echo "recreating arq-worker"
    compose --profile arq "${backend_args[@]}" arq-worker
  fi

  if [[ "$skip_migrate" -eq 0 ]]; then
    echo "alembic upgrade heads (in-container shim; graph is backend/alembic)"
    compose exec -T backend alembic upgrade heads
  fi
fi

echo "waiting for backend /healthz"
ok=0
for _ in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 1
done
if [[ "$ok" -ne 1 ]]; then
  echo "backend did not become healthy on :8000" >&2
  compose logs backend --tail 80 >&2 || true
  exit 1
fi

echo "--- GET /build (process identity) ---"
curl -sS http://127.0.0.1:8000/build
echo
echo "--- dist/build.json (SPA identity) ---"
cat hostflow-frontend/dist/build.json
echo "--- https://hostflow.cc/build.json ---"
curl -sk https://hostflow.cc/build.json || true
echo
echo "done"
echo "hard-refresh the browser (Ctrl+Shift+R) if the tab still holds an old index-*.js"
