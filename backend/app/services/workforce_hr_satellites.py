from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_absence import WorkforceAbsence
from backend.app.models.workforce_employment import WorkforceEmployment
from backend.app.models.workforce_leave_request import WorkforceLeaveRequest
from backend.app.models.workforce_onboarding_task import WorkforceOnboardingTask
from backend.app.models.workforce_payroll_profile import WorkforcePayrollProfile
from backend.app.models.workforce_zus_profile import WorkforceZusProfile
from backend.app.services.workforce_employees import ensure_hr_profiles_bundle, get_employee

PAYROLL_STATUSES = frozenset(
    {
        "missing_data",
        "ready_for_payroll",
        "sent_to_accounting",
        "settled",
        "correction_needed",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _touch(row: Any) -> None:
    row.updated_at = _now()


def _parse_decimal_str(raw: Optional[str]) -> Optional[Decimal]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


async def patch_payroll_profile(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforcePayrollProfile]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    await ensure_hr_profiles_bundle(db, tenant_id, employee_id)
    row = (
        await db.execute(
            select(WorkforcePayrollProfile).where(
                WorkforcePayrollProfile.tenant_id == tenant_id,
                WorkforcePayrollProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    data = dict(patch)
    if "base_rate" in data:
        row.base_rate = _parse_decimal_str(data.pop("base_rate"))  # type: ignore[assignment]
    for k, v in data.items():
        setattr(row, k, v)
    ps = (row.payroll_status or "").strip()
    if not ps or ps not in PAYROLL_STATUSES:
        row.payroll_status = "missing_data"
    _touch(row)
    await db.flush()
    return row


async def patch_zus_profile(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceZusProfile]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    await ensure_hr_profiles_bundle(db, tenant_id, employee_id)
    row = (
        await db.execute(
            select(WorkforceZusProfile).where(
                WorkforceZusProfile.tenant_id == tenant_id,
                WorkforceZusProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    for k, v in patch.items():
        setattr(row, k, v)
    _touch(row)
    await db.flush()
    return row


async def create_employment(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    payload: dict[str, Any],
) -> Optional[WorkforceEmployment]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    row = WorkforceEmployment(
        id=str(uuid4()),
        tenant_id=tenant_id,
        employee_id=employee_id,
        contract_type=str(payload.get("contract_type") or "unknown")[:64],
        rate_model=payload.get("rate_model"),
        schedule=payload.get("schedule"),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        conditions_text=payload.get("conditions_text"),
        vacancy_id=payload.get("vacancy_id"),
        meta=payload.get("meta"),
    )
    db.add(row)
    await db.flush()
    return row


async def patch_employment(
    db: AsyncSession,
    tenant_id: str,
    employment_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceEmployment]:
    row = (
        await db.execute(
            select(WorkforceEmployment).where(
                WorkforceEmployment.id == employment_id,
                WorkforceEmployment.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    for k, v in patch.items():
        setattr(row, k, v)
    _touch(row)
    await db.flush()
    return row


async def patch_onboarding_task(
    db: AsyncSession,
    tenant_id: str,
    task_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceOnboardingTask]:
    row = (
        await db.execute(
            select(WorkforceOnboardingTask).where(
                WorkforceOnboardingTask.id == task_id,
                WorkforceOnboardingTask.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    for k, v in patch.items():
        setattr(row, k, v)
    if row.status == "done" and row.completed_at is None:
        row.completed_at = _now()
    _touch(row)
    await db.flush()
    return row


async def list_absences_for_employee(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> Optional[list[WorkforceAbsence]]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    res = await db.execute(
        select(WorkforceAbsence)
        .where(
            WorkforceAbsence.tenant_id == tenant_id,
            WorkforceAbsence.employee_id == employee_id,
        )
        .order_by(WorkforceAbsence.start_date.desc(), WorkforceAbsence.created_at.desc())
    )
    return list(res.scalars().all())


async def create_absence(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    payload: dict[str, Any],
) -> Optional[WorkforceAbsence]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    row = WorkforceAbsence(
        id=str(uuid4()),
        tenant_id=tenant_id,
        employee_id=employee_id,
        absence_type=str(payload["absence_type"])[:64],
        start_date=payload["start_date"],
        end_date=payload.get("end_date"),
        source=str(payload.get("source") or "manual")[:64],
        status=str(payload.get("status") or "reported")[:64],
        payer=(payload.get("payer") or None),
        payroll_impact=payload.get("payroll_impact"),
        comment=payload.get("comment"),
        meta=payload.get("meta"),
    )
    db.add(row)
    await db.flush()
    return row


async def patch_absence(
    db: AsyncSession,
    tenant_id: str,
    absence_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceAbsence]:
    row = (
        await db.execute(
            select(WorkforceAbsence).where(
                WorkforceAbsence.id == absence_id,
                WorkforceAbsence.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    for k, v in patch.items():
        setattr(row, k, v)
    _touch(row)
    await db.flush()
    return row


async def list_leave_requests_for_employee(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> Optional[list[WorkforceLeaveRequest]]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    res = await db.execute(
        select(WorkforceLeaveRequest)
        .where(
            WorkforceLeaveRequest.tenant_id == tenant_id,
            WorkforceLeaveRequest.employee_id == employee_id,
        )
        .order_by(WorkforceLeaveRequest.start_date.desc(), WorkforceLeaveRequest.created_at.desc())
    )
    return list(res.scalars().all())


async def create_leave_request(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    payload: dict[str, Any],
) -> Optional[WorkforceLeaveRequest]:
    if not await get_employee(db, tenant_id, employee_id):
        return None
    row = WorkforceLeaveRequest(
        id=str(uuid4()),
        tenant_id=tenant_id,
        employee_id=employee_id,
        leave_type=str(payload["leave_type"])[:64],
        start_date=payload["start_date"],
        end_date=payload["end_date"],
        status=str(payload.get("status") or "pending")[:64],
        year_entitlement_days=_parse_decimal_str(payload.get("year_entitlement_days")),
        used_days_before=_parse_decimal_str(payload.get("used_days_before")),
        conflict_flags=payload.get("conflict_flags"),
        comment=payload.get("comment"),
        meta=payload.get("meta"),
    )
    db.add(row)
    await db.flush()
    return row


async def patch_leave_request(
    db: AsyncSession,
    tenant_id: str,
    leave_id: str,
    patch: dict[str, Any],
    *,
    actor_user_id: Optional[str] = None,
) -> Optional[WorkforceLeaveRequest]:
    row = (
        await db.execute(
            select(WorkforceLeaveRequest).where(
                WorkforceLeaveRequest.id == leave_id,
                WorkforceLeaveRequest.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    patch_copy = dict(patch)
    if "year_entitlement_days" in patch_copy:
        row.year_entitlement_days = _parse_decimal_str(patch_copy.pop("year_entitlement_days"))
    if "used_days_before" in patch_copy:
        row.used_days_before = _parse_decimal_str(patch_copy.pop("used_days_before"))
    for k, v in patch_copy.items():
        setattr(row, k, v)
    if row.status in ("approved", "rejected"):
        if row.decided_at is None:
            row.decided_at = _now()
        if actor_user_id and row.approver_user_id is None:
            row.approver_user_id = actor_user_id
    _touch(row)
    await db.flush()
    return row
