"""Read-model: trusted identity prep status per downstream consumer (PR8)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.employment_identity_projection import EXPIRY_ATTRS, PROJECTION_STATUS_STALE
from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_HR_REVIEW_DISPLAY,
    evaluate_consumer_access,
    get_trusted_employment_identity_for_employee,
)
from backend.app.services.workforce_downstream_identity import (
    CONSUMER_CLIENT_FORM,
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_EXPORT,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_PERMIT_APPLICATION,
    CONSUMER_ZUS_PREPARATION,
    evaluate_client_form_identity,
    evaluate_contract_merge_identity,
    evaluate_export_identity,
    evaluate_payroll_preparation,
    evaluate_permit_application,
    evaluate_zus_preparation,
)

PREP_STATUS_CONSUMERS: tuple[str, ...] = (
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_ZUS_PREPARATION,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_PERMIT_APPLICATION,
    CONSUMER_EXPORT,
    CONSUMER_CLIENT_FORM,
)

_CONSUMER_EVALUATORS = {
    CONSUMER_CONTRACT_GENERATION: evaluate_contract_merge_identity,
    CONSUMER_ZUS_PREPARATION: evaluate_zus_preparation,
    CONSUMER_PAYROLL_PREP: evaluate_payroll_preparation,
    CONSUMER_PERMIT_APPLICATION: evaluate_permit_application,
    CONSUMER_EXPORT: evaluate_export_identity,
    CONSUMER_CLIENT_FORM: evaluate_client_form_identity,
}


def _stale_field_codes(projection: dict[str, Any]) -> list[str]:
    if str(projection.get("status") or "") != PROJECTION_STATUS_STALE:
        return []
    attrs = projection.get("attributes") if isinstance(projection.get("attributes"), dict) else {}
    return [code for code in sorted(EXPIRY_ATTRS) if attrs.get(code)]


async def build_trusted_identity_prep_status(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
) -> dict[str, Any]:
    display = await get_trusted_employment_identity_for_employee(
        db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        consumer=CONSUMER_HR_REVIEW_DISPLAY,
        raise_on_denied=False,
    )
    projection = display.projection
    status = str(projection.get("status") or "")
    attrs = projection.get("attributes") if isinstance(projection.get("attributes"), dict) else {}
    labels = projection.get("attribute_labels") if isinstance(projection.get("attribute_labels"), dict) else {}

    allowed_consumers: list[str] = []
    blocked_consumers: list[dict[str, Any]] = []
    consumer_details: list[dict[str, Any]] = []

    for consumer in PREP_STATUS_CONSUMERS:
        ok, code = evaluate_consumer_access(consumer, status)
        evaluator = _CONSUMER_EVALUATORS.get(consumer)
        prep = await evaluator(db, tenant_id, employee_id) if evaluator else None
        detail: dict[str, Any] = {
            "consumer": consumer,
            "allowed": ok,
            "block_code": code,
            "ready": bool(prep and prep.ready),
            "projection_status": status,
        }
        if prep and prep.bindings:
            detail["binding_keys"] = sorted(prep.bindings.keys())
        consumer_details.append(detail)
        if ok:
            allowed_consumers.append(consumer)
        else:
            blocked_consumers.append({"consumer": consumer, "block_code": code})

    return {
        "employee_id": employee_id,
        "review_id": display.review_id,
        "projection_status": status,
        "derived_at": projection.get("derived_at"),
        "attributes": attrs,
        "allowed_consumers": allowed_consumers,
        "blocked_consumers": blocked_consumers,
        "consumers": consumer_details,
        "missing_fields": [labels.get(c) or c for c in (projection.get("missing_required") or [])],
        "missing_field_codes": list(projection.get("missing_required") or []),
        "conflicted_fields": [labels.get(c) or c for c in (projection.get("conflicts") or [])],
        "conflicted_field_codes": list(projection.get("conflicts") or []),
        "stale_fields": _stale_field_codes(projection),
        "ready_for_downstream": bool(projection.get("ready_for_downstream")),
    }
