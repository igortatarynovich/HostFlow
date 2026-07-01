"""HR acceptance lifecycle orchestrator (Stage B): single entry for accept / approve side effects."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.services import workforce_employees as we_svc
from backend.app.services.handoff import (
    _ensure_internal_hr_handoff_checklist_activities,
)
from backend.app.services.tenant_hr_flags import delayed_hr_workforce_creation_enabled
from backend.app.services.workforce_hr_operational_context import ensure_hr_operational_context
from backend.app.services.workforce_hr_operational_context import ensure_hr_document_links
from backend.app.services.workforce_hr_review import (
    HR_REVIEW_STATUS_APPROVED,
    approve_hr_review_record,
    ensure_hr_review_for_handoff,
    get_hr_review_by_handoff,
)


async def accept_internal_hr_handoff(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    candidate: Candidate,
    reviewed_by_user_id: str | None,
    tenant_id: str,
) -> WorkforceEmployee | None:
    """After handoff marked accepted: legacy creates workforce immediately; delayed only opens HR review."""
    tid = str(handoff.agency_tenant_id).strip()
    actor = str(reviewed_by_user_id or handoff.requested_by_user_id or "").strip() or "system"

    if await delayed_hr_workforce_creation_enabled(db, tid):
        review = await ensure_hr_review_for_handoff(
            db,
            tenant_id=tid,
            handoff_id=str(handoff.id),
            candidate_id=str(candidate.id),
        )
        await ensure_hr_document_links(
            db,
            tenant_id=tid,
            candidate_id=str(candidate.id),
            linked_entity_type="workforce_hr_review",
            linked_entity_id=str(review.id),
        )
        return None

    emp = await we_svc.handoff_from_candidate(
        db,
        tid,
        candidate,
        hire_date=None,
        actor_user_id=actor,
    )
    md = dict(emp.meta or {})
    md["internal_hr_handoff_id"] = handoff.id
    emp.meta = md
    await db.flush()
    await ensure_hr_operational_context(db, tid, emp)
    await _ensure_internal_hr_handoff_checklist_activities(
        db,
        tenant_id=tid,
        candidate_id=str(handoff.candidate_id),
        handoff_id=handoff.id,
        assignee_user_id=handoff.assigned_to_user_id,
        created_by_user_id=actor,
    )
    await db.flush()
    return emp


async def approve_employment_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    actor_user_id: str,
) -> tuple[WorkforceEmployee, WorkforceHrReview]:
    """Materialize workforce + HR bundle, then mark review approved (delayed-workforce path)."""
    tid = str(tenant_id).strip()
    hid = str(handoff_id).strip()
    review = await get_hr_review_by_handoff(db, tid, hid)
    if not review:
        raise ValueError("HR_REVIEW_NOT_FOUND")

    handoff = await db.get(CandidateHandoff, hid)
    if not handoff:
        raise ValueError("HANDOFF_NOT_FOUND")
    cand = await db.get(Candidate, str(handoff.candidate_id))
    if not cand:
        raise ValueError("CANDIDATE_NOT_FOUND")

    emp: WorkforceEmployee | None = None
    if review.employee_id:
        emp = await we_svc.get_employee(db, tid, str(review.employee_id))
    if emp is None:
        emp = await we_svc.handoff_from_candidate(
            db,
            tid,
            cand,
            hire_date=None,
            actor_user_id=actor_user_id,
            seed_hr_bundle=True,
        )
        md = dict(emp.meta or {})
        md["internal_hr_handoff_id"] = handoff.id
        emp.meta = md
        review.employee_id = emp.id
        if not review.candidate_id:
            review.candidate_id = str(cand.id)
        await db.flush()
        await ensure_hr_operational_context(db, tid, emp)
        await _ensure_internal_hr_handoff_checklist_activities(
            db,
            tenant_id=tid,
            candidate_id=str(handoff.candidate_id),
            handoff_id=handoff.id,
            assignee_user_id=handoff.assigned_to_user_id,
            created_by_user_id=actor_user_id,
        )
        await db.flush()
    else:
        await we_svc.ensure_hr_profiles_bundle(db, tid, emp.id)
        from backend.app.services.workforce_zus_task_autocreate import sync_auto_tasks_after_employee_created

        await sync_auto_tasks_after_employee_created(db, tid, emp.id)

    review = await approve_hr_review_record(db, tenant_id=tid, review=review, employee=emp, actor_user_id=actor_user_id)
    return emp, review
