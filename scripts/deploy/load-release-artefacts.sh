#!/usr/bin/env bash
# Reload a retained artefact by digest. Never rebuilds (OL-2A C-6).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
store="${HOSTFLOW_ARTEFACT_STORE:-/var/lib/hostflow/artefact-store}"
python="${HOSTFLOW_PYTHON:-python3}"
store_py="$here/artefact_store.py"

usage() {
  cat <<'EOF' >&2
usage:
  load-release-artefacts.sh backend <sha256:…|hex>
  load-release-artefacts.sh frontend <sha256:…|hex> <dest-dir>
EOF
  exit 2
}

[[ $# -ge 1 ]] || usage
cmd="$1"
shift

case "$cmd" in
  backend)
    digest="${1:?digest required}"
    blob="$("$python" "$store_py" blob-path --store "$store" --kind images --digest "$digest")"
    if [[ ! -f "$blob" ]]; then
      echo "rollback failed: backend blob missing: $blob" >&2
      echo "rebuild is not a fallback" >&2
      exit 3
    fi
    docker load -i "$blob"
    echo "loaded backend from $blob"
    ;;
  frontend)
    digest="${1:?digest required}"
    dest="${2:?destination directory required}"
    blob="$("$python" "$store_py" blob-path --store "$store" --kind frontend --digest "$digest")"
    if [[ ! -f "$blob" ]]; then
      echo "rollback failed: frontend blob missing: $blob" >&2
      echo "rebuild is not a fallback" >&2
      exit 3
    fi
    mkdir -p "$dest"
    # Refuse to unpack over a non-empty dest: rollback publishes beside, then swaps.
    if [[ -n "$(find "$dest" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
      echo "refusing to unpack into non-empty directory: $dest" >&2
      exit 2
    fi
    tar -C "$dest" -xf "$blob"
    echo "loaded frontend sha256:${digest#sha256:} -> $dest"
    ;;
  *)
    usage
    ;;
esac
