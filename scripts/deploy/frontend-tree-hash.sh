#!/usr/bin/env bash
# Content hash of a frontend artefact tree (OL-2A C-2).
# Prints a single sha256 hex of the sorted (path, file-digest) list.
set -euo pipefail
root="${1:?usage: frontend-tree-hash.sh <artefact-dir>}"
if [[ ! -d "$root" ]]; then
  echo "not a directory: $root" >&2
  exit 1
fi
(
  cd "$root"
  find . -type f -print0 | sort -z | while IFS= read -r -d '' f; do
    # path + digest, so renaming or content change both move the identity
    printf '%s ' "$f"
    sha256sum -- "$f" | awk '{print $1}'
  done
) | sha256sum | awk '{print $1}'
