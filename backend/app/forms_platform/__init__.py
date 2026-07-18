"""Forms platform package — ADR-007 / Sprint 1–3 Adapter surface."""

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
    get_version_for_audit,
    list_versions_for_audit,
    pin_submission_to_publication_version,
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
    "get_version_for_audit",
    "list_versions_for_audit",
    "pin_submission_to_publication_version",
    "publish",
    "resolve_endpoint",
    "resolve_publication",
    "result_handoff",
    "submission_entry",
]
