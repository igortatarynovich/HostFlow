"""
One-shot migration: copy every file under ``UPLOAD_DIR`` into the configured
S3-compatible bucket, preserving the relative path as the object key.

Usage
-----

::

    # Dry run — just print what would be uploaded, no writes.
    python -m backend.scripts.migrate_uploads_to_s3 --dry-run

    # Real run, reading credentials from the environment.
    OBJECT_STORAGE_BACKEND=s3 \
    OBJECT_STORAGE_BUCKET=hostflow-uploads \
    OBJECT_STORAGE_ENDPOINT_URL=http://minio:9000 \
    OBJECT_STORAGE_ACCESS_KEY_ID=hostflow \
    OBJECT_STORAGE_SECRET_ACCESS_KEY=hostflow-minio \
    python -m backend.scripts.migrate_uploads_to_s3

Design notes
------------

*   The script does **not** touch ``Document.files[*].url`` entries. Those URLs
    keep pointing at ``/uploads/<key>``; once the backend is flipped to S3,
    :func:`app.modules.documents.storage._build_public_url` re-resolves them
    through :func:`app.core.object_storage.get_object_storage` and hands back
    a presigned URL transparently. That keeps the rollout reversible:
    flipping ``OBJECT_STORAGE_BACKEND`` back to ``fs`` restores the old path
    without data surgery.

*   Files already present in the bucket with the same key and size are
    skipped. Use ``--force`` to re-upload anyway (useful after a corrupted
    sync).

*   The script is idempotent — run it again after adding new uploads to copy
    only the delta.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Iterator, Optional, Tuple

# Make sure we can import `backend.app.*` when invoked as
# `python -m backend.scripts.migrate_uploads_to_s3` from the repo root or the
# backend container.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
for candidate in (_REPO_ROOT, _REPO_ROOT / "backend"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from backend.app.core.object_storage import (  # noqa: E402
    FilesystemObjectStorage,
    S3ObjectStorage,
    get_object_storage,
    reset_object_storage,
)
from backend.app.core.settings import settings  # noqa: E402

logger = logging.getLogger("migrate_uploads_to_s3")


def _iter_files(root: Path) -> Iterator[Tuple[Path, str]]:
    """Yield ``(absolute_path, relative_posix_key)`` for every file below root."""
    root = root.resolve()
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:  # pragma: no cover - symlink weirdness
            continue
        # Skip hidden junk and transient files.
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.name.endswith(("~", ".tmp", ".part")):
            continue
        yield path, rel.as_posix()


async def _maybe_upload(
    dest: S3ObjectStorage,
    abs_path: Path,
    key: str,
    *,
    force: bool,
    dry_run: bool,
) -> str:
    """Return one of ``uploaded``, ``skipped``, ``planned``, ``skip-exists``."""
    size = abs_path.stat().st_size
    if not force and await dest.exists(key):
        return "skip-exists"
    if dry_run:
        return "planned"
    with abs_path.open("rb") as fh:
        await dest.save_stream(key, fh)
    logger.info("→ uploaded %s (%s bytes)", key, size)
    return "uploaded"


async def run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Source is always the legacy FS root — independent of the configured
    # backend, so the script works even *after* switching the backend to S3.
    source_root = Path(args.source or os.environ.get("UPLOAD_DIR") or "").resolve()
    if not args.source:
        # Fall back to the FS backend defaults when no explicit source given.
        source_root = FilesystemObjectStorage(
            Path(os.environ.get("UPLOAD_DIR") or Path(__file__).resolve().parents[1] / "uploads")
        ).local_path("")  # type: ignore[assignment]
        source_root = Path(source_root) if source_root else Path(".")
    if not source_root.is_dir():
        logger.error("Source directory does not exist: %s", source_root)
        return 2

    # Destination = the S3 backend, regardless of OBJECT_STORAGE_BACKEND.
    # We force-instantiate S3 here so a half-configured env fails loudly.
    if settings.object_storage_backend.lower() != "s3":
        logger.error(
            "OBJECT_STORAGE_BACKEND is %r; set it to 's3' before running the migration.",
            settings.object_storage_backend,
        )
        return 2
    reset_object_storage()
    dest = get_object_storage()
    if not isinstance(dest, S3ObjectStorage):
        logger.error(
            "S3 backend failed to initialise — check OBJECT_STORAGE_* env vars "
            "and aioboto3/boto3 install."
        )
        return 2

    logger.info(
        "Migrating %s → bucket=%s endpoint=%s",
        source_root,
        settings.object_storage_bucket,
        settings.object_storage_endpoint_url or "<aws-default>",
    )

    stats: dict[str, int] = {
        "uploaded": 0,
        "planned": 0,
        "skip-exists": 0,
        "skipped": 0,
        "failed": 0,
    }
    total_bytes = 0

    for abs_path, key in _iter_files(source_root):
        total_bytes += abs_path.stat().st_size
        try:
            outcome = await _maybe_upload(
                dest,
                abs_path,
                key,
                force=args.force,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            logger.exception("Failed to upload %s: %s", key, exc)
            stats["failed"] += 1
            continue
        stats[outcome] = stats.get(outcome, 0) + 1
        if args.dry_run and outcome == "planned":
            logger.info("[dry-run] would upload %s (%s bytes)", key, abs_path.stat().st_size)

    logger.info(
        "Done. uploaded=%d planned=%d skip-exists=%d failed=%d total_bytes≈%d",
        stats["uploaded"],
        stats["planned"],
        stats["skip-exists"],
        stats["failed"],
        total_bytes,
    )
    return 0 if stats["failed"] == 0 else 1


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=None,
        help="Source directory (defaults to $UPLOAD_DIR or backend/uploads).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without writing to S3.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Upload even if an object with the same key already exists.",
    )
    return parser.parse_args(argv)


def main() -> int:
    return asyncio.run(run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
