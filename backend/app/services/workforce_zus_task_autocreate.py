"""Auto-create ZUS workspace tasks from employee / insurance state (no ZUS API, no payroll)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.audit import log_activity
from backend.app.services.workforce_hr_core_profiles import get_insurance_profile
from backend.app.services.workforce_work_eligibility import get_work_eligibility_profile
from backend.app.services.workforce_work_eligibility_payments import list_payment_requirements
from backend.app.services.workforce_work_eligibility_rules import evaluate_zus_registration_gate
from backend.app.services import workforce_zus_workspace as zus_svc
from backend.app.services.workforce_downstream_identity import evaluate_zus_preparation

TASK_KIND_REGISTRATION = "registration"
TASK_KIND_DEREGISTRATION = "deregistration"
TASK_KIND_MONTHLY_SETTLEMENT = "monthly_settlement"
FORM_KIND_MONTHLY_SETTLEMENT = "monthly_settlement"

_ACTIVE_IDEMPOTENCY_STATUSES = frozenset({"pending", "open", "in_progress"})
_REGISTRATION_ROW_STATUSES = frozenset({"pending", "open", "in_progress", "blocked"})

_STATUS_REQUIRES_ZUS_REGISTRATION = frozenset({"pending_zus", "pending_registration"})
_STATUS_EXEMPT_REGISTRATION = frozenset({"exempt", "no_zus", "not_applicable"})
_STATUS_IMPLIES_ZWUA = frozenset(
    {"terminated", "deregistered", "pending_zwua", "pending_deregistration"}
)
_DEREG_INSURANCE_STATUSES = frozenset({"deregistered", "terminated", "pending_zwua", "pending_deregistration"})


def normalize_monthly_period(period: str) -> str:
    p = (period or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}", p):
        return p
    if re.fullmatch(r"\d{6}", p):
        return f"{p[:4]}-{p[4:6]}"
    raise ValueError(f"Invalid period {period!r}; expected YYYY-MM or YYYYMM")


def insurance_status_requires_zus_registration(ins: WorkforceInsuranceProfile) -> bool:
    st = (ins.status or "").strip().lower()
    return st in _STATUS_REQUIRES_ZUS_REGISTRATION


def should_offer_registration_task(ins: WorkforceInsuranceProfile) -> bool:
    if ins.registered_at is not None:
        return False
    if not (ins.zus_registration_type or "").strip():
        return False
    st = (ins.status or "").strip().lower()
    if st in _STATUS_EXEMPT_REGISTRATION:
        return False
    return insurance_status_requires_zus_registration(ins)


def pick_registration_form_kind(ins: WorkforceInsuranceProfile) -> str:
    t = (ins.zus_registration_type or "").lower()
    if "zlec" in t or "b2b" in t or "contractor" in t or "order" in t or "dzieło" in t:
        return "ZZA"
    if "prac" in t or "uop" in t or "employment" in t:
        return "ZUA"
    si = (ins.social_insurance or "").lower()
    if "zlec" in si:
        return "ZZA"
    return "ZUA"


def should_create_zwua_after_insurance_change(before: dict[str, Any], ins: WorkforceInsuranceProfile) -> bool:
    prev_d = before.get("deregistered_at")
    new_d = ins.deregistered_at
    if new_d is not None and prev_d is None:
        return True
    prev_st = str(before.get("status") or "").strip().lower()
    new_st = (ins.status or "").strip().lower()
    if new_st in _STATUS_IMPLIES_ZWUA and prev_st not in _STATUS_IMPLIES_ZWUA:
        return True
    return False


def insurance_eligible_for_zwua_task(ins: WorkforceInsuranceProfile) -> bool:
    if ins.deregistered_at is not None:
        return True
    return (ins.status or "").strip().lower() in _DEREG_INSURANCE_STATUSES


def insurance_monitored_fields_unchanged(before: dict[str, Any], ins: WorkforceInsuranceProfile) -> bool:
    def _d(v: object) -> object:
        return v if not isinstance(v, date) else v

    return (
        before.get("zus_registration_type") == ins.zus_registration_type
        and _d(before.get("registered_at")) == _d(ins.registered_at)
        and _d(before.get("deregistered_at")) == _d(ins.deregistered_at)
        and before.get("status") == ins.status
    )


async def _get_employee(db: AsyncSession, employee_id: str) -> Optional[WorkforceEmployee]:
    eid = str(employee_id).strip()
    return (
        await db.execute(select(WorkforceEmployee).where(WorkforceEmployee.id == eid))
    ).scalar_one_or_none()


async def _get_registration_task_row(
    db: AsyncSession, tenant_id: str, employee_id: str, form_kind: str
) -> Optional[WorkforceZusWorkspaceTask]:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    fk = str(form_kind).strip()
    return (
        await db.execute(
            select(WorkforceZusWorkspaceTask)
            .where(
                WorkforceZusWorkspaceTask.tenant_id == tid,
                WorkforceZusWorkspaceTask.employee_id == eid,
                WorkforceZusWorkspaceTask.task_kind == TASK_KIND_REGISTRATION,
                WorkforceZusWorkspaceTask.form_kind == fk,
                WorkforceZusWorkspaceTask.status.in_(_REGISTRATION_ROW_STATUSES),
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def _has_active_task(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    *,
    task_kind: str,
    form_kind: Optional[str],
    period: Optional[str] = None,
) -> bool:
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    q = select(func.count(WorkforceZusWorkspaceTask.id)).where(
        WorkforceZusWorkspaceTask.tenant_id == tid,
        WorkforceZusWorkspaceTask.employee_id == eid,
        WorkforceZusWorkspaceTask.task_kind == task_kind,
        WorkforceZusWorkspaceTask.status.in_(_ACTIVE_IDEMPOTENCY_STATUSES),
    )
    if form_kind is not None:
        q = q.where(WorkforceZusWorkspaceTask.form_kind == form_kind)
    if period is not None:
        q = q.where(WorkforceZusWorkspaceTask.checklist_json["period"].as_string() == period)
    n = (await db.execute(q)).scalar_one()
    return int(n or 0) > 0


async def _log_zus_task_auto_created(
    db: AsyncSession,
    *,
    tenant_id: str,
    task_id: str,
    employee_id: str,
    form_kind: Optional[str],
    task_kind: str,
    period: Optional[str],
    source: str,
    actor_id: Optional[str],
) -> None:
    await log_activity(
        db,
        tenant_id=str(tenant_id).strip(),
        action="zus_task_auto_created",
        actor_id=actor_id,
        target_type="workforce_zus_workspace_task",
        target_id=str(task_id).strip(),
        payload={
            "employee_id": str(employee_id).strip(),
            "task_id": str(task_id).strip(),
            "form_kind": form_kind,
            "task_kind": task_kind,
            "period": period,
            "source": source,
            "actor_id": actor_id,
        },
    )
    await db.flush()


async def ensure_zus_registration_task(
    db: AsyncSession,
    employee_id: str,
    *,
    actor_id: Optional[str] = None,
    source: str = "employee_create",
) -> Optional[str]:
    emp = await _get_employee(db, employee_id)
    if not emp:
        return None
    tenant_id = str(emp.tenant_id).strip()
    eid = str(employee_id).strip()

    identity_prep = await evaluate_zus_preparation(db, tenant_id, eid)
    if identity_prep.blocked:
        fk_guess = "ZUA"
        ins_early = await get_insurance_profile(db, tenant_id, employee_id)
        if ins_early:
            fk_guess = pick_registration_form_kind(ins_early)
        existing_row = await _get_registration_task_row(db, tenant_id, eid, fk_guess)
        blocked_by = [f"trusted_identity:{identity_prep.block_code}"]
        if existing_row:
            row = existing_row
            row.status = "blocked"
            ch = dict(row.checklist_json) if isinstance(row.checklist_json, dict) else {}
            ch["auto"] = True
            ch["source"] = source
            ch["blocked_by"] = blocked_by
            ch["identity_block_code"] = identity_prep.block_code
            ch["identity_projection_status"] = identity_prep.projection_status
            row.checklist_json = ch
            await db.flush()
            return row.id
        row = await zus_svc.create_zus_workspace_task(
            db,
            tenant_id,
            {
                "employee_id": eid,
                "workspace_lane": "task_queue",
                "task_kind": TASK_KIND_REGISTRATION,
                "title": "ZUS registration (blocked — trusted identity)",
                "form_kind": fk_guess,
                "form_status": "draft",
                "status": "blocked",
                "checklist_json": {
                    "auto": True,
                    "source": source,
                    "blocked_by": blocked_by,
                    "identity_block_code": identity_prep.block_code,
                    "identity_projection_status": identity_prep.projection_status,
                },
            },
        )
        if row:
            await _log_zus_task_auto_created(
                db,
                tenant_id=tenant_id,
                task_id=row.id,
                employee_id=eid,
                form_kind=fk_guess,
                task_kind=TASK_KIND_REGISTRATION,
                period=None,
                source=source,
                actor_id=actor_id,
            )
            return row.id
        return None

    ins = await get_insurance_profile(db, tenant_id, employee_id)
    if not ins or not should_offer_registration_task(ins):
        return None
    fk = pick_registration_form_kind(ins)
    wel = await get_work_eligibility_profile(db, tenant_id, eid)
    payments = await list_payment_requirements(db, tenant_id, eid)
    mode, blocked_by = evaluate_zus_registration_gate(wel, emp, payments)

    existing = await _get_registration_task_row(db, tenant_id, str(employee_id).strip(), fk)

    if mode == "blocked":
        if existing:
            if existing.status != "blocked":
                existing.status = "blocked"
            ch = dict(existing.checklist_json) if isinstance(existing.checklist_json, dict) else {}
            ch["auto"] = True
            ch["source"] = source
            ch["blocked_by"] = blocked_by
            ch["eligibility_status"] = (wel.eligibility_status if wel else None) or "unknown"
            if identity_prep.ready and identity_prep.bindings:
                ch["trusted_identity_bindings"] = identity_prep.bindings
            existing.checklist_json = ch
            await db.flush()
            return existing.id
        row = await zus_svc.create_zus_workspace_task(
            db,
            tenant_id,
            {
                "employee_id": str(employee_id).strip(),
                "workspace_lane": "task_queue",
                "task_kind": TASK_KIND_REGISTRATION,
                "title": "ZUS registration (blocked — work eligibility)",
                "form_kind": fk,
                "form_status": "draft",
                "status": "blocked",
                "checklist_json": {
                    "auto": True,
                    "source": source,
                    "blocked_by": blocked_by,
                    "eligibility_status": (wel.eligibility_status if wel else None) or "unknown",
                },
            },
        )
        if not row:
            return None
        await _log_zus_task_auto_created(
            db,
            tenant_id=tenant_id,
            task_id=row.id,
            employee_id=str(employee_id).strip(),
            form_kind=fk,
            task_kind=TASK_KIND_REGISTRATION,
            period=None,
            source=source,
            actor_id=actor_id,
        )
        return row.id

    # allow
    if existing:
        if existing.status == "blocked":
            existing.status = "pending"
            ch = dict(existing.checklist_json) if isinstance(existing.checklist_json, dict) else {}
            ch["auto"] = True
            ch["source"] = source
            ch.pop("blocked_by", None)
            existing.checklist_json = ch
            await db.flush()
        return existing.id
    row = await zus_svc.create_zus_workspace_task(
        db,
        tenant_id,
        {
            "employee_id": str(employee_id).strip(),
            "workspace_lane": "task_queue",
            "task_kind": TASK_KIND_REGISTRATION,
            "title": "ZUS registration (ZZA)" if fk == "ZZA" else "ZUS registration (ZUA)",
            "form_kind": fk,
            "form_status": "draft",
            "status": "pending",
            "checklist_json": {
                "auto": True,
                "source": source,
                **(
                    {"trusted_identity_bindings": identity_prep.bindings}
                    if identity_prep.ready and identity_prep.bindings
                    else {}
                ),
            },
        },
    )
    if not row:
        return None
    await _log_zus_task_auto_created(
        db,
        tenant_id=tenant_id,
        task_id=row.id,
        employee_id=str(employee_id).strip(),
        form_kind=fk,
        task_kind=TASK_KIND_REGISTRATION,
        period=None,
        source=source,
        actor_id=actor_id,
    )
    return row.id


async def ensure_zus_deregistration_task(
    db: AsyncSession,
    employee_id: str,
    *,
    actor_id: Optional[str] = None,
    source: str = "insurance_profile",
) -> Optional[str]:
    emp = await _get_employee(db, employee_id)
    if not emp:
        return None
    tenant_id = str(emp.tenant_id).strip()
    ins = await get_insurance_profile(db, tenant_id, employee_id)
    if not ins or not insurance_eligible_for_zwua_task(ins):
        return None
    fk = "ZWUA"
    if await _has_active_task(
        db, tenant_id, employee_id, task_kind=TASK_KIND_DEREGISTRATION, form_kind=fk
    ):
        return None
    row = await zus_svc.create_zus_workspace_task(
        db,
        tenant_id,
        {
            "employee_id": str(employee_id).strip(),
            "workspace_lane": "task_queue",
            "task_kind": TASK_KIND_DEREGISTRATION,
            "title": "ZUS deregistration (ZWUA)",
            "form_kind": fk,
            "form_status": "draft",
            "status": "pending",
            "checklist_json": {"auto": True, "source": source},
        },
    )
    if not row:
        return None
    await _log_zus_task_auto_created(
        db,
        tenant_id=tenant_id,
        task_id=row.id,
        employee_id=str(employee_id).strip(),
        form_kind=fk,
        task_kind=TASK_KIND_DEREGISTRATION,
        period=None,
        source=source,
        actor_id=actor_id,
    )
    return row.id


async def ensure_zus_monthly_settlement_task(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    period: str,
    *,
    dry_run: bool = False,
    actor_id: Optional[str] = None,
    source: str = "monthly_cycle",
) -> bool:
    """Return True if a new task was created or would be created (dry_run)."""
    tid = str(tenant_id).strip()
    eid = str(employee_id).strip()
    norm = normalize_monthly_period(period)
    if await _has_active_task(
        db,
        tid,
        eid,
        task_kind=TASK_KIND_MONTHLY_SETTLEMENT,
        form_kind=FORM_KIND_MONTHLY_SETTLEMENT,
        period=norm,
    ):
        return False
    if dry_run:
        return True
    row = await zus_svc.create_zus_workspace_task(
        db,
        tid,
        {
            "employee_id": eid,
            "workspace_lane": "monthly_settlement",
            "task_kind": TASK_KIND_MONTHLY_SETTLEMENT,
            "title": f"ZUS monthly settlement ({norm})",
            "form_kind": FORM_KIND_MONTHLY_SETTLEMENT,
            "form_status": "draft",
            "status": "pending",
            "checklist_json": {"period": norm, "source": source},
        },
    )
    if not row:
        return False
    await _log_zus_task_auto_created(
        db,
        tenant_id=tid,
        task_id=row.id,
        employee_id=eid,
        form_kind=FORM_KIND_MONTHLY_SETTLEMENT,
        task_kind=TASK_KIND_MONTHLY_SETTLEMENT,
        period=norm,
        source=source,
        actor_id=actor_id,
    )
    return True


async def sync_auto_tasks_after_employee_created(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    *,
    actor_id: Optional[str] = None,
) -> None:
    await ensure_zus_registration_task(db, employee_id, actor_id=actor_id, source="employee_create")


async def sync_after_insurance_profile_patch(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    before: dict[str, Any],
    *,
    actor_id: Optional[str] = None,
) -> None:
    ins = await get_insurance_profile(db, tenant_id, employee_id)
    if not ins:
        return
    if insurance_monitored_fields_unchanged(before, ins):
        return
    await ensure_zus_registration_task(db, employee_id, actor_id=actor_id, source="insurance_profile")
    if should_create_zwua_after_insurance_change(before, ins):
        await ensure_zus_deregistration_task(db, employee_id, actor_id=actor_id, source="insurance_profile")
