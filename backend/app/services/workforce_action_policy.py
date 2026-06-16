from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.audit import log_activity
from backend.app.services.workforce_eligibility_delivery_contract import (
    WorkforceEligibilityContext,
    resolve_workforce_eligibility_via_contract,
)


@dataclass
class WorkforceActionBlockedError(Exception):
    operation: str
    eligibility_status: str
    reasons: list[dict]

    def __str__(self) -> str:
        return "WORKFORCE_ACTION_BLOCKED"


def _candidate_ctx(c: Candidate | None) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    if c is None:
        return None, None, None, None
    extra = c._get_extra() if hasattr(c, "_get_extra") else {}
    personal = c._get_personal_data() if hasattr(c, "_get_personal_data") else {}
    citizenship = str(extra.get("citizenship") or personal.get("citizenship") or "").strip() or None
    work_country = str(extra.get("work_country") or personal.get("work_country") or "").strip() or None
    residence_status = str(extra.get("legal_status") or extra.get("residency_status") or personal.get("residency_status") or "").strip() or None
    position_category = str(extra.get("position_category") or extra.get("profession_category") or "").strip() or None
    return citizenship, work_country, residence_status, position_category


async def assert_operation_allowed(
    db: AsyncSession,
    *,
    tenant_id: str,
    operation: str,
    actor_id: str | None = None,
    employee: WorkforceEmployee | None = None,
    candidate: Candidate | None = None,
    stage: str | None = None,
) -> dict:
    cid = str(candidate.id) if candidate is not None else (str(employee.candidate_id) if employee and employee.candidate_id else None)
    eid = str(employee.id) if employee is not None else None

    citizenship, work_country, residence_status, position_category = _candidate_ctx(candidate)
    if employee is not None and isinstance(employee.candidate_snapshot, dict):
        snap = employee.candidate_snapshot
        citizenship = citizenship or str(snap.get("citizenship") or "").strip() or None
        work_country = work_country or str(snap.get("work_country") or "").strip() or None
        residence_status = residence_status or str(snap.get("legal_status") or "").strip() or None
        position_category = position_category or str(snap.get("position_category") or "").strip() or None

    runtime = await resolve_workforce_eligibility_via_contract(
        db,
        context=WorkforceEligibilityContext(
            tenant_id=str(tenant_id),
            candidate_id=cid,
            employee_id=eid,
            citizenship=citizenship,
            work_country=work_country,
            residence_status=residence_status,
            position_category=position_category,
            stage=stage,
        ),
    )

    allowed = bool((runtime.get("allowed_operations") or {}).get(operation, True))
    payload = {
        "result": "allowed" if allowed else "blocked",
        "operation": operation,
        "eligibility_status": runtime.get("eligibility_status"),
        "compliance_status": runtime.get("compliance_status"),
        "blocking_reasons": list(runtime.get("blocking_reasons") or []),
        "warnings": list(runtime.get("warnings") or []),
        "readiness_profiles": dict(runtime.get("readiness_profiles") or {}),
        "candidate_id": cid,
        "employee_id": eid,
        "stage": stage,
    }
    await log_activity(
        db,
        tenant_id=str(tenant_id),
        actor_id=(str(actor_id).strip() or None) if actor_id else None,
        action="workforce.action.decision_event",
        target_type="workforce_operation",
        target_id=eid or cid,
        payload=payload,
    )

    if not allowed:
        raise WorkforceActionBlockedError(
            operation=operation,
            eligibility_status=str(runtime.get("eligibility_status") or "blocked"),
            reasons=list(runtime.get("blocking_reasons") or []),
        )
    return runtime
