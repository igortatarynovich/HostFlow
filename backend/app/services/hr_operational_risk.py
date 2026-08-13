"""Read-only HR operational risk / SLA signals (v1).

Classifies risks from inbox, document queues, reminder tasks, handoffs,
snapshots (via inbox payloads), and workforce — **not** from ``Candidate`` as SoT.
Does not create tasks, mutate candidates, or change handoff state.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.hr_task_types import HR_TASK_TYPES
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services import reminder_tasks
from backend.app.services.hr_documents_queue import list_hr_documents_expiring, list_hr_documents_missing
from backend.app.services.hr_inbox import list_internal_hr_handoffs_for_hr_inbox
from backend.app.services.reference_service_facade import ReferenceServiceFacade

# v1 thresholds (tune later via tenant settings / env if needed).
HANDOFF_UNACCEPTED_SLA_HOURS = 48
HR_INACTIVITY_HOURS = 168  # 7 days without workforce touch after accept
DOCUMENT_EXPIRING_SOON_DAYS = 7

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def resolve_dashboard_assignee_id(
    *,
    assignee_scope: str,
    viewer_id: str,
    viewer_role: str,
    preset_id: str | None = None,
) -> str | None:
    from backend.app.auth.trust_roles import can_use_team_assignee_scope

    scope = (assignee_scope or "team").strip().lower()
    if scope == "team" and can_use_team_assignee_scope(viewer_role, preset_id):
        return None
    return str(viewer_id).strip()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_from_inbox_row(item: dict[str, Any]) -> dict[str, Any]:
    snap = item.get("snapshot") or {}
    c = snap.get("candidate") or {}
    name = c.get("name") or {}
    return {
        "candidate_id": c.get("id"),
        "first_name": name.get("first_name"),
        "last_name": name.get("last_name"),
    }


def _snapshot_from_queue_row(row: dict[str, Any]) -> dict[str, Any]:
    s = row.get("candidate_snapshot_summary") or {}
    return {
        "candidate_id": s.get("candidate_id"),
        "first_name": s.get("first_name"),
        "last_name": s.get("last_name"),
    }


def _severity_for_sla_breach_hours(over_hours: float) -> str:
    if over_hours > 120:
        return "critical"
    if over_hours > 72:
        return "high"
    if over_hours > 24:
        return "medium"
    return "low"


def _days_until_iso_date(expires_iso: str, today: date) -> int | None:
    try:
        exp = date.fromisoformat(str(expires_iso).split("T", 1)[0])
    except Exception:
        return None
    return (exp - today).days


def _risk_item(
    *,
    risk_code: str,
    severity: str,
    handoff_id: str | None,
    workforce_employee_id: str | None,
    candidate_snapshot: dict[str, Any],
    reason: str,
    recommended_action: str,
    due_at: str | None = None,
    expires_at: str | None = None,
    document_type: str | None = None,
    task_id: str | None = None,
    assignee_user_id: str | None = None,
) -> dict[str, Any]:
    severity_code = ReferenceServiceFacade.normalize_reference_code(domain="risk_severities", value=severity)
    action_code = ReferenceServiceFacade.normalize_reference_code(domain="next_actions", value=recommended_action)
    return {
        "risk_code": risk_code,
        "severity": severity_code,
        "handoff_id": (str(handoff_id).strip() if handoff_id else None),
        "workforce_employee_id": workforce_employee_id,
        "candidate_snapshot": candidate_snapshot,
        "reason": reason,
        "recommended_action": action_code,
        "due_at": due_at,
        "expires_at": expires_at,
        "document_type": document_type,
        "task_id": task_id,
        "assignee_user_id": assignee_user_id,
    }


async def list_operational_risk_items(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    horizon_days: int = 30,
    handoff_id: str | None = None,
    candidate_id: str | None = None,
    preset_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return all v1 risk rows for the tenant scope (read-only)."""
    tid = str(tenant_id).strip()
    scope = (assignee_scope or "team").strip().lower()
    now = _now()
    today = now.date()
    items: list[dict[str, Any]] = []
    aid = resolve_dashboard_assignee_id(
        assignee_scope=scope,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        preset_id=preset_id,
    )

    # --- Pending handoffs past SLA (handoff + snapshot via inbox) ---
    pending_rows, _ = await list_internal_hr_handoffs_for_hr_inbox(
        db, tenant_id=tid, status="pending_review", limit=200, offset=0
    )
    for row in pending_rows:
        h = row["handoff"]
        if handoff_id and str(h.id) != str(handoff_id):
            continue
        if candidate_id and str(h.candidate_id) != str(candidate_id):
            continue
        req_at = h.requested_at
        if not req_at:
            continue
        over_h = (now - req_at).total_seconds() / 3600.0 - HANDOFF_UNACCEPTED_SLA_HOURS
        if over_h <= 0:
            continue
        sev = _severity_for_sla_breach_hours(over_h)
        items.append(
            _risk_item(
                risk_code="handoff_unaccepted_over_sla",
                severity=sev,
                handoff_id=str(h.id),
                workforce_employee_id=row.get("workforce_employee_id"),
                candidate_snapshot=_snapshot_from_inbox_row(row),
                reason=(
                    f"Internal HR handoff pending review for {int((now - req_at).total_seconds() / 3600)}h "
                    f"(SLA {HANDOFF_UNACCEPTED_SLA_HOURS}h)."
                ),
                recommended_action="assign_manager",
                due_at=req_at.isoformat(),
                assignee_user_id=str(h.assigned_to_user_id).strip() if h.assigned_to_user_id else None,
            )
        )

    # --- Missing high-risk documents (queue already encodes risk) ---
    miss_rows, _ = await list_hr_documents_missing(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        document_type=None,
        priority="high",
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=500,
        offset=0,
        preset_id=preset_id,
    )
    for row in miss_rows:
        if str(row.get("risk") or "") != "high":
            continue
        items.append(
            _risk_item(
                risk_code="missing_high_risk_document",
                severity="critical",
                handoff_id=str(row.get("handoff_id") or ""),
                workforce_employee_id=row.get("workforce_employee_id"),
                candidate_snapshot=_snapshot_from_queue_row(row),
                reason=f"Required high-risk document missing or invalid: {row.get('document_type')}.",
                recommended_action="upload_document",
                expires_at=None,
                document_type=str(row.get("document_type") or ""),
                assignee_user_id=row.get("assignee_user_id"),
            )
        )

    # --- Live document expired (all risk levels; code captures compliance) ---
    expired_rows, _ = await list_hr_documents_expiring(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        horizon_days=max(7, min(int(horizon_days), 365)),
        status="expired",
        document_type=None,
        risk=None,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=500,
        offset=0,
        preset_id=preset_id,
    )
    for row in expired_rows:
        items.append(
            _risk_item(
                risk_code="document_expired",
                severity="critical",
                handoff_id=str(row.get("handoff_id") or ""),
                workforce_employee_id=row.get("workforce_employee_id"),
                candidate_snapshot=_snapshot_from_queue_row(row),
                reason=f"Live document expired or marked expired: {row.get('document_type')}.",
                recommended_action="renew_document",
                expires_at=row.get("expires_at"),
                document_type=str(row.get("document_type") or ""),
                assignee_user_id=row.get("assignee_user_id"),
            )
        )

    # --- Expiring within 7 days ---
    soon_rows, _ = await list_hr_documents_expiring(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=scope,
        horizon_days=DOCUMENT_EXPIRING_SOON_DAYS,
        status="expiring",
        document_type=None,
        risk=None,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        limit=500,
        offset=0,
        preset_id=preset_id,
    )
    for row in soon_rows:
        exp = row.get("expires_at")
        days_left = _days_until_iso_date(str(exp), today) if exp else None
        if days_left is not None and days_left <= 2:
            sev = "high"
        elif days_left is not None and days_left <= 5:
            sev = "medium"
        else:
            sev = "low"
        if str(row.get("risk") or "") == "high" and sev == "low":
            sev = "medium"
        items.append(
            _risk_item(
                risk_code="document_expiring_soon",
                severity=sev,
                handoff_id=str(row.get("handoff_id") or ""),
                workforce_employee_id=row.get("workforce_employee_id"),
                candidate_snapshot=_snapshot_from_queue_row(row),
                reason=f"Document expires within {DOCUMENT_EXPIRING_SOON_DAYS} days ({row.get('document_type')}).",
                recommended_action="renew_document",
                expires_at=str(row.get("expires_at")) if exp else None,
                document_type=str(row.get("document_type") or ""),
                assignee_user_id=row.get("assignee_user_id"),
            )
        )

    # --- HR lane tasks overdue ---
    reminders = await reminder_tasks.list_reminders(
        db,
        tenant_id=tid,
        assignee_id=aid,
        type_in=list(HR_TASK_TYPES),
        limit=500,
    )
    overdue_reminders: list[Reminder] = []
    snap_handoff_ids: set[str] = set()
    for r in reminders:
        if r.status in (ReminderStatus.done, ReminderStatus.cancelled):
            continue
        is_overdue_status = str(r.status) == ReminderStatus.overdue
        past_due = r.due_at and r.due_at < now
        if not is_overdue_status and not past_due:
            continue
        md = getattr(r, "metadata_", None) or getattr(r, "payload", None) or {}
        if not isinstance(md, dict):
            md = {}
        hid = str(md.get("handoff_id") or "").strip()
        if handoff_id:
            if not hid or str(handoff_id) != hid:
                continue
        if candidate_id:
            et = str(getattr(r, "entity_type", "") or "")
            eid = str(getattr(r, "entity_id", "") or "")
            if et != "candidate" or eid != str(candidate_id):
                continue
        overdue_reminders.append(r)
        if hid:
            snap_handoff_ids.add(hid)

    snap_payload_by_hid: dict[str, dict[str, Any]] = {}
    if snap_handoff_ids:
        snap_rows = (
            await db.execute(
                select(CandidateHandoffSnapshot).where(
                    CandidateHandoffSnapshot.handoff_id.in_(list(snap_handoff_ids))
                )
            )
        ).scalars().all()
        for s in snap_rows:
            snap_payload_by_hid[str(s.handoff_id)] = dict(s.payload or {})

    for r in overdue_reminders:
        md = getattr(r, "metadata_", None) or getattr(r, "payload", None) or {}
        if not isinstance(md, dict):
            md = {}
        hid = str(md.get("handoff_id") or "").strip()
        days_late = 0
        if r.due_at:
            days_late = max(0, int((now - r.due_at).total_seconds() // 86400))
        is_overdue_status = str(r.status) == ReminderStatus.overdue
        if days_late >= 7 or is_overdue_status:
            sev = "high"
        elif days_late >= 3:
            sev = "medium"
        else:
            sev = "low"
        snap_pl = snap_payload_by_hid.get(hid, {})
        items.append(
            _risk_item(
                risk_code="onboarding_task_overdue",
                severity=sev,
                handoff_id=hid,
                workforce_employee_id=None,
                candidate_snapshot=_snapshot_from_inbox_row({"snapshot": snap_pl}),
                reason=f"HR task '{r.title or r.type}' is past due ({days_late}d).",
                recommended_action="contact_employee",
                due_at=r.due_at.isoformat() if r.due_at else None,
                task_id=str(r.id),
                assignee_user_id=str(r.assignee_id).strip() if r.assignee_id else None,
            )
        )

    # --- Accepted handoff + stale workforce row (read handoff + workforce only) ---
    inact_cutoff = now - timedelta(hours=HR_INACTIVITY_HOURS)
    wf_rows = (
        await db.execute(select(WorkforceEmployee).where(WorkforceEmployee.tenant_id == tid))
    ).scalars().all()
    for emp in wf_rows:
        hid = (emp.meta or {}).get("internal_hr_handoff_id")
        if not hid:
            continue
        if handoff_id and str(hid) != str(handoff_id):
            continue
        ho = await db.get(CandidateHandoff, str(hid))
        if (
            ho is None
            or str(ho.agency_tenant_id) != tid
            or str(ho.destination or "") != "internal_hr"
            or str(ho.status or "") != "accepted"
        ):
            continue
        if candidate_id and str(ho.candidate_id) != str(candidate_id):
            continue
        reviewed = ho.reviewed_at or ho.accepted_at
        if not reviewed or reviewed > inact_cutoff:
            continue
        if emp.updated_at >= inact_cutoff:
            continue
        snap = emp.candidate_snapshot if isinstance(emp.candidate_snapshot, dict) else {}
        items.append(
            _risk_item(
                risk_code="hr_inactivity",
                severity="medium",
                handoff_id=str(ho.id),
                workforce_employee_id=str(emp.id),
                candidate_snapshot={
                    "candidate_id": snap.get("candidate_id") or ho.candidate_id,
                    "first_name": snap.get("first_name"),
                    "last_name": snap.get("last_name"),
                },
                reason=(
                    f"No workforce updates for {HR_INACTIVITY_HOURS}h after handoff acceptance "
                    f"(employee record stale)."
                ),
                recommended_action="assign_manager",
                due_at=None,
                assignee_user_id=str(ho.assigned_to_user_id).strip() if ho.assigned_to_user_id else None,
            )
        )

    # Dedup identical keys (same code + handoff + doc type + task)
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for it in items:
        key = (
            it["risk_code"],
            it.get("handoff_id"),
            it.get("document_type"),
            it.get("task_id"),
            it.get("expires_at"),
            it.get("due_at"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    deduped.sort(
        key=lambda x: (
            -SEVERITY_RANK.get(str(x.get("severity")), 0),
            str(x.get("handoff_id") or ""),
            str(x.get("expires_at") or ""),
            str(x.get("due_at") or ""),
        )
    )
    return deduped


async def build_risk_summary(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str,
    preview_cap: int = 8,
    horizon_days: int = 30,
    preset_id: str | None = None,
) -> dict[str, Any]:
    """Compact risk block for ``GET /hr/dashboard/summary``."""
    all_items = await list_operational_risk_items(
        db,
        tenant_id=tenant_id,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=assignee_scope,
        horizon_days=horizon_days,
        handoff_id=None,
        candidate_id=None,
        preset_id=preset_id,
    )
    by_code: dict[str, int] = {}
    by_severity: dict[str, int] = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
    for it in all_items:
        code = str(it.get("risk_code") or "")
        by_code[code] = by_code.get(code, 0) + 1
        sev = ReferenceServiceFacade.normalize_reference_code(
            domain="risk_severities",
            value=str(it.get("severity") or "info"),
        )
        by_severity[sev] = by_severity.get(sev, 0) + 1
    return {
        "total": len(all_items),
        "counts_by_code": by_code,
        "counts_by_severity": by_severity,
        "preview": all_items[:preview_cap],
    }


async def list_scored_risks_page(
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
    preset_id: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Paginated operational risks for ``GET /hr/dashboard/high-risk``."""
    rows = await list_operational_risk_items(
        db,
        tenant_id=tenant_id,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=assignee_scope,
        horizon_days=horizon_days,
        handoff_id=handoff_id,
        candidate_id=candidate_id,
        preset_id=preset_id,
    )
    total = len(rows)
    page = rows[max(0, offset) : max(0, offset) + max(1, min(limit, 200))]
    return page, total
