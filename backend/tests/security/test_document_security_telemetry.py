"""Document / signed URL security telemetry (v1) and redaction."""

from __future__ import annotations

import pytest

from backend.app.security.document_events import (
    DOCUMENT_EVENT_EXTRA_ALLOWLIST,
    emit_document_security_event_v1,
    url_looks_presigned,
)
from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.event_taxonomy import (
    EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
    EVENT_DOCUMENT_FILE_DOWNLOADED,
    EVENT_DOCUMENT_METADATA_READ,
    EVENT_DOCUMENT_SIGNED_URL_DENIED,
    EVENT_DOCUMENT_SIGNED_URL_EXPIRED,
    EVENT_DOCUMENT_SIGNED_URL_GENERATED,
    EVENT_DOCUMENT_SIGNED_URL_REPLAY_DENIED,
    validate_event_type,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://bucket.s3.amazonaws.com/x?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=abc", True),
        ("https://storage.googleapis.com/o?X-Goog-Signature=x", True),
        ("/uploads/documents/1/file.pdf", False),
        ("https://cdn.example.com/static/logo.png", False),
    ],
)
def test_url_looks_presigned(url: str, expected: bool) -> None:
    assert url_looks_presigned(url) is expected


def test_document_event_types_validate() -> None:
    for et in (
        EVENT_DOCUMENT_METADATA_READ,
        EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
        EVENT_DOCUMENT_FILE_DOWNLOADED,
        EVENT_DOCUMENT_SIGNED_URL_GENERATED,
        EVENT_DOCUMENT_SIGNED_URL_DENIED,
        EVENT_DOCUMENT_SIGNED_URL_EXPIRED,
        EVENT_DOCUMENT_SIGNED_URL_REPLAY_DENIED,
    ):
        assert validate_event_type(et) == et


def test_emit_document_security_event_v1_allowlist() -> None:
    p = emit_document_security_event_v1(
        event_type=EVENT_DOCUMENT_SIGNED_URL_GENERATED,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        document_id="22222222-2222-2222-2222-222222222222",
        access_kind="tenant_bound",
        document_class="passport",
        candidate_id="33333333-3333-3333-3333-333333333333",
        upload_presign=True,
    )
    assert p["event_type"] == EVENT_DOCUMENT_SIGNED_URL_GENERATED
    assert p["entity_type"] == "document"
    assert p["extra"]["document_class"] == "passport"
    assert p["extra"]["upload_presign"] is True
    assert "url" not in p["extra"]


def test_redaction_filename_and_url_keys_even_if_allowlisted() -> None:
    out = redact_and_size_extra(
        {
            "filename": "Иванов_Иван_паспорт.pdf",
            "signed_url": "https://x.example/?sig=1",
            "jwt_tenant_id": "ok",
        },
        allowlist=frozenset({"filename", "signed_url", "jwt_tenant_id"}),
    )
    assert out["jwt_tenant_id"] == "ok"
    assert out["filename"] == "[REDACTED]"
    assert out["signed_url"] == "[REDACTED]"


def test_redaction_scrubs_sensitive_url_in_allowlisted_value() -> None:
    out = redact_and_size_extra(
        {
            "reason": "https://evil.example/?X-Amz-Signature=deadbeef&X-Amz-Credential=x",
        },
        allowlist=frozenset({"reason"}),
    )
    assert out["reason"] == "[REDACTED_SENSITIVE_VALUE]"


def test_redaction_scrubs_token_like_string_in_allowlisted_value() -> None:
    out = redact_and_size_extra(
        {"reason": "https://api.example/cb#access_token=ya29.secretbit"},
        allowlist=frozenset({"reason"}),
    )
    assert out["reason"] == "[REDACTED_SENSITIVE_VALUE]"


def test_document_extra_allowlist_is_closed() -> None:
    assert "url" not in DOCUMENT_EVENT_EXTRA_ALLOWLIST
    assert "filename" not in DOCUMENT_EVENT_EXTRA_ALLOWLIST
