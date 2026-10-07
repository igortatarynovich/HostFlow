"""Operator path from Employment(preparing) to Active.

Each step calls an existing runtime. This router does not invent a document
list or a required person-fact checklist.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.hr_workforce_access import require_hr_workforce_module_access
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.hr_employment import Employment
from backend.app.models.hr_employment_requirement import HrEmploymentRequirement
from backend.app.models.hr_employment_terms import HrEmploymentTerms
from backend.app.models.hr_legal_eligibility_gate import HrLegalEligibilityGateDecision
from backend.app.models.hr_ready_to_start import HrReadyToStartDecision
from backend.app.services.employment_terms_runtime import (
    TERMS_COMPLETE,
    EmploymentTermsConfirmation,
    confirm_employment_terms,
    evaluate_employment_terms,
)
from backend.app.services.hr_legal_eligibility_gate import record_hr_legal_eligibility_gate
from backend.app.services.pre_employment_requirements_runtime import (
    RequirementDefinition,
    block_pre_employment_requirement,
    evaluate_pre_employment_requirements,
    materialize_pre_employment_requirements,
    satisfy_pre_employment_requirement,
    waive_pre_employment_requirement,
)
from backend.app.services.ready_to_start_runtime import activate_employment, record_ready_to_start

router = APIRouter(prefix="/hr", dependencies=[Depends(require_hr_workforce_module_access)])


class LegalReadingIn(BaseModel):
    citizenship_class: str
    stay_basis: str
    work_authorization_basis: str
    valid_for_this_employment: str


class EmployeeDataIn(BaseModel):
    complete: bool
    facts: dict[str, Any] = Field(default_factory=dict)


class TermsIn(BaseModel):
    position: str
    contract_basis: str
    work_time_value: Decimal
    work_time_unit: str
    workplace: str
    compensation_amount: Decimal
    compensation_currency: str
    compensation_unit: str
    duration: str
    probation_status: str
    fixed_term_end: date | None = None
    probation_end: date | None = None
    default_vacancy_id: str | None = None


class RequirementItemIn(BaseModel):
    definition_key: str
    applicability: str = "applicable"
    policy_id: str = "operator.v1"
    policy_version: str = "1"
    applicability_basis: str = "operator"


class MaterializeIn(BaseModel):
    items: list[RequirementItemIn]


class WaiveIn(BaseModel):
    definition_key: str
    reason: str


class SatisfyIn(BaseModel):
    definition_key: str
    evidence_id: str | None = None
    document_id: str | None = None


class BlockIn(BaseModel):
    definition_key: str
    reason: str


class ReadyIn(BaseModel):
    legal: LegalReadingIn
    employee_data_complete: bool
    facts: dict[str, Any] = Field(default_factory=dict)


def _reading(body: LegalReadingIn) -> dict[str, str]:
    return {
        "citizenship_class": body.citizenship_class,
        "stay_basis": body.stay_basis,
        "work_authorization_basis": body.work_authorization_basis,
        "valid_for_this_employment": body.valid_for_this_employment,
    }


async def _employment_for_employee(db: AsyncSession, tenant_id: str, employee_id: str) -> Employment | None:
    res = await db.execute(
        select(Employment)
        .where(
            Employment.tenant_id == tenant_id,
            Employment.employee_id == employee_id,
        )
        .order_by(Employment.created_at.desc(), Employment.id.desc())
    )
    return res.scalars().first()


async def _employment(db: AsyncSession, tenant_id: str, employment_id: str) -> Employment:
    row = await db.get(Employment, employment_id)
    if row is None or str(row.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Employment not found")
    return row


def _refuse(reason: str | None) -> None:
    if reason:
        raise HTTPException(status_code=400, detail=reason)


@router.get("/employees/{employee_id}/employment-path")
async def get_employment_path(
    employee_id: str,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    employment = await _employment_for_employee(db, tid, employee_id)
    if employment is None:
        return {"employment": None}
    legal = (
        await db.execute(
            select(HrLegalEligibilityGateDecision)
            .where(
                HrLegalEligibilityGateDecision.tenant_id == tid,
                HrLegalEligibilityGateDecision.employment_id == employment.id,
            )
            .order_by(
                HrLegalEligibilityGateDecision.decided_at.desc(),
                HrLegalEligibilityGateDecision.id.desc(),
            )
        )
    ).scalars().first()
    terms = (
        await db.execute(
            select(HrEmploymentTerms).where(
                HrEmploymentTerms.tenant_id == tid,
                HrEmploymentTerms.employment_id == employment.id,
                HrEmploymentTerms.is_current.is_(True),
            )
        )
    ).scalars().first()
    requirements = (
        await db.execute(
            select(HrEmploymentRequirement)
            .where(
                HrEmploymentRequirement.tenant_id == tid,
                HrEmploymentRequirement.employment_id == employment.id,
            )
            .order_by(HrEmploymentRequirement.definition_key.asc())
        )
    ).scalars().all()
    ready = (
        await db.execute(
            select(HrReadyToStartDecision)
            .where(
                HrReadyToStartDecision.tenant_id == tid,
                HrReadyToStartDecision.employment_id == employment.id,
            )
            .order_by(HrReadyToStartDecision.decided_at.desc(), HrReadyToStartDecision.id.desc())
        )
    ).scalars().first()

    def _sync_eval(sync) -> bool:
        row = sync.get(Employment, employment.id)
        if row is None:
            return False
        return bool(evaluate_pre_employment_requirements(sync, tenant_id=tid, employment=row))

    requirements_ready = await db.run_sync(_sync_eval)
    return {
        "employment": {
            "id": employment.id,
            "state": employment.state,
            "employee_id": employment.employee_id,
            "handoff_id": employment.handoff_id,
        },
        "legal": None
        if legal is None
        else {
            "outcome": legal.outcome,
            "citizenship_class": legal.citizenship_class,
            "stay_basis": legal.stay_basis,
            "work_authorization_basis": legal.work_authorization_basis,
            "valid_for_this_employment": legal.valid_for_this_employment,
        },
        "terms": None
        if terms is None
        else {
            "complete": evaluate_employment_terms(terms) == TERMS_COMPLETE,
            "position": terms.position,
            "contract_basis": terms.contract_basis,
            "work_time_value": str(terms.work_time_value) if terms.work_time_value is not None else None,
            "work_time_unit": terms.work_time_unit,
            "workplace": terms.workplace,
            "compensation_amount": str(terms.compensation_amount) if terms.compensation_amount is not None else None,
            "compensation_currency": terms.compensation_currency,
            "compensation_unit": terms.compensation_unit,
            "duration": terms.duration,
            "probation_status": terms.probation_status,
        },
        "requirements": [
            {
                "definition_key": row.definition_key,
                "applicability": row.applicability,
                "resolution": row.resolution,
            }
            for row in requirements
        ],
        "requirements_ready": requirements_ready,
        "ready_to_start": None
        if ready is None
        else {
            "outcome": ready.outcome,
            "blocked_reasons": ready.blocked_reasons,
            "employee_data_result": ready.employee_data_result,
        },
    }


@router.post("/employments/{employment_id}/legal")
async def post_legal(
    employment_id: str,
    body: LegalReadingIn,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    employment = await _employment(db, str(tenant_id), employment_id)
    result = await record_hr_legal_eligibility_gate(
        db,
        tenant_id=str(tenant_id),
        employment=employment,
        reading=_reading(body),
        actor_user_id=current_user.sub,
    )
    if not result.applies:
        raise HTTPException(status_code=400, detail=result.outcome or "legal_not_applicable")
    return {"outcome": result.outcome}


@router.post("/employments/{employment_id}/terms")
async def post_terms(
    employment_id: str,
    body: TermsIn,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _confirm(sync):
        employment = sync.get(Employment, employment_id)
        return confirm_employment_terms(
            sync,
            tenant_id=tid,
            employment=employment,
            confirmation=EmploymentTermsConfirmation(
                position=body.position,
                contract_basis=body.contract_basis,
                work_time_value=body.work_time_value,
                work_time_unit=body.work_time_unit,
                workplace=body.workplace,
                compensation_amount=body.compensation_amount,
                compensation_currency=body.compensation_currency,
                compensation_unit=body.compensation_unit,
                duration=body.duration,
                fixed_term_end=body.fixed_term_end,
                probation_status=body.probation_status,
                probation_end=body.probation_end,
                default_vacancy_id=body.default_vacancy_id,
            ),
        )

    result = await db.run_sync(_confirm)
    _refuse(None if result.accepted else result.reason)
    return {"accepted": True}


@router.post("/employments/{employment_id}/requirements")
async def post_requirements(
    employment_id: str,
    body: MaterializeIn,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)
    definitions = tuple(
        RequirementDefinition(
            definition_key=item.definition_key,
            policy_id=item.policy_id,
            policy_version=item.policy_version,
            applicability=item.applicability,
            applicability_basis=item.applicability_basis,
        )
        for item in body.items
    )

    def _write(sync):
        employment = sync.get(Employment, employment_id)
        return materialize_pre_employment_requirements(
            sync,
            tenant_id=tid,
            employment=employment,
            definitions=definitions,
        )

    result = await db.run_sync(_write)
    _refuse(None if result.accepted else result.reason)
    return {"accepted": True, "count": len(result.requirements)}


@router.post("/employments/{employment_id}/requirements/waive")
async def post_waive(
    employment_id: str,
    body: WaiveIn,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _waive(sync):
        employment = sync.get(Employment, employment_id)
        return waive_pre_employment_requirement(
            sync,
            tenant_id=tid,
            employment=employment,
            definition_key=body.definition_key,
            actor_id=current_user.sub,
            waiver_at=datetime.now(timezone.utc),
            reason=body.reason,
        )

    result = await db.run_sync(_waive)
    _refuse(None if result.accepted else result.reason)
    return {"accepted": True}


@router.post("/employments/{employment_id}/requirements/satisfy")
async def post_satisfy(
    employment_id: str,
    body: SatisfyIn,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _satisfy(sync):
        employment = sync.get(Employment, employment_id)
        return satisfy_pre_employment_requirement(
            sync,
            tenant_id=tid,
            employment=employment,
            definition_key=body.definition_key,
            evidence_id=body.evidence_id,
            document_id=body.document_id,
        )

    result = await db.run_sync(_satisfy)
    _refuse(None if result.accepted else result.reason)
    return {"accepted": True}


@router.post("/employments/{employment_id}/requirements/block")
async def post_block(
    employment_id: str,
    body: BlockIn,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _block(sync):
        employment = sync.get(Employment, employment_id)
        return block_pre_employment_requirement(
            sync,
            tenant_id=tid,
            employment=employment,
            definition_key=body.definition_key,
            blocking_reason=body.reason,
        )

    result = await db.run_sync(_block)
    _refuse(None if result.accepted else result.reason)
    return {"accepted": True}


@router.post("/employments/{employment_id}/ready-to-start")
async def post_ready(
    employment_id: str,
    body: ReadyIn,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _record(sync):
        employment = sync.get(Employment, employment_id)
        return record_ready_to_start(
            sync,
            tenant_id=tid,
            employment=employment,
            actor_user_id=current_user.sub,
            legal_reading=_reading(body.legal),
            employee_facts=body.facts,
            employee_data_complete=body.employee_data_complete,
        )

    result = await db.run_sync(_record)
    _refuse(None if result.accepted else result.reason)
    decision = result.decision
    return {
        "outcome": None if decision is None else decision.outcome,
        "blocked_reasons": None if decision is None else decision.blocked_reasons,
    }


@router.post("/employments/{employment_id}/activate")
async def post_activate(
    employment_id: str,
    body: ReadyIn,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    await _employment(db, tid, employment_id)

    def _activate(sync):
        return activate_employment(
            sync,
            tenant_id=tid,
            employment_id=employment_id,
            legal_reading=_reading(body.legal),
            employee_facts=body.facts,
            employee_data_complete=body.employee_data_complete,
        )

    result = await db.run_sync(_activate)
    if not result.activated:
        raise HTTPException(status_code=400, detail=result.reason or "blocked")
    return {"state": "active"}
