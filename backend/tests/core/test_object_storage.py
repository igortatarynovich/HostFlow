"""Phase 0 #6: object storage abstraction (FS backend + factory semantics).

The S3 backend is exercised end-to-end by the migration-script test and
(optionally) against a live MinIO. Here we stick to the FS backend so tests
are fully hermetic and fast.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.app.core import object_storage as os_mod


@pytest.fixture(autouse=True)
def _reset_backend_cache():
    os_mod.reset_object_storage()
    yield
    os_mod.reset_object_storage()


@pytest.fixture
def fs_backend(tmp_path: Path) -> os_mod.FilesystemObjectStorage:
    return os_mod.FilesystemObjectStorage(root=tmp_path)


def test_normalize_key_strips_leading_slash_and_backslash():
    assert os_mod.normalize_key("/foo/bar.txt") == "foo/bar.txt"
    assert os_mod.normalize_key("foo\\bar\\baz.txt") == "foo/bar/baz.txt"
    assert os_mod.normalize_key("foo//bar") == "foo/bar"


def test_normalize_key_rejects_empty_and_dotdot():
    with pytest.raises(ValueError):
        os_mod.normalize_key("")
    with pytest.raises(ValueError):
        os_mod.normalize_key("../etc/passwd")
    with pytest.raises(ValueError):
        os_mod.normalize_key("foo/../../bar")


@pytest.mark.anyio
async def test_fs_save_bytes_roundtrip(fs_backend: os_mod.FilesystemObjectStorage):
    saved = await fs_backend.save_bytes("docs/1.txt", b"hello")
    assert saved.key == "docs/1.txt"
    assert saved.size == 5
    assert await fs_backend.exists("docs/1.txt")
    path = fs_backend.local_path("docs/1.txt")
    assert path is not None and path.read_bytes() == b"hello"


@pytest.mark.anyio
async def test_fs_save_stream_from_sync_fileobj(
    fs_backend: os_mod.FilesystemObjectStorage, tmp_path: Path
):
    src = tmp_path / "src.bin"
    src.write_bytes(b"ABCDE" * 1000)
    with src.open("rb") as fh:
        saved = await fs_backend.save_stream(
            "bin/data.bin", fh, content_type="application/octet-stream"
        )
    assert saved.size == 5000
    assert saved.content_type == "application/octet-stream"
    path = fs_backend.local_path("bin/data.bin")
    assert path is not None and path.stat().st_size == 5000


@pytest.mark.anyio
async def test_fs_save_stream_from_async_iter(
    fs_backend: os_mod.FilesystemObjectStorage,
):
    async def chunks():
        yield b"abc"
        yield b"defg"
        yield b""  # empty chunks must not crash

    saved = await fs_backend.save_stream("async/a.bin", chunks())
    assert saved.size == 7
    path = fs_backend.local_path("async/a.bin")
    assert path is not None and path.read_bytes() == b"abcdefg"


@pytest.mark.anyio
async def test_fs_delete(fs_backend: os_mod.FilesystemObjectStorage):
    await fs_backend.save_bytes("to/delete.txt", b"x")
    assert await fs_backend.exists("to/delete.txt")
    await fs_backend.delete("to/delete.txt")
    assert not await fs_backend.exists("to/delete.txt")
    # deleting a missing key is a no-op
    await fs_backend.delete("to/delete.txt")


def test_fs_public_url_is_relative(fs_backend: os_mod.FilesystemObjectStorage):
    assert fs_backend.public_url("/a/b.txt") == "/uploads/a/b.txt"
    # presigned == public for FS
    assert fs_backend.presigned_get_url("a/b.txt") == "/uploads/a/b.txt"


def test_get_object_storage_defaults_to_fs(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(os_mod.settings, "object_storage_backend", "fs", raising=False)
    backend = os_mod.get_object_storage()
    assert isinstance(backend, os_mod.FilesystemObjectStorage)
    assert backend.local_path("") == tmp_path.resolve()


def test_get_object_storage_falls_back_to_fs_when_s3_misconfigured(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(os_mod.settings, "object_storage_backend", "s3", raising=False)
    monkeypatch.setattr(os_mod.settings, "object_storage_bucket", None, raising=False)
    # Missing bucket → FS fallback with a warning, not an exception.
    backend = os_mod.get_object_storage()
    assert isinstance(backend, os_mod.FilesystemObjectStorage)


def test_fs_resolve_refuses_path_escape(fs_backend: os_mod.FilesystemObjectStorage):
    # normalize_key guards the happy path; this covers raw _resolve defense.
    with pytest.raises(ValueError):
        fs_backend._resolve("../escape.txt")
