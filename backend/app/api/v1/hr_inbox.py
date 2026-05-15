"""HR Inbox / Queue API (internal-HR lane). See docs/specs/architecture/hr-inbox-queue-api.md."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.api.v1.handoffs import HandoffOut
from backend.app.api.v1.reminders_v2 import ReminderListResponse, ReminderOut
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.auth.hr_workforce_access import require_hr_workforce_module_access
from backend.app.constants.hr_task_types import HR_TASK_TYPES
from backend.app.db.deps import get_db_with_tenant
from backend.app.services import reminder_tasks
from backend.app.services.hr_documents_hub import list_hr_documents_hub
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_inbox import list_internal_hr_handoffs_for_hr_inbox

router = APIRouter(prefix="/hr", tags=["hr-inbox"])


class HrHandoffInboxItem(BaseModel):
    handoff: HandoffOut
    snapshot: Optional[dict[str, Any]] = None
    workforce_employee_id: Optional[str] = None


class HrHandoffInboxListOut(BaseModel):
    total: int
    items: List[HrHandoffInboxItem]


class HrDocumentQueueItem(BaseModel):
    handoff_id: str
    workforce_employee_id: Optional[str] = None
    candidate_snapshot_summary: dict[str, Any] = Field(default_factory=dict)
    document_type: str
    current_status: str
    required: bool
    snapshot_status: Optional[str] = None
    expires_at: Optional[str] = None
    risk: str
    assignee_user_id: Optional[str] = None
    recommended_action: str


class HrDocumentQueueListOut(BaseModel):
    total: int
    items: List[HrDocumentQueueItem]


class HrDocumentHubRowOut(BaseModel):
    """Unified HR legal document row (workforce HR document context + live document + compliance)."""

    employee_id: str
    employee_name: str
    handoff_id: Optional[str] = None
    document_id: str
    document_type: str
    legal_category: Optional[str] = None
    document_group: Optional[str] = None
    context_type: str
    required: bool
    verification_status: Optional[str] = None
    current_status: str
    expires_at: Optional[str] = None
    risk: str
    source: Optional[str] = None
    missing: bool
    expired: bool
    expiring: bool
    recommended_action: str
    compliance_status: Optional[str] = None
    compliance_cannot_work: Optional[bool] = None
    handoff_snapshot_summary: dict[str, Any] = Field(default_factory=dict)
    assignee_user_id: Optional[str] = None
    work_eligibility_payment_requirement_ids: List[str] = Field(default_factory=list)


class HrDocumentHubListOut(BaseModel):
    total: int
    items: List[HrDocumentHubRowOut]


def _hr_assignee_scope_resolve(
    *,
    assignee_scope: str,
    viewer_id: str,
    viewer_role: str,
) -> str | None:
    scope = (assignee_scope or "mine").strip().lower()
    role = (viewer_role or "").strip().lower()
    if scope == "team" and role in (
        "administrator",
        "supervisor",
        "hr_officer",
        "superadmin",
    ):
        return None
    return str(viewer_id).strip()


@router.get("/handoffs/pending", response_model=HrHandoffInboxListOut)
async def hr_handoffs_pending(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    db, tid = db_tenant
    rows, total = await list_internal_hr_handoffs_for_hr_inbox(
        db,
        tenant_id=str(tid),
        status="pending_review",
        limit=limit,
        offset=offset,
    )
    items = [
        HrHandoffInboxItem(
            handoff=HandoffOut.model_validate(r["handoff"]),
            snapshot=r.get("snapshot"),
            workforce_employee_id=r.get("workforce_employee_id"),
        )
        for r in rows
    ]
    return HrHandoffInboxListOut(total=total, items=items)


@router.get("/handoffs/accepted", response_model=HrHandoffInboxListOut)
async def hr_handoffs_accepted(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    _current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    db, tid = db_tenant
    rows, total = await list_internal_hr_handoffs_for_hr_inbox(
        db,
        tenant_id=str(tid),
        status="accepted",
        limit=limit,
        offset=offset,
    )
    items = [
        HrHandoffInboxItem(
            handoff=HandoffOut.model_validate(r["handoff"]),
            snapshot=r.get("snapshot"),
            workforce_employee_id=r.get("workforce_employee_id"),
        )
        for r in rows
    ]
    return HrHandoffInboxListOut(total=total, items=items)


@router.get("/tasks", response_model=ReminderListResponse)
async def hr_tasks(
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    limit: int = Query(100, ge=1, le=500),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    db, tid = db_tenant
    aid = _hr_assignee_scope_resolve(
        assignee_scope=assignee_scope,
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
    )
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=str(tid),
        assignee_id=aid,
        type_in=list(HR_TASK_TYPES),
        limit=limit,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(
        db, tenant_id=str(tid), reminders=reminders
    )
    return ReminderListResponse(
        items=[
            ReminderOut.from_model(r, payload_merge=merges.get(str(r.id)))
            for r in reminders
        ],
    )


def _horizon_days(v: int) -> int:
    if v not in (7, 30, 60, 90):
        raise HTTPException(status_code=400, detail="horizon_days must be one of 7, 30, 60, 90")
    return v


@router.get("/documents/hub", response_model=HrDocumentHubListOut, tags=["hr-documents"])
async def hr_documents_hub(
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    document_type: Optional[str] = Query(None),
    legal_category: Optional[str] = Query(None),
    employee_id_substr: Optional[str] = Query(None, description="Substring match on workforce employee id"),
    horizon_days: int = Query(30, ge=7, le=90),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    """Read-model over ``workforce_hr_document_contexts`` (linked docs + employee + compliance + handoff snapshot)."""
    hz = _horizon_days(horizon_days)
    db, tid = db_tenant
    rows, total = await list_hr_documents_hub(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        document_type=document_type,
        legal_category=legal_category,
        employee_id_substr=employee_id_substr,
        horizon_days=hz,
        limit=limit,
        offset=offset,
    )
    return HrDocumentHubListOut(
        total=total,
        items=[HrDocumentHubRowOut(**r) for r in rows],
    )


@router.get("/documents/missing", response_model=HrDocumentQueueListOut, tags=["hr-documents"])
async def hr_documents_missing(
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    document_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    handoff_id: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    db, tid = db_tenant
    rows, total = await list_hr_documents_missing(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        document_type=document_type,
        priority=priority,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=limit,
        offset=offset,
    )
    return HrDocumentQueueListOut(
        total=total,
        items=[HrDocumentQueueItem(**r) for r in rows],
    )


@router.get("/documents/expiring", response_model=HrDocumentQueueListOut, tags=["hr-documents"])
async def hr_documents_expiring(
    horizon_days: int = Query(30, ge=7, le=90),
    status: str = Query("all", pattern="^(all|expired|expiring)$"),
    assignee_scope: str = Query("mine", pattern="^(mine|team)$"),
    document_type: Optional[str] = Query(None),
    risk: Optional[str] = Query(None),
    handoff_id: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_roles(Role.hr_officer, Role.administrator, Role.supervisor)),
):
    hz = _horizon_days(horizon_days)
    db, tid = db_tenant
    rows, total = await list_hr_documents_expiring(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        horizon_days=hz,
        status=status,
        document_type=document_type,
        risk=risk,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=limit,
        offset=offset,
    )
    return HrDocumentQueueListOut(
        total=total,
        items=[HrDocumentQueueItem(**r) for r in rows],
    )
