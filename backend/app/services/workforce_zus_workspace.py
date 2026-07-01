"""List/create/update ZUS workspace tasks (operational queue)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask


def normalize_form_kind_for_storage(raw: object | None) -> Optional[str]:
    """ZUA/ZZA/ZWUA stored uppercase; other labels (e.g. monthly_settlement) keep case, max 32 chars."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    u = s.upper()
    if u in ("ZUA", "ZZA", "ZWUA"):
        return u
    return s[:32]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _touch(row: WorkforceZusWorkspaceTask) -> None:
    row.updated_at = _now()


async def list_zus_workspace_tasks(
    db: AsyncSession,
    tenant_id: str,
    *,
    status: Optional[str] = None,
    workspace_lane: Optional[str] = None,
    task_kind: Optional[str] = None,
    form_kind: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    assigned_hr_user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    tid = str(tenant_id).strip()
    emp = aliased(WorkforceEmployee)
    base = (
        select(WorkforceZusWorkspaceTask, emp.display_name)
        .join(emp, emp.id == WorkforceZusWorkspaceTask.employee_id)
        .where(WorkforceZusWorkspaceTask.tenant_id == tid, emp.tenant_id == tid)
    )
    if status:
        base = base.where(WorkforceZusWorkspaceTask.status == str(status).strip())
    if workspace_lane:
        base = base.where(WorkforceZusWorkspaceTask.workspace_lane == str(workspace_lane).strip())
    if task_kind:
        base = base.where(WorkforceZusWorkspaceTask.task_kind == str(task_kind).strip())
    if form_kind:
        fk = normalize_form_kind_for_storage(form_kind)
        if fk:
            base = base.where(WorkforceZusWorkspaceTask.form_kind == fk)
    if due_before is not None:
        base = base.where(
            WorkforceZusWorkspaceTask.due_at.is_not(None),
            WorkforceZusWorkspaceTask.due_at <= due_before,
        )
    if due_after is not None:
        base = base.where(
            WorkforceZusWorkspaceTask.due_at.is_not(None),
            WorkforceZusWorkspaceTask.due_at >= due_after,
        )
    if assigned_hr_user_id:
        aid = str(assigned_hr_user_id).strip()
        base = base.where(WorkforceZusWorkspaceTask.assigned_hr_user_id == aid)

    count_q = (
        select(func.count(WorkforceZusWorkspaceTask.id))
        .select_from(WorkforceZusWorkspaceTask)
        .join(emp, emp.id == WorkforceZusWorkspaceTask.employee_id)
        .where(WorkforceZusWorkspaceTask.tenant_id == tid, emp.tenant_id == tid)
    )
    if status:
        count_q = count_q.where(WorkforceZusWorkspaceTask.status == str(status).strip())
    if workspace_lane:
        count_q = count_q.where(WorkforceZusWorkspaceTask.workspace_lane == str(workspace_lane).strip())
    if task_kind:
        count_q = count_q.where(WorkforceZusWorkspaceTask.task_kind == str(task_kind).strip())
    if form_kind:
        fk = normalize_form_kind_for_storage(form_kind)
        if fk:
            count_q = count_q.where(WorkforceZusWorkspaceTask.form_kind == fk)
    if due_before is not None:
        count_q = count_q.where(
            WorkforceZusWorkspaceTask.due_at.is_not(None),
            WorkforceZusWorkspaceTask.due_at <= due_before,
        )
    if due_after is not None:
        count_q = count_q.where(
            WorkforceZusWorkspaceTask.due_at.is_not(None),
            WorkforceZusWorkspaceTask.due_at >= due_after,
        )
    if assigned_hr_user_id:
        count_q = count_q.where(WorkforceZusWorkspaceTask.assigned_hr_user_id == str(assigned_hr_user_id).strip())
    total = int((await db.execute(count_q)).scalar_one() or 0)

    stmt = base.order_by(
        WorkforceZusWorkspaceTask.due_at.asc().nullslast(),
        WorkforceZusWorkspaceTask.created_at.desc(),
    ).offset(max(offset, 0)).limit(min(max(limit, 1), 500))
    rows = list((await db.execute(stmt)).all())

    out: list[dict[str, Any]] = []
    for task, display_name in rows:
        out.append(
            {
                "task": task,
                "employee_display_name": str(display_name or "").strip(),
            }
        )
    return out, total


async def create_zus_workspace_task(
    db: AsyncSession,
    tenant_id: str,
    payload: dict[str, Any],
) -> Optional[WorkforceZusWorkspaceTask]:
    tid = str(tenant_id).strip()
    eid = str(payload.get("employee_id") or "").strip()
    emp = (
        await db.execute(
            select(WorkforceEmployee).where(WorkforceEmployee.tenant_id == tid, WorkforceEmployee.id == eid)
        )
    ).scalar_one_or_none()
    if not emp:
        return None
    fk = normalize_form_kind_for_storage(payload.get("form_kind"))
    row = WorkforceZusWorkspaceTask(
        tenant_id=tid,
        employee_id=eid,
        workspace_lane=str(payload.get("workspace_lane") or "")[:32],
        task_kind=str(payload.get("task_kind") or "")[:64],
        title=str(payload.get("title") or "")[:256],
        form_kind=fk,
        form_status=(str(payload.get("form_status")).strip()[:32] if payload.get("form_status") is not None else None),
        status=str(payload.get("status") or "open")[:32],
        due_at=payload.get("due_at"),
        assigned_hr_user_id=str(payload["assigned_hr_user_id"]).strip()
        if payload.get("assigned_hr_user_id")
        else None,
        export_status=(str(payload.get("export_status")).strip()[:32] if payload.get("export_status") is not None else None),
        checklist_json=payload.get("checklist_json"),
        notes=str(payload.get("notes")).strip() if payload.get("notes") else None,
    )
    db.add(row)
    await db.flush()
    return row


async def patch_zus_workspace_task(
    db: AsyncSession,
    tenant_id: str,
    task_id: str,
    patch: dict[str, Any],
) -> Optional[WorkforceZusWorkspaceTask]:
    tid = str(tenant_id).strip()
    row = (
        await db.execute(
            select(WorkforceZusWorkspaceTask).where(
                WorkforceZusWorkspaceTask.tenant_id == tid,
                WorkforceZusWorkspaceTask.id == str(task_id).strip(),
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    data = dict(patch)
    if "form_kind" in data and data["form_kind"] is not None:
        data["form_kind"] = normalize_form_kind_for_storage(data["form_kind"])
    for k in (
        "workspace_lane",
        "task_kind",
        "title",
        "form_kind",
        "form_status",
        "status",
        "due_at",
        "assigned_hr_user_id",
        "export_status",
        "checklist_json",
        "notes",
    ):
        if k in data:
            setattr(row, k, data[k])
    _touch(row)
    await db.flush()
    return row


async def get_task_with_employee_name(
    db: AsyncSession, tenant_id: str, task_id: str
) -> Optional[tuple[WorkforceZusWorkspaceTask, str]]:
    tid = str(tenant_id).strip()
    emp = aliased(WorkforceEmployee)
    r = (
        await db.execute(
            select(WorkforceZusWorkspaceTask, emp.display_name)
            .join(emp, emp.id == WorkforceZusWorkspaceTask.employee_id)
            .where(
                WorkforceZusWorkspaceTask.tenant_id == tid,
                WorkforceZusWorkspaceTask.id == str(task_id).strip(),
                emp.tenant_id == tid,
            )
        )
    ).one_or_none()
    if not r:
        return None
    task, dn = r[0], r[1]
    return task, str(dn or "").strip()


def task_to_out(task: WorkforceZusWorkspaceTask, employee_display_name: str) -> dict[str, Any]:
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "employee_id": task.employee_id,
        "employee_display_name": employee_display_name,
        "workspace_lane": task.workspace_lane,
        "task_kind": task.task_kind,
        "form_kind": task.form_kind,
        "form_status": task.form_status,
        "status": task.status,
        "due_at": task.due_at,
        "assigned_hr_user_id": task.assigned_hr_user_id,
        "export_status": task.export_status,
        "checklist_json": task.checklist_json,
        "title": task.title,
        "notes": task.notes,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
