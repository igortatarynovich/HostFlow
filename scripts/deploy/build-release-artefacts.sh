#!/usr/bin/env bash
# Build backend image + frontend tree for one commit (OL-2A C-1, C-2, C-3).
#
# Does not deploy. Does not tag. Does not touch the live compose stack.
# Requires a clean checkout so the artefact cannot include uncommitted files.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "refusing to build: working tree is not clean" >&2
  git status --short >&2
  exit 2
fi

GIT_SHA="$(git rev-parse HEAD)"
GIT_REF="$(git describe --tags --exact-match 2>/dev/null || true)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
short="${GIT_SHA:0:12}"

out_dir="${HOSTFLOW_RELEASE_DIR:-$repo_root/releases}"
frontend_dir="$out_dir/frontend/$GIT_SHA"
image_tag="${HOSTFLOW_BACKEND_IMAGE:-hostflow-backend:$short}"

mkdir -p "$frontend_dir" "$out_dir/backend"

echo "building backend image $image_tag from $GIT_SHA"
docker build \
  -f deploy/Dockerfile.backend \
  --build-arg "GIT_SHA=$GIT_SHA" \
  --build-arg "GIT_REF=$GIT_REF" \
  --build-arg "BUILD_TIME=$BUILD_TIME" \
  -t "$image_tag" \
  "$repo_root"

digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$image_tag" 2>/dev/null || true)"
if [[ -z "$digest" ]]; then
  # Local-only images have no repo digest until they are pushed. Fall back to Id.
  digest="$(docker image inspect --format '{{.Id}}' "$image_tag")"
fi

echo "building frontend outside the live document root → $frontend_dir"
(
  cd hostflow-frontend
  if [[ ! -d node_modules ]]; then
    npm ci
  else
    npm ci --prefer-offline --no-audit --no-fund
  fi
  HOSTFLOW_REVISION="$GIT_SHA" \
  HOSTFLOW_VERSION="${GIT_REF:-unknown}" \
  HOSTFLOW_BUILT_AT="$BUILD_TIME" \
  npm run build -- --outDir "$frontend_dir" --emptyOutDir
)

tree_hash="$(bash "$repo_root/scripts/deploy/frontend-tree-hash.sh" "$frontend_dir")"

cat > "$out_dir/backend/$GIT_SHA.json" <<JSON
{
  "kind": "backend-image",
  "revision": "$GIT_SHA",
  "version": "${GIT_REF:-unknown}",
  "built_at": "$BUILD_TIME",
  "image": "$image_tag",
  "identity": "$digest"
}
JSON

cat > "$frontend_dir/../$GIT_SHA.identity.json" <<JSON
{
  "kind": "frontend-tree",
  "revision": "$GIT_SHA",
  "version": "${GIT_REF:-unknown}",
  "built_at": "$BUILD_TIME",
  "path": "$frontend_dir",
  "identity": "sha256:$tree_hash"
}
JSON

echo "backend identity: $digest"
echo "frontend identity: sha256:$tree_hash"
echo "frontend tree: $frontend_dir"
echo "done"
