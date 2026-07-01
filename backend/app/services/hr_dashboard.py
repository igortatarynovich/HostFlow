"""HR dashboard aggregates — inbox, document queues, HR reminder tasks only."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.hr_task_types import HR_TASK_TYPES
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services import reminder_tasks
from backend.app.services.candidate_lifecycle import exclude_completed_candidate_entities_clause
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_inbox import list_internal_hr_handoffs_for_hr_inbox
from backend.app.services.hr_operational_risk import (
    build_risk_summary,
    list_scored_risks_page,
    resolve_dashboard_assignee_id,
)
from backend.app.services.lead_lifecycle import exclude_completed_lead_entities_clause

PREVIEW_CAP = 8

# Open / actionable reminder rows (legacy statuses still possible in DB).
OPEN_TASK_STATUSES: tuple[str, ...] = (
    ReminderStatus.planned,
    ReminderStatus.in_progress,
    ReminderStatus.overdue,
    ReminderStatus.new,
    ReminderStatus.pending,
    ReminderStatus.sent,
)


async def count_open_hr_tasks(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str | None,
) -> int:
    stmt = select(func.count()).select_from(Reminder).where(
        Reminder.tenant_id == str(tenant_id).strip(),
        Reminder.type.in_(list(HR_TASK_TYPES)),
        Reminder.status.in_(list(OPEN_TASK_STATUSES)),
    )
    if assignee_id:
        stmt = stmt.where(Reminder.assignee_id == str(assignee_id).strip())
    stmt = stmt.where(
        and_(
            exclude_completed_candidate_entities_clause(
                str(tenant_id).strip(),
                entity_type_col=Reminder.entity_type,
                entity_id_col=Reminder.entity_id,
            ),
            exclude_completed_lead_entities_clause(
                str(tenant_id).strip(),
                entity_type_col=Reminder.entity_type,
                entity_id_col=Reminder.entity_id,
            ),
        )
    )
    row = (await db.execute(stmt)).scalar_one()
    return int(row or 0)


async def build_summary(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
) -> dict[str, Any]:
    tid = str(tenant_id).strip()
    scope = (assignee_scope or "team").strip().lower()

    _, pending_total = await list_internal_hr_handoffs_for_hr_inbox(
        db, tenant_id=tid, status="pending_review", limit=1, offset=0
    )
    _, accepted_total = await list_internal_hr_handoffs_for_hr_inbox(
        db, tenant_id=tid, status="accepted", limit=1, offset=0
    )

    aid = resolve_dashboard_assignee_id(
        assignee_scope=scope, viewer_id=viewer_id, viewer_role=viewer_role
    )
    hr_tasks_open = await count_open_hr_tasks(db, tenant_id=tid, assignee_id=aid)

    _, missing_total = await list_hr_documents_missing(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        document_type=None,
        priority=None,
        handoff_id=None,
        candidate_id=None,
        limit=1,
        offset=0,
    )
    _, high_risk_expiring_total = await list_hr_documents_expiring(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        horizon_days=90,
        status="all",
        document_type=None,
        risk="high",
        handoff_id=None,
        candidate_id=None,
        limit=1,
        offset=0,
    )

    pending_rows, _ = await list_internal_hr_handoffs_for_hr_inbox(
        db, tenant_id=tid, status="pending_review", limit=PREVIEW_CAP, offset=0
    )
    exp_preview, _ = await list_hr_documents_expiring(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        horizon_days=90,
        status="all",
        document_type=None,
        risk="high",
        handoff_id=None,
        candidate_id=None,
        limit=PREVIEW_CAP,
        offset=0,
    )
    miss_preview, _ = await list_hr_documents_missing(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        document_type=None,
        priority=None,
        handoff_id=None,
        candidate_id=None,
        limit=PREVIEW_CAP,
        offset=0,
    )

    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=tid,
        assignee_id=aid,
        type_in=list(HR_TASK_TYPES),
        status_in=list(OPEN_TASK_STATUSES),
        limit=PREVIEW_CAP,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(
        db, tenant_id=tid, reminders=reminders
    )
    task_preview = []
    for r in reminders:
        task_preview.append(
            {
                "id": str(r.id),
                "type": str(r.type),
                "title": r.title,
                "assignee_user_id": r.assignee_id,
                "due_at": r.due_at.isoformat() if r.due_at else None,
                "status": str(r.status),
                "payload_merge": merges.get(str(r.id)),
            }
        )

    risk_summary = await build_risk_summary(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        preview_cap=PREVIEW_CAP,
        horizon_days=90,
    )

    return {
        "schema_version": 1,
        "counts": {
            "handoffs_pending": int(pending_total),
            "handoffs_accepted": int(accepted_total),
            "hr_tasks_open": int(hr_tasks_open),
            "documents_missing": int(missing_total),
            "documents_high_risk_expiring": int(high_risk_expiring_total),
        },
        "previews": {
            "pending_handoffs": [
                {
                    "handoff_id": str(r["handoff"].id),
                    "status": str(r["handoff"].status),
                    "workforce_employee_id": r.get("workforce_employee_id"),
                }
                for r in pending_rows
            ],
            "high_risk_expiring_documents": exp_preview,
            "missing_documents": miss_preview,
            "open_hr_tasks": task_preview,
        },
        "risk_summary": risk_summary,
    }


async def list_high_risk_expiring(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    horizon_days: int,
    handoff_id: str | None,
    candidate_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    return await list_scored_risks_page(
        db,
        tenant_id=str(tenant_id).strip(),
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=(assignee_scope or "team").strip().lower(),
        horizon_days=horizon_days,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=limit,
        offset=offset,
    )


def _task_row(r: Reminder, merge: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "type": str(r.type),
        "title": r.title,
        "status": str(r.status),
        "due_at": r.due_at.isoformat() if r.due_at else None,
        "assignee_user_id": r.assignee_id,
        "payload_merge": merge,
    }


async def build_workload(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    limit_per_group: int,
) -> dict[str, Any]:
    tid = str(tenant_id).strip()
    scope = (assignee_scope or "team").strip().lower()
    aid = resolve_dashboard_assignee_id(
        assignee_scope=scope, viewer_id=viewer_id, viewer_role=viewer_role
    )
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=tid,
        assignee_id=aid,
        type_in=list(HR_TASK_TYPES),
        status_in=list(OPEN_TASK_STATUSES),
        limit=500,
    )
    merges = await reminder_tasks.build_reminder_payload_enrichments_for_api(
        db, tenant_id=tid, reminders=reminders
    )
    buckets: dict[str | None, list[Reminder]] = defaultdict(list)
    for r in reminders:
        key = str(r.assignee_id).strip() if r.assignee_id else None
        buckets[key].append(r)

    groups: list[dict[str, Any]] = []
    for assignee_key in sorted(buckets.keys(), key=lambda x: (x is None, x or "")):
        all_rows = buckets[assignee_key]
        preview = [
            _task_row(r, merges.get(str(r.id))) for r in all_rows[:limit_per_group]
        ]
        groups.append(
            {
                "assignee_user_id": assignee_key,
                "open_task_count": len(all_rows),
                "tasks": preview,
            }
        )
    return {"schema_version": 1, "groups": groups}


async def build_compliance(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    preview_cap: int,
) -> dict[str, Any]:
    tid = str(tenant_id).strip()
    scope = (assignee_scope or "team").strip().lower()
    rows, total = await list_hr_documents_missing(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        document_type=None,
        priority=None,
        handoff_id=None,
        candidate_id=None,
        limit=500,
        offset=0,
    )

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cand: dict[tuple[str | None, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        dt = str(row.get("document_type") or "")
        by_type[dt].append(row)
        summ = row.get("candidate_snapshot_summary") or {}
        cid = summ.get("candidate_id")
        hid = str(row.get("handoff_id") or "")
        by_cand[(str(cid) if cid else None, hid)].append(row)

    by_document_type = []
    for doc_type in sorted(by_type.keys()):
        items = by_type[doc_type]
        by_document_type.append(
            {
                "document_type": doc_type,
                "count": len(items),
                "items": items[:preview_cap],
            }
        )

    by_candidate = []
    for (cid, hid), items in sorted(by_cand.items(), key=lambda x: (x[0][0] or "", x[0][1])):
        types = sorted({str(i.get("document_type") or "") for i in items})
        by_candidate.append(
            {
                "candidate_id": cid,
                "handoff_id": hid,
                "missing_count": len(items),
                "document_types": types,
                "items": items[:preview_cap],
            }
        )

    return {
        "schema_version": 1,
        "total": int(total),
        "by_document_type": by_document_type,
        "by_candidate": by_candidate,
    }
