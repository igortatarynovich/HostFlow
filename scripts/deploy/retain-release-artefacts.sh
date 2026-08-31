#!/usr/bin/env bash
# Retain a built release artefact by digest (OL-2A C-1.5 / C-6).
#
# Does not build. Does not tag. Does not touch the live compose stack.
# Re-retain of the same digest is idempotent. A different payload at the
# same path is refused. Missing blob later = rollback failed; no rebuild.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
store="${HOSTFLOW_ARTEFACT_STORE:-/var/lib/hostflow/artefact-store}"
python="${HOSTFLOW_PYTHON:-python3}"
store_py="$here/artefact_store.py"

usage() {
  cat <<'EOF' >&2
usage:
  retain-release-artefacts.sh backend <image-ref>
  retain-release-artefacts.sh frontend <artefact-dir>
  retain-release-artefacts.sh manifest \
      --revision <sha> \
      --backend-id <sha256:…|hex> \
      --frontend-hash <sha256:…|hex> \
      --alembic-head <revision>
EOF
  exit 2
}

[[ $# -ge 1 ]] || usage
cmd="$1"
shift

case "$cmd" in
  backend)
    image="${1:?image ref required}"
    id="$(docker image inspect --format '{{.Id}}' "$image")"
    hex="${id#sha256:}"
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    docker save "$image" -o "$tmp"
    dest="$("$python" "$store_py" retain --store "$store" --kind images --digest "$hex" --blob "$tmp")"
    echo "retained backend $id -> $dest"
    ;;
  frontend)
    root="${1:?frontend tree required}"
    if [[ ! -d "$root" ]]; then
      echo "not a directory: $root" >&2
      exit 1
    fi
    hex="$(bash "$here/frontend-tree-hash.sh" "$root")"
    tmp="$(mktemp)"
    trap 'rm -f "$tmp"' EXIT
    tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
      -C "$root" -cf "$tmp" .
    dest="$("$python" "$store_py" retain --store "$store" --kind frontend --digest "$hex" --blob "$tmp")"
    echo "retained frontend sha256:$hex -> $dest"
    ;;
  manifest)
    revision=""
    backend_id=""
    frontend_hash=""
    alembic_head=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --revision) revision="${2:?}"; shift 2 ;;
        --backend-id) backend_id="${2:?}"; shift 2 ;;
        --frontend-hash) frontend_hash="${2:?}"; shift 2 ;;
        --alembic-head) alembic_head="${2:?}"; shift 2 ;;
        *) usage ;;
      esac
    done
    [[ -n "$revision" && -n "$backend_id" && -n "$frontend_hash" && -n "$alembic_head" ]] || usage
    dest="$("$python" "$store_py" write-manifest \
      --store "$store" \
      --revision "$revision" \
      --backend-id "$backend_id" \
      --frontend-hash "$frontend_hash" \
      --alembic-head "$alembic_head")"
    echo "wrote manifest $dest"
    ;;
  *)
    usage
    ;;
esac
