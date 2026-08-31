#!/usr/bin/env bash
# Atomically publish a previously built frontend tree (OL-2A C-2).
#
# The live document root must be a symlink. This script never writes into a
# directory that is currently being served as a real folder, and never runs
# `vite build` against the live root.
set -euo pipefail

src="${1:?usage: publish-frontend.sh <built-tree> [releases-root]}"
releases_root="${2:-/var/lib/hostflow/releases/frontend}"

if [[ ! -d "$src" ]]; then
  echo "not a directory: $src" >&2
  exit 1
fi
if [[ ! -f "$src/index.html" ]]; then
  echo "refusing: $src has no index.html" >&2
  exit 1
fi
if [[ ! -f "$src/build.json" ]]; then
  echo "refusing: $src has no build.json (not an OL-2A artefact)" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
identity="$(bash "$repo_root/scripts/deploy/frontend-tree-hash.sh" "$src")"
dest="$releases_root/$identity"

mkdir -p "$releases_root"
if [[ ! -d "$dest" ]]; then
  mkdir -p "$dest"
  # Copy rather than move: the built tree may still be the retained artefact store.
  cp -a "$src"/. "$dest"/
fi

tmp_link="$releases_root/current.tmp.$$"
ln -sfn "$dest" "$tmp_link"
mv -Tf "$tmp_link" "$releases_root/current"

echo "published sha256:$identity"
echo "current -> $dest"
