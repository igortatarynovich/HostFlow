"""Stabilization: document + export security ``extra`` redaction (shared sensitive keys)."""

from __future__ import annotations

from backend.app.security.document_events import DOCUMENT_EVENT_EXTRA_ALLOWLIST
from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.export_events import EXPORT_EVENT_EXTRA_ALLOWLIST


def test_document_extra_misused_sensitive_keys_are_redacted() -> None:
    """Simulate buggy producer: keys accidentally on allowlist → scrub must still redact."""
    allow = DOCUMENT_EVENT_EXTRA_ALLOWLIST | frozenset(
        {"signed_url", "download_url", "filename", "url", "access_token"}
    )
    out = redact_and_size_extra(
        {
            "document_class": "passport",
            "signed_url": "https://evil/?X-Amz-Signature=1",
            "download_url": "https://x/",
            "filename": "Иванов_passport.pdf",
            "url": "https://y/",
            "access_token": "ya29.secret",
        },
        allowlist=allow,
    )
    assert out["document_class"] == "passport"
    assert out["signed_url"] == "[REDACTED]"
    assert out["download_url"] == "[REDACTED]"
    assert out["filename"] == "[REDACTED]"
    assert out["url"] == "[REDACTED]"
    assert out["access_token"] == "[REDACTED]"


def test_export_extra_misused_sensitive_keys_are_redacted() -> None:
    allow = EXPORT_EVENT_EXTRA_ALLOWLIST | frozenset(
        {"rows", "archive_path", "export_path", "attachment_filename", "signed_url"}
    )
    out = redact_and_size_extra(
        {
            "export_type": "candidate_documents_csv",
            "row_count": 2,
            "byte_size": 100,
            "rows": [{"id": "x"}],
            "archive_path": "/data/secret.zip",
            "export_path": "/tmp/out.zip",
            "attachment_filename": "pii.csv",
            "signed_url": "https://cdn/x?token=abc",
        },
        allowlist=allow,
    )
    assert out["export_type"] == "candidate_documents_csv"
    assert out["row_count"] == 2
    assert out["byte_size"] == 100
    assert out["rows"] == "[REDACTED]"
    assert out["archive_path"] == "[REDACTED]"
    assert out["export_path"] == "[REDACTED]"
    assert out["attachment_filename"] == "[REDACTED]"
    assert out["signed_url"] == "[REDACTED]"
