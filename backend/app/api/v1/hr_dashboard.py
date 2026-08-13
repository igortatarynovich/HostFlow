"""HR Dashboard API — aggregates over inbox, document queues, and HR tasks."""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.auth.hr_workforce_access import require_hr_workforce_module_access
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.hr_dashboard import (
    build_compliance,
    build_summary,
    build_workload,
    list_high_risk_expiring,
)

router = APIRouter(prefix="/hr/dashboard", tags=["hr-dashboard"])


class DashboardCountsOut(BaseModel):
    handoffs_pending: int
    handoffs_accepted: int
    hr_tasks_open: int
    documents_missing: int
    documents_high_risk_expiring: int


class DashboardPreviewsOut(BaseModel):
    pending_handoffs: list[dict[str, Any]]
    high_risk_expiring_documents: list[dict[str, Any]]
    missing_documents: list[dict[str, Any]]
    open_hr_tasks: list[dict[str, Any]]


class HrOperationalRiskItemOut(BaseModel):
    risk_code: str
    severity: Literal["low", "medium", "high", "critical"]
    handoff_id: Optional[str] = None
    workforce_employee_id: Optional[str] = None
    assignee_user_id: Optional[str] = None
    candidate_snapshot: dict[str, Any] = Field(default_factory=dict)
    reason: str
    recommended_action: str
    due_at: Optional[str] = None
    expires_at: Optional[str] = None
    document_type: Optional[str] = None
    task_id: Optional[str] = None


class DashboardRiskSummaryOut(BaseModel):
    total: int
    counts_by_code: dict[str, int] = Field(default_factory=dict)
    counts_by_severity: dict[str, int] = Field(default_factory=dict)
    preview: List[HrOperationalRiskItemOut]


class HrDashboardSummaryOut(BaseModel):
    schema_version: Literal[1] = 1
    counts: DashboardCountsOut
    previews: DashboardPreviewsOut
    risk_summary: DashboardRiskSummaryOut


class HrDashboardHighRiskOut(BaseModel):
    schema_version: Literal[2] = 2
    total: int
    items: List[HrOperationalRiskItemOut]


class WorkloadGroupOut(BaseModel):
    assignee_user_id: Optional[str] = None
    open_task_count: int
    tasks: list[dict[str, Any]]


class HrDashboardWorkloadOut(BaseModel):
    schema_version: Literal[1] = 1
    groups: list[WorkloadGroupOut]


class ComplianceDocTypeGroupOut(BaseModel):
    document_type: str
    count: int
    items: list[dict[str, Any]]


class ComplianceCandidateGroupOut(BaseModel):
    candidate_id: Optional[str] = None
    handoff_id: str
    missing_count: int
    document_types: list[str]
    items: list[dict[str, Any]]


class HrDashboardComplianceOut(BaseModel):
    schema_version: Literal[1] = 1
    total: int
    by_document_type: list[ComplianceDocTypeGroupOut]
    by_candidate: list[ComplianceCandidateGroupOut]


@router.get("/summary", response_model=HrDashboardSummaryOut)
async def hr_dashboard_summary(
    assignee_scope: str = Query("team", pattern="^(mine|team)$"),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_trust_write()),
):
    db, tid = db_tenant
    raw = await build_summary(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
    )
    rs = raw["risk_summary"]
    return HrDashboardSummaryOut(
        schema_version=1,
        counts=DashboardCountsOut(**raw["counts"]),
        previews=DashboardPreviewsOut(**raw["previews"]),
        risk_summary=DashboardRiskSummaryOut(
            total=int(rs["total"]),
            counts_by_code=dict(rs.get("counts_by_code") or {}),
            counts_by_severity=dict(rs.get("counts_by_severity") or {}),
            preview=[HrOperationalRiskItemOut(**x) for x in (rs.get("preview") or [])],
        ),
    )


@router.get("/high-risk", response_model=HrDashboardHighRiskOut)
async def hr_dashboard_high_risk(
    horizon_days: int = Query(30, ge=7, le=90),
    assignee_scope: str = Query("team", pattern="^(mine|team)$"),
    handoff_id: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_trust_write()),
):
    db, tid = db_tenant
    rows, total = await list_high_risk_expiring(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        horizon_days=horizon_days,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=limit,
        offset=offset,
    )
    return HrDashboardHighRiskOut(
        schema_version=2,
        total=total,
        items=[HrOperationalRiskItemOut(**r) for r in rows],
    )


@router.get("/workload", response_model=HrDashboardWorkloadOut)
async def hr_dashboard_workload(
    assignee_scope: str = Query("team", pattern="^(mine|team)$"),
    tasks_per_assignee: int = Query(10, ge=1, le=50),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_trust_write()),
):
    db, tid = db_tenant
    raw = await build_workload(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        limit_per_group=tasks_per_assignee,
    )
    return HrDashboardWorkloadOut(
        schema_version=1,
        groups=[WorkloadGroupOut(**g) for g in raw["groups"]],
    )


@router.get("/compliance", response_model=HrDashboardComplianceOut)
async def hr_dashboard_compliance(
    assignee_scope: str = Query("team", pattern="^(mine|team)$"),
    preview_cap: int = Query(10, ge=1, le=50),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    _: UserCtx = Depends(require_hr_workforce_module_access),
    __: str = Depends(require_trust_write()),
):
    db, tid = db_tenant
    raw = await build_compliance(
        db,
        tenant_id=str(tid),
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
        assignee_scope=assignee_scope,
        preview_cap=preview_cap,
    )
    return HrDashboardComplianceOut(
        schema_version=1,
        total=raw["total"],
        by_document_type=[ComplianceDocTypeGroupOut(**x) for x in raw["by_document_type"]],
        by_candidate=[ComplianceCandidateGroupOut(**x) for x in raw["by_candidate"]],
    )
