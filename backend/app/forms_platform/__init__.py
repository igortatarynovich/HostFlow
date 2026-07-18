"""Forms platform package — ADR-007 / Sprint 1 Adapter surface."""

from __future__ import annotations

from backend.app.forms_platform.adapter import (
    FORMS_ADAPTER_ID,
    FORMS_PUBLIC_CONTRACT_ID,
    adapter_identity,
    endpoint_from_publication,
    publish,
    resolve_endpoint,
    result_handoff,
    submission_entry,
)

__all__ = [
    "FORMS_ADAPTER_ID",
    "FORMS_PUBLIC_CONTRACT_ID",
    "adapter_identity",
    "endpoint_from_publication",
    "publish",
    "resolve_endpoint",
    "result_handoff",
    "submission_entry",
]
