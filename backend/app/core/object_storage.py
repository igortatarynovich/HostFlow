"""
Object storage abstraction for HostFlow (Phase 0 #6).

Two backends are supported:

*   ``fs`` — default, backward-compatible. Files are persisted under
    ``settings.object_storage_local_root`` (== historical ``UPLOAD_DIR``) and
    served via the ``/uploads/<key>`` FastAPI route. All existing call sites
    that still write straight to ``UPLOAD_DIR`` remain valid.

*   ``s3`` — S3-compatible bucket (AWS S3, MinIO, Cloudflare R2, Wasabi, Ceph
    RGW). Writes go to the bucket over the async ``aioboto3`` client; reads are
    served via presigned GET URLs (or a CDN prefix when
    ``object_storage_public_base_url`` is configured).

Public API:

*   :func:`get_object_storage` — process-wide singleton selected via
    ``OBJECT_STORAGE_BACKEND``. Falls back to the FS backend automatically when
    the S3 backend is requested but its dependencies / configuration are
    missing (so a broken env var never takes the whole API down).
*   :class:`ObjectStorage` — the protocol every backend implements. Keep the
    surface small — ``save_stream`` / ``save_bytes`` for writes, ``public_url``
    / ``presigned_get_url`` / ``local_path`` for reads, ``exists`` / ``delete``
    for housekeeping.

The helper ``normalize_key`` guarantees a POSIX-style, no-leading-slash key so
callers can pass anything that used to go into ``os.path.join(...)``.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, AsyncIterator, BinaryIO, Optional, Protocol, Union

from backend.app.core.settings import settings

logger = logging.getLogger(__name__)

# 8 MiB stream chunks — same order of magnitude as the in-process upload loop
# (1 MiB) but larger to keep S3 multipart PUTs efficient.
_STREAM_CHUNK_BYTES = 8 * 1024 * 1024


def normalize_key(key: Union[str, os.PathLike[str]]) -> str:
    """Return a POSIX-style, no-leading-slash key.

    The key is the lingua franca between the FS and S3 backends — on FS it is
    the path relative to ``local_root``; on S3 it is the object key. Accepts
    ``str`` or ``PathLike`` and normalises Windows separators so the caller
    need not care.
    """
    raw = os.fspath(key).strip()
    if not raw:
        raise ValueError("Object storage key must not be empty")
    # Collapse backslashes (Windows paths passed through) then normalise via
    # PurePosixPath to strip ``.`` / ``..`` segments and duplicate slashes.
    posix = raw.replace("\\", "/").lstrip("/")
    cleaned = PurePosixPath(posix)
    if ".." in cleaned.parts:
        raise ValueError(f"Object storage key may not contain '..': {raw!r}")
    return cleaned.as_posix()


@dataclass(frozen=True)
class SavedObject:
    """Metadata returned by write operations. ``key`` is the canonical key;
    ``size`` is the byte count actually written (useful for quota calculations)."""

    key: str
    size: int
    content_type: Optional[str] = None


class ObjectStorage(Protocol):
    """The contract every storage backend satisfies.

    All methods are async to keep the FS and S3 backends interchangeable — the
    FS backend simply offloads blocking IO to a default executor.
    """

    backend_name: str

    async def save_stream(
        self,
        key: str,
        reader: "Union[BinaryIO, AsyncIterator[bytes]]",
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject: ...

    async def save_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject: ...

    async def exists(self, key: str) -> bool: ...

    async def delete(self, key: str) -> None: ...

    def local_path(self, key: str) -> Optional[Path]:
        """Return a filesystem path when the object lives on disk. S3 returns None."""

    def public_url(self, key: str) -> str:
        """URL safe to embed in API responses. May be a presigned URL for S3."""

    def presigned_get_url(
        self, key: str, *, expires_in: Optional[int] = None
    ) -> str:
        """Presigned GET URL; FS backend returns the same path as ``public_url``."""


# ---------------------------------------------------------------------------
# Filesystem backend (default — preserves pre-Phase-0 behaviour)
# ---------------------------------------------------------------------------


class FilesystemObjectStorage:
    """Drop-in backend that keeps the legacy ``UPLOAD_DIR`` layout."""

    backend_name = "fs"

    def __init__(self, root: Path, public_prefix: str = "/uploads") -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        # No trailing slash on the prefix; URLs look like f"{prefix}/{key}".
        self._public_prefix = public_prefix.rstrip("/")

    # -- writes ---------------------------------------------------------------

    async def save_stream(
        self,
        key: str,
        reader: "Union[BinaryIO, AsyncIterator[bytes]]",
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject:
        key = normalize_key(key)
        abs_path = self._resolve(key)
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        # Support both sync file-like and async iterators of bytes chunks.
        if hasattr(reader, "__aiter__"):
            with abs_path.open("wb") as fh:
                async for chunk in reader:  # type: ignore[union-attr]
                    if not chunk:
                        continue
                    fh.write(chunk)
                    total += len(chunk)
        else:
            # Offload the blocking read loop to the default executor.
            def _pump() -> int:
                bytes_written = 0
                with abs_path.open("wb") as fh:
                    while True:
                        chunk = reader.read(_STREAM_CHUNK_BYTES)  # type: ignore[union-attr]
                        if not chunk:
                            break
                        fh.write(chunk)
                        bytes_written += len(chunk)
                return bytes_written

            total = await asyncio.get_running_loop().run_in_executor(None, _pump)

        return SavedObject(key=key, size=total, content_type=content_type)

    async def save_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject:
        key = normalize_key(key)
        abs_path = self._resolve(key)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.get_running_loop().run_in_executor(
            None, abs_path.write_bytes, data
        )
        return SavedObject(key=key, size=len(data), content_type=content_type)

    # -- reads / housekeeping -------------------------------------------------

    async def exists(self, key: str) -> bool:
        abs_path = self._resolve(normalize_key(key))
        return await asyncio.get_running_loop().run_in_executor(
            None, abs_path.is_file
        )

    async def delete(self, key: str) -> None:
        abs_path = self._resolve(normalize_key(key))
        try:
            await asyncio.get_running_loop().run_in_executor(None, abs_path.unlink)
        except FileNotFoundError:
            return

    def local_path(self, key: str) -> Optional[Path]:
        if not key:
            # Convention: an empty key asks "where is the storage root?" —
            # used by the /uploads handler and code that iterates the tree.
            return self._root
        return self._resolve(normalize_key(key))

    def public_url(self, key: str) -> str:
        return f"{self._public_prefix}/{normalize_key(key)}"

    def presigned_get_url(
        self, key: str, *, expires_in: Optional[int] = None
    ) -> str:
        # FS has no expiring URLs — same as public_url.
        return self.public_url(key)

    # -- internals ------------------------------------------------------------

    def _resolve(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        # Defence in depth — normalize_key already rejects '..', but a symlink
        # inside the tree could still escape. Reject anything outside root.
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Resolved path escapes storage root: {candidate}") from exc
        return candidate


# ---------------------------------------------------------------------------
# S3 / MinIO backend
# ---------------------------------------------------------------------------


class S3ObjectStorage:
    """S3-compatible backend powered by ``aioboto3``.

    The bucket itself is expected to already exist (create it on deploy or via
    the migration script — we intentionally do not auto-create buckets on
    every request).
    """

    backend_name = "s3"

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        endpoint_url: Optional[str],
        access_key_id: Optional[str],
        secret_access_key: Optional[str],
        use_path_style: bool,
        presign_expires_sec: int,
        public_base_url: Optional[str],
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._use_path_style = use_path_style
        self._presign_expires_sec = presign_expires_sec
        self._public_base_url = (public_base_url or "").rstrip("/") or None

        # Import lazily so installs without aioboto3 (default) still work.
        import aioboto3  # type: ignore  # noqa: F401  (import for side-effect check)
        from botocore.config import Config as BotoConfig  # type: ignore

        self._session_factory = aioboto3.Session
        self._boto_config = BotoConfig(
            signature_version="s3v4",
            s3={"addressing_style": "path" if use_path_style else "virtual"},
            retries={"max_attempts": 3, "mode": "standard"},
        )

        # Synchronous botocore client for presign-URL generation (presigning is
        # pure-crypto / URL building and does not hit the network, so doing it
        # inside an async event loop with a sync client is cheap and keeps
        # `public_url` non-async — which matters: it is called from lots of
        # sync code paths building Document.files[].url).
        import boto3  # type: ignore

        self._sync_client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=self._boto_config,
        )

    # -- writes ---------------------------------------------------------------

    async def save_stream(
        self,
        key: str,
        reader: "Union[BinaryIO, AsyncIterator[bytes]]",
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject:
        key = normalize_key(key)

        # aioboto3's ``upload_fileobj`` handles multipart automatically for
        # large payloads — but it wants a sync file-like. For async iterators
        # we buffer into a temp file first (simpler than rolling our own
        # multipart upload for a Phase 0 skeleton).
        if hasattr(reader, "__aiter__"):
            import tempfile

            total = 0
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
                async for chunk in reader:  # type: ignore[union-attr]
                    if not chunk:
                        continue
                    tmp.write(chunk)
                    total += len(chunk)
            try:
                await self._upload_file(tmp_path, key, content_type=content_type)
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            return SavedObject(key=key, size=total, content_type=content_type)

        # Sync file-like: count bytes by rewinding + stat when possible,
        # otherwise reading through.
        pos_before: Optional[int]
        try:
            pos_before = reader.tell()  # type: ignore[union-attr]
        except Exception:
            pos_before = None

        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            extra: dict[str, Any] = {}
            if content_type:
                extra["ContentType"] = content_type
            await client.upload_fileobj(
                Fileobj=reader,  # type: ignore[arg-type]
                Bucket=self._bucket,
                Key=key,
                ExtraArgs=extra or None,
            )

        # Byte count: prefer the position delta if the underlying object is
        # seekable, fall back to a HEAD to get the final object size.
        size = 0
        try:
            pos_after = reader.tell()  # type: ignore[union-attr]
            if pos_before is not None and pos_after >= pos_before:
                size = pos_after - pos_before
        except Exception:
            pass
        if size == 0:
            size = await self._head_size(key)
        return SavedObject(key=key, size=size, content_type=content_type)

    async def save_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> SavedObject:
        key = normalize_key(key)
        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            extra_kwargs: dict[str, Any] = {}
            if content_type:
                extra_kwargs["ContentType"] = content_type
            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                **extra_kwargs,
            )
        return SavedObject(key=key, size=len(data), content_type=content_type)

    # -- reads / housekeeping -------------------------------------------------

    async def exists(self, key: str) -> bool:
        key = normalize_key(key)
        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            try:
                await client.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False

    async def delete(self, key: str) -> None:
        key = normalize_key(key)
        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            await client.delete_object(Bucket=self._bucket, Key=key)

    def local_path(self, key: str) -> Optional[Path]:
        return None  # S3 never exposes a local path.

    def public_url(self, key: str) -> str:
        key = normalize_key(key)
        if self._public_base_url:
            # CDN / public bucket — callers may cache this indefinitely.
            return f"{self._public_base_url}/{key}"
        # Default: hand out a short-lived presigned URL so private buckets
        # remain reachable without leaking raw object keys in the long run.
        return self.presigned_get_url(key)

    def presigned_get_url(
        self, key: str, *, expires_in: Optional[int] = None
    ) -> str:
        key = normalize_key(key)
        ttl = expires_in if expires_in is not None else self._presign_expires_sec
        return self._sync_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=ttl,
        )

    # -- internals ------------------------------------------------------------

    async def _upload_file(
        self,
        path: Path,
        key: str,
        *,
        content_type: Optional[str],
    ) -> None:
        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            extra: dict[str, Any] = {}
            if content_type:
                extra["ContentType"] = content_type
            await client.upload_file(
                Filename=str(path),
                Bucket=self._bucket,
                Key=key,
                ExtraArgs=extra or None,
            )

    async def _head_size(self, key: str) -> int:
        async with self._session_factory().client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            config=self._boto_config,
        ) as client:
            try:
                head = await client.head_object(Bucket=self._bucket, Key=key)
                return int(head.get("ContentLength", 0))
            except Exception:
                return 0


# ---------------------------------------------------------------------------
# Factory / singleton
# ---------------------------------------------------------------------------


_cached_storage: Optional[ObjectStorage] = None


def _fs_backend() -> FilesystemObjectStorage:
    root_env = os.environ.get("UPLOAD_DIR")
    if root_env:
        root = Path(root_env)
    else:
        # Same default as app.main / modules.documents.storage.
        root = Path(__file__).resolve().parents[2] / "uploads"
    return FilesystemObjectStorage(root=root)


def _build_s3_backend() -> Optional[S3ObjectStorage]:
    bucket = settings.object_storage_bucket
    if not bucket:
        logger.warning(
            "[object_storage] OBJECT_STORAGE_BACKEND=s3 requested but "
            "OBJECT_STORAGE_BUCKET is empty — falling back to filesystem backend."
        )
        return None
    try:
        return S3ObjectStorage(
            bucket=bucket,
            region=settings.object_storage_region,
            endpoint_url=settings.object_storage_endpoint_url,
            access_key_id=settings.object_storage_access_key_id,
            secret_access_key=settings.object_storage_secret_access_key,
            use_path_style=settings.object_storage_use_path_style,
            presign_expires_sec=settings.object_storage_presign_expires_sec,
            public_base_url=settings.object_storage_public_base_url,
        )
    except ImportError as exc:
        logger.warning(
            "[object_storage] S3 backend requested but aioboto3/boto3 not installed "
            "(%s) — falling back to filesystem backend.",
            exc,
        )
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[object_storage] Failed to initialise S3 backend: %s", exc)
        return None


def get_object_storage() -> ObjectStorage:
    """Return the process-wide storage backend, lazily initialised.

    The selection honours ``settings.object_storage_backend`` at first call
    time and is then cached. Tests can call :func:`reset_object_storage` to
    force re-initialisation between cases.
    """
    global _cached_storage
    if _cached_storage is not None:
        return _cached_storage

    backend = (settings.object_storage_backend or "fs").lower().strip()
    if backend == "s3":
        s3 = _build_s3_backend()
        if s3 is not None:
            _cached_storage = s3
            logger.info(
                "[object_storage] initialised S3 backend bucket=%s endpoint=%s",
                settings.object_storage_bucket,
                settings.object_storage_endpoint_url or "<aws-default>",
            )
            return s3

    _cached_storage = _fs_backend()
    logger.info(
        "[object_storage] initialised filesystem backend root=%s",
        _cached_storage.local_path("") or "<unknown>",
    )
    return _cached_storage


def reset_object_storage() -> None:
    """Drop the cached backend — for tests or a runtime reconfigure."""
    global _cached_storage
    _cached_storage = None


__all__ = [
    "FilesystemObjectStorage",
    "ObjectStorage",
    "S3ObjectStorage",
    "SavedObject",
    "get_object_storage",
    "normalize_key",
    "reset_object_storage",
]
