"""Forms platform package — ADR-007 / Sprint 1–6 Adapter surface."""

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
    get_submission,
    get_version_for_audit,
    list_submissions,
    list_versions_for_audit,
    persist_submission,
    pin_submission_to_publication_version,
    publish,
    resolve_endpoint,
    resolve_publication,
    result_handoff,
    set_submission_status,
    submission_entry,
)
from backend.app.forms_platform.answers import (
    ANSWER_CONTRACT,
    build_normalized_answers,
)
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    build_field_schema_v1,
    extract_field_schema,
)
from backend.app.forms_platform.validation import (
    shared_intake_payload_from_answers,
    validate_submission,
    validate_submission_against_publication,
)

__all__ = [
    "ANSWER_CONTRACT",
    "FIELD_SCHEMA_CONTRACT",
    "FORMS_ADAPTER_ID",
    "FORMS_PUBLIC_CONTRACT_ID",
    "activate_endpoint",
    "adapter_identity",
    "assert_submission_version_compatible",
    "build_field_schema_v1",
    "build_normalized_answers",
    "commit_publish",
    "deactivate_endpoint",
    "endpoint_from_publication",
    "extract_field_schema",
    "get_submission",
    "get_version_for_audit",
    "list_submissions",
    "list_versions_for_audit",
    "persist_submission",
    "pin_submission_to_publication_version",
    "publish",
    "resolve_endpoint",
    "resolve_publication",
    "result_handoff",
    "set_submission_status",
    "shared_intake_payload_from_answers",
    "submission_entry",
    "validate_submission",
    "validate_submission_against_publication",
]
