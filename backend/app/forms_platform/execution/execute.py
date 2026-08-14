"""Forms Platform C5 — Form Execution (submit contract).

Binds existing validate / pin / Shared Intake persist to Runtime Model.
Does not invent a second Forms submit HTTP surface.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.constants import LIFECYCLE_ARCHIVED
from backend.app.forms_platform.contract_identity import (
    parse_contract_identity,
    verify_identity_against_schema,
)
from backend.app.forms_platform.errors import (
    FormsArchivedError,
    FormsExecutionRequiresRuntimeModelError,
    FormsIdentityIncompleteError,
    FormsInactiveError,
)
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT, RuntimeModel
from backend.app.forms_platform.submission_envelope import persist_submission_envelope
from backend.app.forms_platform.validation import validate_submission

PUBLIC_INTAKE_PATH = "/api/v1/public/intake"


def _require_runtime_model(model: object) -> RuntimeModel:
    if not isinstance(model, RuntimeModel):
        raise FormsExecutionRequiresRuntimeModelError(
            details={"reason": "runtime_model_required", "got": type(model).__name__}
        )
    if model.contract != RUNTIME_MODEL_CONTRACT:
        raise FormsExecutionRequiresRuntimeModelError(
            details={
                "reason": "runtime_model_contract_mismatch",
                "contract": model.contract,
                "expected": RUNTIME_MODEL_CONTRACT,
            }
        )
    return model


def _require_executable(model: RuntimeModel) -> None:
    """Fail-closed before validate/persist. Does not re-mint identity."""
    raw_identity = dict(model.contract_identity) if model.contract_identity else None
    if not raw_identity:
        raise FormsIdentityIncompleteError(
            details={"reason": "execution_requires_frozen_identity"}
        )
    field_schema = dict(model.field_schema) if model.field_schema else None
    if not field_schema:
        raise FormsIdentityIncompleteError(
            details={"reason": "execution_requires_frozen_schema"}
        )
    identity = parse_contract_identity(raw_identity)
    verify_identity_against_schema(identity, field_schema)

    if str(model.lifecycle_status) == LIFECYCLE_ARCHIVED:
        raise FormsArchivedError(
            details={"form_id": model.form_id, "lifecycle_status": model.lifecycle_status}
        )
    if not model.is_active:
        raise FormsInactiveError(
            details={"form_id": model.form_id, "is_active": False}
        )


def submission_pin(model: RuntimeModel) -> dict[str, Any]:
    """Pin + Shared Intake path from Runtime Model (not a second submit engine)."""
    model = _require_runtime_model(model)
    _require_executable(model)
    return {
        "forms_role": "submission_surface",
        "public_intake_path": PUBLIC_INTAKE_PATH,
        "form_id": model.form_id,
        "published_version": int(model.published_version),
        "publication_version_pin": {
            "form_id": model.form_id,
            "version": int(model.published_version),
        },
        "contract_identity": dict(model.contract_identity),
        "consent_pin": dict(model.consent_pin),
        "answer_contract": "forms.normalized_answers.v1",
        "field_schema_contract": dict(model.field_schema).get("schema_contract"),
    }


def validate_against_runtime_model(
    model: RuntimeModel,
    payload: dict[str, Any] | None,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Validate payload against Runtime Model field_schema only."""
    model = _require_runtime_model(model)
    _require_executable(model)
    return validate_submission(
        dict(model.field_schema),
        payload,
        published_version=int(model.published_version),
        form_id=str(model.form_id),
        raise_on_error=raise_on_error,
    )


def execute_submission(
    model: RuntimeModel,
    payload: dict[str, Any] | None,
    *,
    raise_on_error: bool = False,
) -> dict[str, Any]:
    """Runtime Model → Validation → Submission pin (no persist, no Builder)."""
    answer = validate_against_runtime_model(
        model, payload, raise_on_error=raise_on_error
    )
    pin = submission_pin(model)
    return {
        "answer": answer,
        "submission_pin": pin,
        "public_intake_path": PUBLIC_INTAKE_PATH,
        "contract_identity": dict(model.contract_identity),
        "form_id": model.form_id,
        "published_version": int(model.published_version),
        "ok": bool(answer.get("ok")),
    }


async def persist_execution(
    db: AsyncSession,
    *,
    tenant_id: str,
    model: RuntimeModel,
    payload: dict[str, Any] | None,
    idempotency_key: str | None = None,
    raise_on_error: bool = False,
    pin_publication_version: bool = True,
) -> dict[str, Any]:
    """Validate against Runtime Model then persist via Shared Intake envelope path."""
    executed = execute_submission(model, payload, raise_on_error=raise_on_error)
    answer = dict(executed["answer"])
    answer["published_version"] = int(model.published_version)
    answer["form_id"] = str(model.form_id)
    envelope = await persist_submission_envelope(
        db,
        tenant_id=tenant_id,
        form_id=str(model.form_id),
        answer=answer,
        idempotency_key=idempotency_key,
        pin_publication_version=pin_publication_version,
    )
    return {
        **executed,
        "envelope": envelope,
    }
