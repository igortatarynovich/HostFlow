"""Phase 0 #6: ensure documents.storage URL/path helpers go through the
object-storage abstraction so the S3 backend drop-in works without patching
every call-site."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from backend.app.core import object_storage as os_mod
from backend.app.modules.documents import storage as docs_storage


class _StubS3Backend:
    """Minimal stub so we do not need live MinIO for URL-contract tests."""

    backend_name = "s3"

    def local_path(self, key: str) -> Optional[Path]:
        return None

    def public_url(self, key: str) -> str:
        return f"https://example.invalid/{key}?sig=fake"

    def presigned_get_url(self, key: str, *, expires_in=None) -> str:
        return self.public_url(key)


@pytest.fixture(autouse=True)
def _reset_backend_cache():
    os_mod.reset_object_storage()
    yield
    os_mod.reset_object_storage()


def test_build_public_url_fs_returns_uploads_prefix(monkeypatch, tmp_path):
    monkeypatch.setattr(
        os_mod, "_cached_storage", os_mod.FilesystemObjectStorage(root=tmp_path)
    )
    assert docs_storage._build_public_url("docs/1/file.pdf") == "/uploads/docs/1/file.pdf"


def test_build_public_url_s3_returns_presigned(monkeypatch):
    monkeypatch.setattr(os_mod, "_cached_storage", _StubS3Backend())
    url = docs_storage._build_public_url("docs/1/file.pdf")
    assert url.startswith("https://example.invalid/docs/1/file.pdf?")


def test_extract_storage_key_prefers_storage_path():
    assert docs_storage.extract_storage_key({"storage_path": "a/b.pdf"}) == "a/b.pdf"
    assert docs_storage.extract_storage_key({"url": "/uploads/x/y.pdf"}) == "x/y.pdf"
    assert docs_storage.extract_storage_key({"url": "https://cdn.example/q"}) is None
    assert docs_storage.extract_storage_key({}) is None


def test_file_entry_download_url_uses_backend(monkeypatch):
    monkeypatch.setattr(os_mod, "_cached_storage", _StubS3Backend())
    url = docs_storage.file_entry_download_url({"storage_path": "tenant/doc.pdf"})
    assert url == "https://example.invalid/tenant/doc.pdf?sig=fake"


def test_resolve_file_path_rejects_non_fs_backend(monkeypatch):
    monkeypatch.setattr(os_mod, "_cached_storage", _StubS3Backend())
    with pytest.raises(ValueError, match="local filesystem"):
        docs_storage.resolve_file_path({"storage_path": "doc.pdf"})
