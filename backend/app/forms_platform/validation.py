"""Forms Sprint 4–5 — submission validation + normalized answers.

Pure functions. No dynamic code execution. No Builder. No domain mapping.
"""

from __future__ import annotations

from typing import Any

from backend.app.forms_platform.answers import (
    ANSWER_CONTRACT,
    build_normalized_answers,
)
from backend.app.forms_platform.errors import FormsAdapterError
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    LEGACY_PAYLOAD_KEYS,
    extract_field_schema,
)


class FormsValidationError(FormsAdapterError):
    code = "forms_submission_validation_failed"
    http_status = 422
    default_message = "Submission failed field schema validation"


def normalize_submission_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extract flat raw field map from intake-shaped payload (pre-canonicalization)."""
    raw = dict(payload or {})
    if isinstance(raw.get("values"), dict):
        values = dict(raw["values"])
    else:
        values = {
            str(k): v
            for k, v in raw.items()
            if str(k) not in LEGACY_PAYLOAD_KEYS and str(k) != "presentation_values_v1"
        }
        pv = raw.get("presentation_values_v1")
        if isinstance(pv, dict):
            values = {**values, **{str(k): v for k, v in pv.items()}}
    return {str(k).strip(): v for k, v in values.items() if str(k).strip()}


def validate_submission(
    schema: dict[str, Any] | None,
    payload: dict[str, Any] | None,
    *,
    published_version: int | None = None,
    form_id: str | None = None,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Validate + normalize payload → forms.normalized_answers.v1 (+ Sprint 4 keys)."""
    raw_values = normalize_submission_payload(payload)
    answer = build_normalized_answers(
        schema=schema,
        raw_values=raw_values,
        published_version=published_version,
        form_id=form_id,
        schema_contract=(
            FIELD_SCHEMA_CONTRACT
            if schema and schema.get("schema_contract") == FIELD_SCHEMA_CONTRACT
            else None
        ),
    )
    # Sprint 4-compatible top-level keys retained.
    result = {
        **answer,
        "answer_contract": ANSWER_CONTRACT,
        "schema_contract": answer.get("schema_contract"),
        "compat_mode": answer.get("compat_mode"),
        "published_version": published_version,
        "normalized_values": answer.get("normalized_values") or {},
        "raw_values": answer.get("raw_values") or {},
        "errors": answer.get("errors") or [],
        "ok": bool(answer.get("ok")),
        "intake_handoff": answer.get("intake_handoff") or {},
    }
    if raise_on_error and not result["ok"]:
        raise FormsValidationError(
            details={
                "errors": result["errors"],
                "published_version": published_version,
                "form_id": form_id,
                "answer_contract": ANSWER_CONTRACT,
            }
        )
    return result


def validate_submission_against_publication(
    publication_or_snapshot: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    schema = extract_field_schema(publication_or_snapshot)
    version = publication_or_snapshot.get("published_version")
    if version is None and isinstance(publication_or_snapshot.get("snapshot"), dict):
        version = publication_or_snapshot["snapshot"].get("published_version")
    form_id = publication_or_snapshot.get("publication_id") or publication_or_snapshot.get(
        "form_id"
    )
    if form_id is None and isinstance(publication_or_snapshot.get("snapshot"), dict):
        form_id = publication_or_snapshot.get("form_id")
    return validate_submission(
        schema,
        payload,
        published_version=int(version) if version is not None else None,
        form_id=str(form_id) if form_id else None,
        raise_on_error=raise_on_error,
    )


def shared_intake_payload_from_answers(answer: dict[str, Any]) -> dict[str, Any]:
    """Map normalized answers → Shared Intake fragment (no domain mapping)."""
    handoff = answer.get("intake_handoff") if isinstance(answer.get("intake_handoff"), dict) else {}
    if handoff:
        return dict(handoff)
    return {
        "presentation_values_v1": dict(answer.get("normalized_values") or {}),
        "forms_answer_contract_v1": {
            "answer_contract": ANSWER_CONTRACT,
            "schema_contract": answer.get("schema_contract"),
            "published_version": answer.get("published_version"),
            "form_id": answer.get("form_id"),
            "ok": answer.get("ok"),
        },
        "forms_raw_values_v1": dict(answer.get("raw_values") or {}),
    }
