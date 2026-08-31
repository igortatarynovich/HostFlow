"""Local immutable artefact store (OL-2A C-1 clause 5 / C-1.5, OL-2D).

Identity is the digest, not the blob bytes and not a git ref. A path that
already exists is never rewritten. Missing blob ⇒ rollback has failed;
there is no rebuild fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


KINDS = ("images", "frontend")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_digest(value: str) -> str:
    text = value.strip()
    if text.startswith("sha256:"):
        text = text[len("sha256:") :]
    if len(text) != 64 or any(c not in "0123456789abcdef" for c in text.lower()):
        raise ValueError(f"expected 64-hex digest, got {value!r}")
    return text.lower()


def blob_path(store: Path, kind: str, digest: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
    return store / kind / f"{normalize_digest(digest)}.tar"


def manifest_path(store: Path, revision: str) -> Path:
    rev = revision.strip()
    if not rev or "/" in rev or rev in {".", ".."}:
        raise ValueError(f"invalid revision {revision!r}")
    return store / "manifests" / f"{rev}.json"


def frontend_tree_hash(root: Path) -> str:
    """Identity is ``frontend-tree-hash.sh`` (locale ``sort``), not Python code-point order.

    A Unicode-aware ``sort`` and ``sorted(as_posix())`` disagree on mixed-case
    and non-ASCII paths; the published OL-2B tree ``ba19d410…`` was hashed by
    the shell script. Calling it is the only way to keep retain and publish
    on the same digest.
    """
    if not root.is_dir():
        raise NotADirectoryError(root)
    script = Path(__file__).resolve().parent / "frontend-tree-hash.sh"
    out = subprocess.check_output(["bash", str(script), str(root)], text=True)
    digest = out.strip()
    if len(digest) != 64:
        raise RuntimeError(f"frontend-tree-hash.sh returned {out!r}")
    return digest


def retain_blob(store: Path, kind: str, digest: str, src: Path) -> Path:
    if not src.is_file():
        raise FileNotFoundError(src)
    dest = blob_path(store, kind, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        existing = _sha256_file(dest)
        incoming = _sha256_file(src)
        if existing != incoming:
            raise FileExistsError(
                f"refusing to overwrite {dest} with a different payload"
            )
        return dest
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_bytes(src.read_bytes())
    os.replace(tmp, dest)
    return dest


def write_manifest(
    store: Path,
    *,
    revision: str,
    backend_image_id: str,
    frontend_tree_hash_value: str,
    alembic_head: str,
    extra: dict | None = None,
) -> Path:
    dest = manifest_path(store, revision)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "release-artefact-manifest",
        "revision": revision.strip(),
        "backend_image_id": backend_image_id
        if backend_image_id.startswith("sha256:")
        else f"sha256:{normalize_digest(backend_image_id)}",
        "frontend_tree_hash": frontend_tree_hash_value
        if frontend_tree_hash_value.startswith("sha256:")
        else f"sha256:{normalize_digest(frontend_tree_hash_value)}",
        "alembic_head": alembic_head,
        "retained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if extra:
        payload.update(extra)
    if dest.exists():
        current = json.loads(dest.read_text())
        comparable = {k: current.get(k) for k in (
            "kind",
            "revision",
            "backend_image_id",
            "frontend_tree_hash",
            "alembic_head",
        )}
        incoming = {k: payload[k] for k in comparable}
        if comparable != incoming:
            raise FileExistsError(
                f"refusing to overwrite manifest {dest} with different identities"
            )
        return dest
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, dest)
    return dest


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_hash = sub.add_parser("tree-hash", help="content hash of a frontend tree")
    p_hash.add_argument("root", type=Path)

    p_retain = sub.add_parser("retain", help="store a blob immutably by digest")
    p_retain.add_argument("--store", type=Path, required=True)
    p_retain.add_argument("--kind", choices=KINDS, required=True)
    p_retain.add_argument("--digest", required=True)
    p_retain.add_argument("--blob", type=Path, required=True)

    p_path = sub.add_parser("blob-path", help="print the store path for a digest")
    p_path.add_argument("--store", type=Path, required=True)
    p_path.add_argument("--kind", choices=KINDS, required=True)
    p_path.add_argument("--digest", required=True)

    p_man = sub.add_parser("write-manifest")
    p_man.add_argument("--store", type=Path, required=True)
    p_man.add_argument("--revision", required=True)
    p_man.add_argument("--backend-id", required=True)
    p_man.add_argument("--frontend-hash", required=True)
    p_man.add_argument("--alembic-head", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "tree-hash":
        print(frontend_tree_hash(args.root.resolve()))
        return 0
    if args.cmd == "retain":
        dest = retain_blob(args.store, args.kind, args.digest, args.blob)
        print(dest)
        return 0
    if args.cmd == "blob-path":
        print(blob_path(args.store, args.kind, args.digest))
        return 0
    dest = write_manifest(
        args.store,
        revision=args.revision,
        backend_image_id=args.backend_id,
        frontend_tree_hash_value=args.frontend_hash,
        alembic_head=args.alembic_head,
    )
    print(dest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except (ValueError, FileExistsError, FileNotFoundError, NotADirectoryError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(2)
