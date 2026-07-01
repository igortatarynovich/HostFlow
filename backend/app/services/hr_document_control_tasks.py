from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_hr_document_control_task import WorkforceHrDocumentControlTask


async def list_document_control_tasks(
    db: AsyncSession, *, tenant_id: str, employee_id: str
) -> list[WorkforceHrDocumentControlTask]:
    rows = await db.execute(
        select(WorkforceHrDocumentControlTask).where(
            WorkforceHrDocumentControlTask.tenant_id == str(tenant_id).strip(),
            WorkforceHrDocumentControlTask.employee_id == str(employee_id).strip(),
        )
    )
    return list(rows.scalars().all())


async def upsert_document_control_task(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    document_code: str,
    patch: dict[str, Any],
) -> WorkforceHrDocumentControlTask:
    tid = str(tenant_id).strip()
    eid = str(employee_id).strip()
    code = str(document_code).strip().lower()
    row = (
        await db.execute(
            select(WorkforceHrDocumentControlTask).where(
                WorkforceHrDocumentControlTask.tenant_id == tid,
                WorkforceHrDocumentControlTask.employee_id == eid,
                WorkforceHrDocumentControlTask.document_code == code,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = WorkforceHrDocumentControlTask(
            tenant_id=tid,
            employee_id=eid,
            document_code=code,
        )
        db.add(row)
    for k in ("owner", "next_action", "comment", "status"):
        if k in patch:
            setattr(row, k, patch.get(k))
    if "next_due_date" in patch:
        val = patch.get("next_due_date")
        row.next_due_date = val if isinstance(val, date) or val is None else None
    await db.flush()
    return row

