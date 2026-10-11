"""Read and write the HR employee record projection."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.module_gate import require_hr_workforce_module_access
from backend.app.auth.trust_role_deps import require_trust_write
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import workforce_employees as we_svc
from backend.app.services.hr_employee_record_projection import RecordWriteRejected
from backend.app.services.hr_employee_record_runtime import write_hr_employee_record
from backend.app.services.hr_employee_record_surface import build_hr_employee_record_surface

router = APIRouter(
    prefix="/employees/{employee_id}/employee-record",
    dependencies=[Depends(require_trust_write()), Depends(require_hr_workforce_module_access)],
)


class EmployeeRecordWrite(BaseModel):
    address: str
    value: Any = None
    evidence_id: Optional[str] = None


@router.get("")
async def get_hr_employee_record(
    employee_id: str,
    employment_id: Optional[str] = Query(default=None),
    db_tenant: tuple[AsyncSession, Any] = Depends(get_db_with_tenant),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    employee = await we_svc.get_employee(db, str(tenant_id), employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return await build_hr_employee_record_surface(db, tenant_id=str(tenant_id), employee=employee)


@router.patch("")
async def patch_hr_employee_record(
    employee_id: str,
    payload: EmployeeRecordWrite,
    employment_id: str = Query(...),
    db_tenant: tuple[AsyncSession, Any] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    try:
        return await write_hr_employee_record(
            db,
            tenant_id=str(tenant_id),
            employee_id=employee_id,
            employment_id=employment_id,
            address=payload.address,
            value=payload.value,
            actor_user_id=current_user.sub,
            evidence_id=payload.evidence_id,
        )
    except RecordWriteRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
