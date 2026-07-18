"""Forms platform package — ADR-007 / Sprint 1–4 Adapter surface."""

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
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    build_field_schema_v1,
    extract_field_schema,
)
from backend.app.forms_platform.validation import (
    validate_submission,
    validate_submission_against_publication,
)

__all__ = [
    "FIELD_SCHEMA_CONTRACT",
    "FORMS_ADAPTER_ID",
    "FORMS_PUBLIC_CONTRACT_ID",
    "activate_endpoint",
    "adapter_identity",
    "assert_submission_version_compatible",
    "build_field_schema_v1",
    "commit_publish",
    "deactivate_endpoint",
    "endpoint_from_publication",
    "extract_field_schema",
    "get_version_for_audit",
    "list_versions_for_audit",
    "pin_submission_to_publication_version",
    "publish",
    "resolve_endpoint",
    "resolve_publication",
    "result_handoff",
    "submission_entry",
    "validate_submission",
    "validate_submission_against_publication",
]
