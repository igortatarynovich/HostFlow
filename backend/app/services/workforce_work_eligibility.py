"""Work eligibility profile — legal stay / work permit state (PR-4)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_work_eligibility_profile import WorkforceWorkEligibilityProfile

_PATCH_KEYS = frozenset(
    {
        "citizenship",
        "residence_status",
        "legal_stay_document_type",
        "legal_stay_valid_to",
        "requires_work_permit",
        "work_permit_type",
        "work_permit_submission_method",
        "work_permit_application_status",
        "work_permit_submitted_at",
        "work_permit_received_at",
        "work_permit_valid_to",
        "red_paper_required",
        "red_paper_status",
        "eligibility_status",
        "position_category",
        "work_country",
        "employer_country",
        "contract_type",
        "meta",
    }
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _touch(row: WorkforceWorkEligibilityProfile) -> None:
    row.updated_at = _now()


def _eligibility_overlay(row: WorkforceWorkEligibilityProfile, patch: dict[str, Any]) -> Any:
    data: dict[str, Any] = {k: getattr(row, k, None) for k in _PATCH_KEYS}
    for k, v in patch.items():
        if k in _PATCH_KEYS:
            data[k] = v
    return SimpleNamespace(**data)


async def ensure_work_eligibility_profile(db: AsyncSession, tenant_id: str, employee_id: str) -> None:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceWorkEligibilityProfile)
            .where(
                WorkforceWorkEligibilityProfile.tenant_id == tid,
                WorkforceWorkEligibilityProfile.employee_id == eid,
            )
        )
    ).scalar_one()
    if not int(cnt or 0):
        db.add(
            WorkforceWorkEligibilityProfile(
                tenant_id=tid,
                employee_id=eid,
                eligibility_status="not_evaluated",
            )
        )
    await db.flush()


async def get_work_eligibility_profile(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> Optional[WorkforceWorkEligibilityProfile]:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    return (
        await db.execute(
            select(WorkforceWorkEligibilityProfile).where(
                WorkforceWorkEligibilityProfile.tenant_id == tid,
                WorkforceWorkEligibilityProfile.employee_id == eid,
            )
        )
    ).scalar_one_or_none()


async def patch_work_eligibility_profile(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceWorkEligibilityProfile]:
    from backend.app.services.workforce_work_eligibility_payments import (
        ensure_fee_onboarding_tasks,
        ensure_foreign_driver_payment_requirements,
        list_payment_requirements,
    )
    from backend.app.services.workforce_work_eligibility_rules import validate_work_eligibility_profile_patch

    await ensure_work_eligibility_profile(db, tenant_id, employee_id)
    row = await get_work_eligibility_profile(db, tenant_id, employee_id)
    if not row:
        return None
    overlay = _eligibility_overlay(row, patch)
    await ensure_foreign_driver_payment_requirements(db, tenant_id, employee_id, overlay)
    payments = await list_payment_requirements(db, tenant_id, employee_id)
    validate_work_eligibility_profile_patch(row, patch, payments)
    for k, v in patch.items():
        if k in _PATCH_KEYS:
            setattr(row, k, v)
    _touch(row)
    await db.flush()
    await ensure_foreign_driver_payment_requirements(db, tenant_id, employee_id, row)
    await ensure_fee_onboarding_tasks(db, tenant_id, employee_id)
    return row
