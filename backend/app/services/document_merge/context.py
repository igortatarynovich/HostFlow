from __future__ import annotations

# Trusted HR identity for workforce cases: use employment_identity_read_adapter
# (consumer contract_generation), not candidate snapshot or raw employee profile.

from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Candidate,
    OwnCompany,
    WorkforceEmployee,
    WorkforceEmployment,
)


def _date_iso(val: Optional[date]) -> Optional[str]:
    if val is None:
        return None
    return val.isoformat()


def _candidate_dict(c: Candidate) -> Dict[str, Any]:
    birth = c.birth_date
    return {
        "id": c.id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "full_name": f"{c.first_name} {c.last_name}".strip(),
        "email": c.email,
        "phone": c.phone,
        "address": c.address,
        "address_latin": c.address_latin,
        "birth_date": _date_iso(birth) if isinstance(birth, date) else (str(birth) if birth else None),
        "stage": c.stage,
        "own_company_id": c.own_company_id,
    }


def _employee_dict(e: WorkforceEmployee) -> Dict[str, Any]:
    return {
        "id": e.id,
        "display_name": e.display_name,
        "status": e.status,
        "hire_date": _date_iso(e.hire_date),
        "probation_end": _date_iso(e.probation_end),
        "termination_date": _date_iso(e.termination_date),
        "candidate_id": e.candidate_id,
        "own_company_id": e.own_company_id,
        "company_id": e.company_id,
        "vacancy_id": e.vacancy_id,
    }


def _employment_dict(row: WorkforceEmployment) -> Dict[str, Any]:
    return {
        "id": row.id,
        "contract_type": row.contract_type,
        "start_date": _date_iso(row.start_date),
        "end_date": _date_iso(row.end_date),
        "conditions_text": row.conditions_text,
        "rate_model": row.rate_model,
        "schedule": row.schedule,
        "meta": row.meta,
    }


def _own_company_dict(oc: OwnCompany) -> Dict[str, Any]:
    return {
        "id": oc.id,
        "name": oc.name,
        "legal_name": oc.legal_name,
        "tax_id": oc.tax_id,
        "country_code": oc.country_code,
        "country": oc.country,
        "city": oc.city,
        "address": oc.address,
        "signing_place": oc.city or oc.address or oc.name,
    }


async def build_merge_context(
    session: AsyncSession,
    tenant_id: str,
    *,
    candidate: Optional[Candidate] = None,
    employee: Optional[WorkforceEmployee] = None,
    extra_bindings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    ctx: Dict[str, Any] = {
        "generated": {
            "now": now.isoformat(),
            "today": now.date().isoformat(),
            "utc_date": now.date().isoformat(),
        },
        "bindings": dict(extra_bindings or {}),
    }

    oc_id: Optional[str] = None
    if employee is not None:
        ctx["employee"] = _employee_dict(employee)
        oc_id = employee.own_company_id or oc_id
        stmt = (
            select(WorkforceEmployment)
            .where(
                WorkforceEmployment.tenant_id == tenant_id,
                WorkforceEmployment.employee_id == employee.id,
            )
            .order_by(WorkforceEmployment.created_at.desc())
            .limit(1)
        )
        emp_row = (await session.execute(stmt)).scalar_one_or_none()
        ctx["employment"] = _employment_dict(emp_row) if emp_row else {}

    if candidate is not None:
        ctx["candidate"] = _candidate_dict(candidate)
        oc_id = oc_id or candidate.own_company_id

    if oc_id:
        oc = await session.get(OwnCompany, oc_id)
        if oc and oc.tenant_id == tenant_id and not oc.is_archived:
            ctx["own_company"] = _own_company_dict(oc)
        else:
            ctx["own_company"] = {}
    else:
        ctx["own_company"] = {}

    return ctx
