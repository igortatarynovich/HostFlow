"""Ensure first-class HR core rows (tax, insurance, compliance) exist per workforce employee."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_compliance_state import WorkforceComplianceState
from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
from backend.app.models.workforce_tax_profile import WorkforceTaxProfile


async def ensure_workforce_hr_core_profiles(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> None:
    """Idempotent: create empty tax, insurance, and compliance_state rows when missing."""
    tid = str(tenant_id).strip()
    eid = str(employee_id).strip()

    tax_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceTaxProfile)
            .where(WorkforceTaxProfile.tenant_id == tid, WorkforceTaxProfile.employee_id == eid)
        )
    ).scalar_one()
    if not int(tax_cnt or 0):
        db.add(
            WorkforceTaxProfile(
                tenant_id=tid,
                employee_id=eid,
                pit2_submitted=False,
                young_person_relief=False,
            )
        )

    ins_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceInsuranceProfile)
            .where(
                WorkforceInsuranceProfile.tenant_id == tid,
                WorkforceInsuranceProfile.employee_id == eid,
            )
        )
    ).scalar_one()
    if not int(ins_cnt or 0):
        db.add(
            WorkforceInsuranceProfile(
                tenant_id=tid,
                employee_id=eid,
                status="draft",
            )
        )

    comp_cnt = (
        await db.execute(
            select(func.count())
            .select_from(WorkforceComplianceState)
            .where(
                WorkforceComplianceState.tenant_id == tid,
                WorkforceComplianceState.employee_id == eid,
            )
        )
    ).scalar_one()
    if not int(comp_cnt or 0):
        db.add(
            WorkforceComplianceState(
                tenant_id=tid,
                employee_id=eid,
                status="not_evaluated",
                missing_count=0,
                expired_count=0,
                expiring_soon_count=0,
                high_risk_count=0,
                cannot_work=False,
            )
        )

    await db.flush()


async def get_tax_profile(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> Optional[WorkforceTaxProfile]:
    return (
        await db.execute(
            select(WorkforceTaxProfile).where(
                WorkforceTaxProfile.tenant_id == tenant_id,
                WorkforceTaxProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()


async def get_insurance_profile(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> Optional[WorkforceInsuranceProfile]:
    return (
        await db.execute(
            select(WorkforceInsuranceProfile).where(
                WorkforceInsuranceProfile.tenant_id == tenant_id,
                WorkforceInsuranceProfile.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()


async def get_compliance_state(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> Optional[WorkforceComplianceState]:
    return (
        await db.execute(
            select(WorkforceComplianceState).where(
                WorkforceComplianceState.tenant_id == tenant_id,
                WorkforceComplianceState.employee_id == employee_id,
            )
        )
    ).scalar_one_or_none()
