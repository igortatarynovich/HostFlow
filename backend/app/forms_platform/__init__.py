"""Forms platform package — ADR-007 / Sprint 1–2 Adapter surface."""

from __future__ import annotations

from backend.app.forms_platform.adapter import (
    FORMS_ADAPTER_ID,
    FORMS_PUBLIC_CONTRACT_ID,
    activate_endpoint,
    adapter_identity,
    assert_submission_version_compatible,
    commit_publish,
    deactivate_endpoint,
    endpoint_from_publication,
    publish,
    resolve_endpoint,
    resolve_publication,
    result_handoff,
    submission_entry,
)

__all__ = [
    "FORMS_ADAPTER_ID",
    "FORMS_PUBLIC_CONTRACT_ID",
    "activate_endpoint",
    "adapter_identity",
    "assert_submission_version_compatible",
    "commit_publish",
    "deactivate_endpoint",
    "endpoint_from_publication",
    "publish",
    "resolve_endpoint",
    "resolve_publication",
    "result_handoff",
    "submission_entry",
]
