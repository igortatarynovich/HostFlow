"""Handoff service: create, accept, reject, return."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import and_, or_, select, func
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.constants.hr_task_types import HANDOFF_HR_CHECKLIST, INTERNAL_HR_HANDOFF_PENDING
from backend.app.models.access import UserCompanyAccess
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.tenant import TenantLink
from backend.app.models import User
from backend.app.models.user import Role as UserRole
from backend.app.services.audit import log_audit_event
from backend.app.services.events import EventAudience, emit_event
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantType
from backend.app.services.tenant_links import get_tenant_link, list_links_for_agency
from backend.app.models.activity import Activity, ActivityStatus
from backend.app.services import workforce_employees as workforce_employees_service
from backend.app.services.recruitment_application_service import get_application_for_handoff
from backend.app.services.recruitment_application_lifecycle import (
    InvalidRecruitmentApplicationTransition,
    normalize_application_status,
    set_recruitment_application_status,
)
from backend.app.services.recruitment_handoff_write_guard import (
    is_recruitment_recruiter_write_locked_by_handoff,
)
from backend.app.services.handoff_snapshot import persist_handoff_create_snapshot


def _extract_session(db_like) -> AsyncSession:
    if isinstance(db_like, AsyncSession):
        return db_like
    if isinstance(db_like, tuple):
        for item in db_like:
            if isinstance(item, AsyncSession):
                return item
    raise TypeError("AsyncSession not found in provided dependency")


async def get_pending_handoff(
    db: AsyncSession,
    candidate_id: str,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
) -> CandidateHandoff | None:
    """Get pending handoff for (candidate, client)."""
    stmt = select(CandidateHandoff).where(
        CandidateHandoff.candidate_id == candidate_id,
        CandidateHandoff.status == "pending_review",
    )
    if client_company_id:
        stmt = stmt.where(CandidateHandoff.client_company_id == client_company_id)
    elif client_tenant_id:
        stmt = stmt.where(CandidateHandoff.client_tenant_id == client_tenant_id)
    else:
        return None
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def get_pending_handoff_for_agency(
    db: AsyncSession,
    candidate_id: str,
    agency_tenant_id: str,
) -> CandidateHandoff | None:
    """Get pending handoff for candidate created by this agency (any client)."""
    stmt = (
        select(CandidateHandoff)
        .where(
            CandidateHandoff.candidate_id == candidate_id,
            CandidateHandoff.agency_tenant_id == agency_tenant_id,
            CandidateHandoff.status == "pending_review",
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def unlock_pending_handoff_for_recruitment_close(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
    actor_user_id: str | None,
    close_stage: str,
) -> None:
    """Return a *pending* handoff when recruiter closes dossier (rejected/declined).

    Does not mutate ``Candidate.stage`` — caller sets the terminal stage in the same transaction.
    """
    pending = await get_pending_handoff_for_agency(db, candidate_id, agency_tenant_id)
    if pending is None:
        return

    reason = f"Recruitment closed: {str(close_stage or '').strip() or 'terminal'}"
    now = datetime.now(timezone.utc)
    pending.status = "returned"
    pending.return_reason = reason
    pending.returned_reason = reason
    pending.returned_by_user_id = actor_user_id
    pending.reviewed_by_user_id = actor_user_id
    pending.reviewed_at = now
    pending.locked_at = None
    await db.flush()

    dest = (getattr(pending, "destination", None) or "client_portal").strip().lower()
    if dest == "internal_hr":
        await _terminalize_internal_hr_pending_handoff_activity(
            db,
            tenant_id=str(pending.agency_tenant_id),
            candidate_id=str(pending.candidate_id),
            handoff_id=pending.id,
            terminal_status=ActivityStatus.cancelled,
            completed_at=now,
        )


async def get_accepted_handoff_for_agency(
    db: AsyncSession,
    candidate_id: str,
    agency_tenant_id: str,
) -> CandidateHandoff | None:
    """Get accepted handoff for candidate from this agency (any client)."""
    stmt = (
        select(CandidateHandoff)
        .where(
            CandidateHandoff.candidate_id == candidate_id,
            CandidateHandoff.agency_tenant_id == agency_tenant_id,
            CandidateHandoff.status == "accepted",
        )
        .order_by(CandidateHandoff.reviewed_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_accepted_handoff(
    db: AsyncSession,
    candidate_id: str,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
) -> CandidateHandoff | None:
    """Get accepted (active) handoff for candidate."""
    stmt = select(CandidateHandoff).where(
        CandidateHandoff.candidate_id == candidate_id,
        CandidateHandoff.status == "accepted",
    )
    if client_company_id:
        stmt = stmt.where(CandidateHandoff.client_company_id == client_company_id)
    elif client_tenant_id:
        stmt = stmt.where(CandidateHandoff.client_tenant_id == client_tenant_id)
    else:
        stmt = stmt.where(
            or_(
                CandidateHandoff.client_company_id.isnot(None),
                CandidateHandoff.client_tenant_id.isnot(None),
            )
        )
    result = await db.execute(stmt.order_by(CandidateHandoff.reviewed_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def has_accepted_handoff(
    db: AsyncSession,
    candidate_id: str,
    *,
    client_tenant_id: str | None = None,
    client_company_id: str | None = None,
) -> bool:
    """True if there is an accepted handoff for (candidate, client)."""
    h = await get_accepted_handoff(
        db,
        candidate_id,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
    )
    return h is not None


async def _client_owns_accepted_handoff(
    db: AsyncSession,
    candidate_id: str,
    tenant_id: str,
) -> bool:
    """True if tenant_id is client in some accepted handoff for this candidate."""
    # Direct: handoff.client_tenant_id == tenant_id
    h = await get_accepted_handoff(db, candidate_id, client_tenant_id=tenant_id)
    if h:
        return True
    # Via handoff_include_company_id: handoff to company linked to tenant
    row = await db.execute(
        select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == tenant_id,
            TenantLink.handoff_include_company_id.isnot(None),
        ).limit(1)
    )
    inc = row.scalar_one_or_none()
    if inc:
        inc_id = str(inc) if inc else None
        h2 = await get_accepted_handoff(db, candidate_id, client_company_id=inc_id)
        if h2:
            return True
    return False


async def can_agency_edit(
    db: AsyncSession,
    candidate_id: str,
    agency_tenant_id: str,
) -> bool:
    """Agency-tenant users may edit candidate dossier unless HR workforce or handoff locks recruitment."""
    from backend.app.services.candidate_workforce_lock import is_candidate_locked_by_workforce

    cand = await db.get(Candidate, candidate_id)
    if not cand or str(cand.tenant_id) != agency_tenant_id:
        return False
    if await is_candidate_locked_by_workforce(
        db, tenant_id=agency_tenant_id, candidate_id=candidate_id
    ):
        return False
    locked, _ = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=agency_tenant_id, candidate_id=candidate_id
    )
    return not locked


async def can_client_edit(
    db: AsyncSession,
    candidate_id: str,
    client_tenant_id: str,
) -> bool:
    """Client can edit candidate only when they have an accepted handoff."""
    return await _client_owns_accepted_handoff(db, candidate_id, client_tenant_id)


async def client_has_accepted_handoff(
    db: AsyncSession,
    candidate_id: str,
    client_tenant_id: str,
) -> bool:
    """True if client tenant has an accepted handoff for this candidate."""
    return await _client_owns_accepted_handoff(db, candidate_id, client_tenant_id)


async def is_client_tenant(db: AsyncSession, tenant_id: str) -> bool:
    """True if tenant is a client (company type)."""
    session = _extract_session(db)
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        return False
    return getattr(tenant, "type", None) == TenantType.company


async def is_client_tenant_for_list(db: AsyncSession, tenant_id: str) -> bool:
    """True if tenant should be treated as client in candidates list scope.

    Important: we intentionally rely only on tenant type.
    `TenantLink` records configure handoff/link access, but must not globally
    flip an agency workspace into client view.
    """
    return await is_client_tenant(db, tenant_id)


async def has_pending_handoff_for_client(
    db: AsyncSession,
    candidate_id: str,
    client_tenant_id: str,
) -> bool:
    """True if client has a pending handoff for this candidate (Do-procesowania context = full data)."""
    h = await get_pending_handoff(db, candidate_id, client_tenant_id=client_tenant_id)
    if h:
        return True
    row = await db.execute(
        select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == client_tenant_id,
            TenantLink.handoff_include_company_id.isnot(None),
        ).limit(1)
    )
    inc = row.scalar_one_or_none()
    if inc:
        inc_id = str(inc) if inc else None
        h2 = await get_pending_handoff(db, candidate_id, client_company_id=inc_id)
        if h2:
            return True
    return False


def _normalize_handoff_destination(raw: str | None) -> str:
    s = (raw or "client_portal").strip().lower()
    if s in ("internal_hr", "hr", "internal"):
        return "internal_hr"
    return "client_portal"


def _handoff_product_type(destination: str, client_tenant_id: str | None) -> str:
    """Product classifier: internal HR vs client account (tenant) vs portal (company-only)."""
    if destination == "internal_hr":
        return "internal_hr"
    if client_tenant_id:
        return "client_account"
    return "client_portal"


async def _sync_application_after_handoff_created(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    application_id: str | None,
) -> Optional[str]:
    """Mark recruitment intent as ready_for_handoff when handoff is opened."""
    app = await get_application_for_handoff(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        vacancy_id=getattr(candidate, "vacancy_id", None),
        application_id=application_id,
    )
    if not app:
        return None
    cur = normalize_application_status(app.status)
    if cur in ("applied", "in_review", "shortlisted"):
        try:
            set_recruitment_application_status(app, "ready_for_handoff")
        except InvalidRecruitmentApplicationTransition:
            pass
    return str(app.id)


async def _sync_application_after_handoff_accepted(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: str | None,
    application_id: str | None,
) -> None:
    """Recruitment intent closed from agency perspective: handed_off."""
    app = await get_application_for_handoff(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        application_id=application_id,
    )
    if not app:
        return
    cur = normalize_application_status(app.status)
    if cur in ("applied", "in_review", "shortlisted"):
        try:
            set_recruitment_application_status(app, "ready_for_handoff")
        except InvalidRecruitmentApplicationTransition:
            pass
    try:
        set_recruitment_application_status(app, "handed_off")
    except InvalidRecruitmentApplicationTransition:
        pass


async def _sync_application_after_handoff_returned(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    vacancy_id: str | None,
    application_id: str | None,
) -> None:
    app = await get_application_for_handoff(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        application_id=application_id,
    )
    if not app:
        return
    try:
        set_recruitment_application_status(app, "returned_for_revision")
    except InvalidRecruitmentApplicationTransition:
        pass


async def _first_active_hr_officer_user_id(db: AsyncSession, tenant_id: str) -> str | None:
    """Prefer the most recently created active HR officer (stable with dev seed + test fixtures)."""
    res = await db.execute(
        select(User.id)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.hr_officer,
            User.is_active.is_(True),
        )
        .order_by(User.created_at.desc().nulls_last(), User.id.desc())
        .limit(1)
    )
    row = res.first()
    return str(row[0]) if row and row[0] else None


async def _resolve_internal_hr_activity_assignee(
    db: AsyncSession,
    *,
    tenant_id: str,
    assigned_to_user_id: str | None,
) -> str | None:
    aid = (assigned_to_user_id or "").strip()
    if aid:
        return aid
    return await _first_active_hr_officer_user_id(db, tenant_id)


async def _ensure_internal_hr_pending_handoff_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    handoff_id: str,
    assigned_to_user_id: str | None,
    created_by_user_id: str,
) -> None:
    """HR queue: idempotent task for a new internal-HR handoff awaiting review."""
    assignee = await _resolve_internal_hr_activity_assignee(
        db, tenant_id=tenant_id, assigned_to_user_id=assigned_to_user_id
    )
    if not assignee:
        return
    stmt = select(Activity).where(
        Activity.tenant_id == tenant_id,
        Activity.type == INTERNAL_HR_HANDOFF_PENDING,
        Activity.related_entity_type == "candidate",
        Activity.related_entity_id == candidate_id,
    )
    for row in (await db.execute(stmt)).scalars().all():
        md = getattr(row, "metadata_", None) or {}
        if isinstance(md, dict) and str(md.get("handoff_id") or "") == str(handoff_id):
            return
    due = datetime.now(timezone.utc) + timedelta(days=3)
    db.add(
        Activity(
            id=str(uuid4()),
            tenant_id=tenant_id,
            type=INTERNAL_HR_HANDOFF_PENDING,
            source_module="hr",
            related_entity_type="candidate",
            related_entity_id=candidate_id,
            title="Review internal HR handoff request",
            assigned_to_user_id=assignee,
            created_by_user_id=created_by_user_id,
            due_at=due,
            status=ActivityStatus.planned,
            channel="internal",
            metadata_={
                "handoff_id": handoff_id,
                "destination": "internal_hr",
            },
        )
    )
    await db.flush()


async def _terminalize_internal_hr_pending_handoff_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    handoff_id: str,
    terminal_status: str,
    completed_at: datetime,
) -> None:
    if terminal_status not in (ActivityStatus.done, ActivityStatus.cancelled):
        return
    stmt = select(Activity).where(
        Activity.tenant_id == tenant_id,
        Activity.type == INTERNAL_HR_HANDOFF_PENDING,
        Activity.related_entity_type == "candidate",
        Activity.related_entity_id == candidate_id,
    )
    for row in (await db.execute(stmt)).scalars().all():
        md = getattr(row, "metadata_", None) or {}
        if not isinstance(md, dict) or str(md.get("handoff_id") or "") != str(handoff_id):
            continue
        if row.status in (ActivityStatus.done, ActivityStatus.cancelled):
            continue
        row.status = terminal_status
        if terminal_status == ActivityStatus.done:
            row.completed_at = completed_at
        else:
            row.cancelled_at = completed_at
    await db.flush()


async def _ensure_internal_hr_handoff_checklist_activities(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    handoff_id: str,
    assignee_user_id: str | None,
    created_by_user_id: str,
) -> None:
    """Idempotent HR checklist tasks after internal HR handoff (MVP)."""
    due = datetime.now(timezone.utc) + timedelta(days=7)
    assignee = (assignee_user_id or created_by_user_id or "").strip()
    if not assignee:
        assignee = await _first_active_hr_officer_user_id(db, tenant_id) or ""
    if not assignee:
        return
    keys: tuple[tuple[str, str], ...] = (
        ("verify_candidate_data", "Verify candidate data"),
        ("onboarding_checklist", "Complete onboarding checklist"),
        ("documents_hr_review", "Review employee documents"),
        ("zus_registration", "ZUS registration"),
        ("medical_examination", "Medical examination"),
        ("psychological_assessment", "Psychological assessment"),
    )
    rows = (
        (
            await db.execute(
                select(Activity).where(
                    Activity.tenant_id == tenant_id,
                    Activity.related_entity_type == "candidate",
                    Activity.related_entity_id == candidate_id,
                    Activity.type == HANDOFF_HR_CHECKLIST,
                )
            )
        )
        .scalars()
        .all()
    )
    existing_keys = set()
    for row in rows:
        md = getattr(row, "metadata_", None) or {}
        if isinstance(md, dict) and md.get("handoff_checklist_key"):
            existing_keys.add(str(md.get("handoff_checklist_key")))
    for key, title in keys:
        if key in existing_keys:
            continue
        db.add(
            Activity(
                id=str(uuid4()),
                tenant_id=tenant_id,
                type=HANDOFF_HR_CHECKLIST,
                source_module="hr",
                related_entity_type="candidate",
                related_entity_id=candidate_id,
                title=title,
                assigned_to_user_id=assignee,
                created_by_user_id=created_by_user_id,
                due_at=due,
                status=ActivityStatus.planned,
                channel="internal",
                metadata_={
                    "handoff_checklist_key": key,
                    "handoff_id": handoff_id,
                },
            )
        )
    await db.flush()


async def create_handoff(
    db: AsyncSession,
    *,
    candidate_id: str,
    agency_tenant_id: str,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
    requested_by_user_id: str,
    assigned_to_user_id: str | None = None,
    destination: str | None = None,
    application_id: str | None = None,
) -> tuple[CandidateHandoff | None, str | dict[str, Any] | None]:
    """Create handoff (client portal or internal HR). Returns (handoff, error)."""
    if not client_company_id and not client_tenant_id:
        return None, "Either client_company_id or client_tenant_id required"
    if client_company_id and client_tenant_id:
        return None, "Only one of client_company_id or client_tenant_id"

    dest = _normalize_handoff_destination(destination)

    cand = await db.get(Candidate, candidate_id)
    if not cand:
        return None, "Candidate not found"
    if str(cand.tenant_id) != agency_tenant_id:
        return None, "Candidate does not belong to agency tenant"

    from backend.app.services.company_module_enforcement import (
        assert_hr_for_candidate,
        assert_recruitment_for_candidate,
    )

    await assert_recruitment_for_candidate(db, agency_tenant_id, cand)
    if dest == "internal_hr":
        await assert_hr_for_candidate(db, agency_tenant_id, cand)

    cand_stage = (getattr(cand, "stage", None) or "").strip().lower()
    if dest == "internal_hr":
        if cand_stage not in ("ready_for_handoff", "ready_for_hr"):
            return None, "Only candidates at ready_for_handoff or ready_for_hr can be transferred to internal HR"
    elif cand_stage != "ready_for_handoff":
        return None, "Only candidates at stage 'Gotowy do przekazania' (ready_for_handoff) can be transferred"

    from backend.app.services.recruitment_package_readiness import assert_recruitment_package_ready_for_handoff

    pkg_err = await assert_recruitment_package_ready_for_handoff(
        db,
        tenant_id=agency_tenant_id,
        candidate_id=candidate_id,
    )
    if pkg_err:
        return None, pkg_err

    link = await get_tenant_link(
        db,
        agency_tenant_id=agency_tenant_id,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
    )
    if not link or not link.get_handoff_enabled():
        return None, "Handoff not enabled for this client"
    if dest == "internal_hr" and not link.get_handoff_to_internal_hr():
        return None, "Internal HR handoff is not enabled for this client link"

    existing = await get_pending_handoff(
        db, candidate_id, client_company_id=client_company_id, client_tenant_id=client_tenant_id
    )
    if existing:
        return None, "Pending handoff already exists for this candidate and client"

    now = datetime.now(timezone.utc)
    from_c = str(getattr(cand, "company_id", None) or "").strip() or None
    if not from_c:
        from_c = str(getattr(cand, "own_company_id", None) or "").strip() or None
    to_c = str(client_company_id or "").strip() or None
    ctid = str(client_tenant_id).strip() if client_tenant_id else None
    ht = _handoff_product_type(dest, ctid)
    handoff = CandidateHandoff(
        id=str(uuid4()),
        candidate_id=candidate_id,
        agency_tenant_id=agency_tenant_id,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
        requested_by_user_id=requested_by_user_id,
        requested_at=now,
        assigned_to_user_id=assigned_to_user_id,
        status="pending_review",
        destination=dest,
        handoff_type=ht,
        from_company_id=from_c,
        to_company_id=to_c,
        locked_at=now,
    )
    db.add(handoff)
    await db.flush()
    resolved_app = await _sync_application_after_handoff_created(
        db,
        tenant_id=agency_tenant_id,
        candidate=cand,
        application_id=application_id,
    )
    if resolved_app:
        handoff.application_id = resolved_app
        await db.flush()

    # internal_hr: PR-4 — do not materialize workforce / HR checklist until accept_handoff.
    # Candidate stays at recruitment stage (e.g. ready_for_handoff) until HR accepts.

    await log_audit_event(
        db,
        tenant_id=agency_tenant_id,
        event_type=AuditEventType.handoff_requested,
        entity_type=AuditEntityType.handoff,
        entity_id=handoff.id,
        actor_id=requested_by_user_id,
        payload={
            "candidate_id": candidate_id,
            "client_company_id": client_company_id,
            "destination": dest,
        },
    )
    # Notify HR (internal lane) or client processors (portal).
    if dest == "internal_hr":
        notify_ids: list[str] = []
        if handoff.assigned_to_user_id:
            notify_ids.append(str(handoff.assigned_to_user_id))
        else:
            hr_rows = await db.execute(
                select(User.id).where(
                    User.tenant_id == agency_tenant_id,
                    User.role == UserRole.hr_officer,
                    User.is_active.is_(True),
                )
            )
            notify_ids = [str(r[0]) for r in hr_rows.all() if r[0]]
        if notify_ids:
            await emit_event(
                db,
                tenant_id=agency_tenant_id,
                event_type="handoff_requested",
                payload={
                    "candidate_id": candidate_id,
                    "handoff_id": handoff.id,
                    "destination": "internal_hr",
                },
                audience=EventAudience(user_ids=notify_ids),
                entity_type="handoff",
                entity_id=handoff.id,
                send_webhook=True,
            )
        await _ensure_internal_hr_pending_handoff_activity(
            db,
            tenant_id=agency_tenant_id,
            candidate_id=candidate_id,
            handoff_id=handoff.id,
            assigned_to_user_id=handoff.assigned_to_user_id,
            created_by_user_id=requested_by_user_id,
        )
        await persist_handoff_create_snapshot(db, handoff=handoff, candidate=cand)
        return handoff, None

    if handoff.assigned_to_user_id:
        await emit_event(
            db,
            tenant_id=agency_tenant_id,
            event_type="handoff_requested",
            payload={"candidate_id": candidate_id, "handoff_id": handoff.id},
            audience=EventAudience(user_ids=[handoff.assigned_to_user_id]),
            entity_type="handoff",
            entity_id=handoff.id,
            send_webhook=True,
        )
    elif client_company_id:
        rows = await db.execute(
            select(UserCompanyAccess.user_id).where(
                UserCompanyAccess.tenant_id == agency_tenant_id,
                UserCompanyAccess.company_id == client_company_id,
            )
        )
        processor_ids = list({str(r[0]) for r in rows if r[0]})
        if processor_ids:
            await emit_event(
                db,
                tenant_id=agency_tenant_id,
                event_type="handoff_requested",
                payload={"candidate_id": candidate_id, "handoff_id": handoff.id},
                audience=EventAudience(user_ids=processor_ids),
                entity_type="handoff",
                entity_id=handoff.id,
                send_webhook=True,
            )
    elif client_tenant_id:
        import sqlalchemy as sa

        um = sa.table("user_memberships", sa.column("user_id"), sa.column("tenant_id"))
        rows = await db.execute(
            sa.select(um.c.user_id).where(um.c.tenant_id == client_tenant_id)
        )
        processor_ids = list({str(r[0]) for r in rows if r[0]})
        if processor_ids:
            await emit_event(
                db,
                tenant_id=client_tenant_id,
                event_type="handoff_requested",
                payload={
                    "candidate_id": candidate_id,
                    "handoff_id": handoff.id,
                    "client_tenant_id": client_tenant_id,
                },
                audience=EventAudience(user_ids=processor_ids),
                entity_type="handoff",
                entity_id=handoff.id,
                send_webhook=True,
            )
    await persist_handoff_create_snapshot(db, handoff=handoff, candidate=cand)
    return handoff, None


async def accept_handoff(
    db: AsyncSession,
    *,
    handoff_id: str,
    reviewed_by_user_id: str | None,
    tenant_id: str,
) -> tuple[CandidateHandoff | None, str | None]:
    """Accept handoff. Sets processor if assigned_to was empty and reviewer is known."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff:
        return None, "Handoff not found"
    if handoff.status != "pending_review":
        return None, f"Handoff is {handoff.status}, cannot accept"

    now = datetime.now(timezone.utc)
    handoff.status = "accepted"
    handoff.reviewed_by_user_id = reviewed_by_user_id
    handoff.reviewed_at = now
    handoff.accepted_at = now
    handoff.accepted_by_user_id = reviewed_by_user_id
    handoff.completed_at = now
    if getattr(handoff, "locked_at", None) is None:
        handoff.locked_at = now
    if not handoff.assigned_to_user_id and reviewed_by_user_id:
        handoff.assigned_to_user_id = reviewed_by_user_id
    await db.flush()

    cand = await db.get(Candidate, handoff.candidate_id)
    dest = (getattr(handoff, "destination", None) or "client_portal").strip().lower()
    if dest == "internal_hr":
        await _terminalize_internal_hr_pending_handoff_activity(
            db,
            tenant_id=str(handoff.agency_tenant_id),
            candidate_id=str(handoff.candidate_id),
            handoff_id=handoff.id,
            terminal_status=ActivityStatus.done,
            completed_at=now,
        )
    if cand:
        if dest == "internal_hr":
            from backend.app.services.company_module_enforcement import assert_hr_for_candidate

            await assert_hr_for_candidate(db, str(handoff.agency_tenant_id), cand)
            cand.stage = "processing_by_hr"
            if hasattr(cand, "status"):
                cand.status = "processing_by_hr"
            await db.flush()
            from backend.app.services.hr_acceptance_orchestrator import accept_internal_hr_handoff

            await accept_internal_hr_handoff(
                db,
                handoff=handoff,
                candidate=cand,
                reviewed_by_user_id=reviewed_by_user_id,
                tenant_id=tenant_id,
            )
        else:
            cand.stage = "processing_by_client"
            if hasattr(cand, "status"):
                cand.status = "processing_by_client"
            await db.flush()

    cand_sync = await db.get(Candidate, handoff.candidate_id)
    vac_raw = getattr(cand_sync, "vacancy_id", None) if cand_sync else None
    vac_id = str(vac_raw).strip() if vac_raw else None
    app_id = str(handoff.application_id).strip() if getattr(handoff, "application_id", None) else None
    await _sync_application_after_handoff_accepted(
        db,
        tenant_id=str(handoff.agency_tenant_id),
        candidate_id=str(handoff.candidate_id),
        vacancy_id=vac_id,
        application_id=app_id,
    )

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.handoff_accepted,
        entity_type=AuditEntityType.handoff,
        entity_id=handoff.id,
        actor_id=reviewed_by_user_id,
        payload={"candidate_id": handoff.candidate_id},
    )
    # Notify agency manager
    cand = await db.get(Candidate, handoff.candidate_id)
    notify_ids = [handoff.requested_by_user_id]
    if cand and cand.manager and str(cand.manager) not in [str(x) for x in notify_ids]:
        notify_ids.append(str(cand.manager))
    if notify_ids:
        await emit_event(
            db,
            tenant_id=handoff.agency_tenant_id,
            event_type="handoff_accepted",
            payload={
                "candidate_id": handoff.candidate_id,
                "handoff_id": handoff.id,
                "via_public_portal": reviewed_by_user_id is None,
            },
            audience=EventAudience(user_ids=notify_ids),
            entity_type="handoff",
            entity_id=handoff.id,
            send_webhook=True,
        )
    return handoff, None


async def reject_handoff(
    db: AsyncSession,
    *,
    handoff_id: str,
    reviewed_by_user_id: str | None,
    rejection_reason: str,
    tenant_id: str,
) -> tuple[CandidateHandoff | None, str | None]:
    """Reject handoff."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff:
        return None, "Handoff not found"
    if handoff.status != "pending_review":
        return None, f"Handoff is {handoff.status}, cannot reject"

    reason = (rejection_reason or "").strip()
    if not reason:
        return None, "rejection_reason is required"

    now = datetime.now(timezone.utc)
    handoff.status = "rejected"
    handoff.reviewed_by_user_id = reviewed_by_user_id
    handoff.reviewed_at = now
    handoff.rejection_reason = reason
    handoff.locked_at = None
    await db.flush()

    dest = (getattr(handoff, "destination", None) or "client_portal").strip().lower()
    if dest == "internal_hr":
        await _terminalize_internal_hr_pending_handoff_activity(
            db,
            tenant_id=str(handoff.agency_tenant_id),
            candidate_id=str(handoff.candidate_id),
            handoff_id=handoff.id,
            terminal_status=ActivityStatus.cancelled,
            completed_at=now,
        )

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.handoff_rejected,
        entity_type=AuditEntityType.handoff,
        entity_id=handoff.id,
        actor_id=reviewed_by_user_id,
        payload={"candidate_id": handoff.candidate_id, "reason": reason},
    )
    # Notify agency manager
    cand = await db.get(Candidate, handoff.candidate_id)
    notify_ids = [handoff.requested_by_user_id]
    if cand and cand.manager and str(cand.manager) not in [str(x) for x in notify_ids]:
        notify_ids.append(str(cand.manager))
    if notify_ids:
        await emit_event(
            db,
            tenant_id=handoff.agency_tenant_id,
            event_type="handoff_rejected",
            payload={
                "candidate_id": handoff.candidate_id,
                "handoff_id": handoff.id,
                "reason": reason,
                "via_public_portal": reviewed_by_user_id is None,
            },
            audience=EventAudience(user_ids=notify_ids),
            entity_type="handoff",
            entity_id=handoff.id,
            send_webhook=True,
        )
    return handoff, None


async def return_handoff(
    db: AsyncSession,
    *,
    handoff_id: str,
    reviewed_by_user_id: str | None,
    return_reason: str,
    tenant_id: str,
) -> tuple[CandidateHandoff | None, str | None]:
    """Return handoff to agency. Works for pending_review (client returns without accepting) and accepted."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff:
        return None, "Handoff not found"
    if handoff.status not in ("pending_review", "accepted"):
        return None, f"Handoff is {handoff.status}, can only return pending or accepted handoffs"

    reason = (return_reason or "").strip()
    if not reason:
        return None, "return_reason is required"

    now = datetime.now(timezone.utc)
    handoff.status = "returned"
    handoff.return_reason = reason
    handoff.returned_reason = reason
    handoff.returned_by_user_id = reviewed_by_user_id
    handoff.reviewed_by_user_id = reviewed_by_user_id
    handoff.reviewed_at = now
    handoff.locked_at = None
    await db.flush()

    dest = (getattr(handoff, "destination", None) or "client_portal").strip().lower()
    if dest == "internal_hr":
        await _terminalize_internal_hr_pending_handoff_activity(
            db,
            tenant_id=str(handoff.agency_tenant_id),
            candidate_id=str(handoff.candidate_id),
            handoff_id=handoff.id,
            terminal_status=ActivityStatus.cancelled,
            completed_at=now,
        )

    # Set candidate stage to "Zwrócono" for easy filtering
    cand = await db.get(Candidate, handoff.candidate_id)
    if cand:
        cand.stage = "handoff_returned"
        if hasattr(cand, "status"):
            cand.status = "handoff_returned"
        await db.flush()

    cand_sync = await db.get(Candidate, handoff.candidate_id)
    vac_raw = getattr(cand_sync, "vacancy_id", None) if cand_sync else None
    vac_id = str(vac_raw).strip() if vac_raw else None
    app_id = str(handoff.application_id).strip() if getattr(handoff, "application_id", None) else None
    await _sync_application_after_handoff_returned(
        db,
        tenant_id=str(handoff.agency_tenant_id),
        candidate_id=str(handoff.candidate_id),
        vacancy_id=vac_id,
        application_id=app_id,
    )

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.handoff_returned,
        entity_type=AuditEntityType.handoff,
        entity_id=handoff.id,
        actor_id=reviewed_by_user_id,
        payload={"candidate_id": handoff.candidate_id, "reason": reason},
    )
    # Notify agency manager
    cand = await db.get(Candidate, handoff.candidate_id)
    notify_ids = [handoff.requested_by_user_id]
    if cand and cand.manager and str(cand.manager) not in [str(x) for x in notify_ids]:
        notify_ids.append(str(cand.manager))
    if notify_ids:
        await emit_event(
            db,
            tenant_id=handoff.agency_tenant_id,
            event_type="handoff_returned",
            payload={
                "candidate_id": handoff.candidate_id,
                "handoff_id": handoff.id,
                "reason": reason,
                "via_public_portal": reviewed_by_user_id is None,
            },
            audience=EventAudience(user_ids=notify_ids),
            entity_type="handoff",
            entity_id=handoff.id,
            send_webhook=True,
        )
    return handoff, None


async def list_available_clients(
    db: AsyncSession,
    agency_tenant_id: str,
) -> list[dict]:
    """List clients (companies and employer tenants) with handoff_enabled for agency."""
    from backend.app.models.tenant import Tenant

    links = await list_links_for_agency(db, agency_tenant_id)
    result = []
    for link in links:
        if not link.get_handoff_enabled():
            continue
        if link.client_company_id:
            company = await db.get(Company, link.client_company_id)
            if company and not getattr(company, "is_archived", False):
                result.append({
                    "link_id": link.id,
                    "client_company_id": link.client_company_id,
                    "client_tenant_id": None,
                    "client_name": company.name if company else "—",
                })
        elif link.client_tenant_id:
            tenant = await db.get(Tenant, link.client_tenant_id)
            result.append({
                "link_id": link.id,
                "client_company_id": None,
                "client_tenant_id": link.client_tenant_id,
                "client_name": tenant.name if tenant else "—",
            })
    return result


async def change_processor(
    db: AsyncSession,
    *,
    handoff_id: str,
    new_processor_user_id: str,
    actor_id: str,
    tenant_id: str,
) -> tuple[CandidateHandoff | None, str | None]:
    """Change processor for accepted handoff. Logs processor_changed audit."""
    handoff = await db.get(CandidateHandoff, handoff_id)
    if not handoff:
        return None, "Handoff not found"
    if handoff.status != "accepted":
        return None, "Can only change processor for accepted handoffs"

    old_id = handoff.assigned_to_user_id
    handoff.assigned_to_user_id = new_processor_user_id
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.processor_changed,
        entity_type=AuditEntityType.handoff,
        entity_id=handoff.id,
        actor_id=actor_id,
        payload={
            "candidate_id": handoff.candidate_id,
            "old_processor_id": old_id,
            "new_processor_id": new_processor_user_id,
        },
    )
    return handoff, None


async def list_pending_for_client(
    db: AsyncSession,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
    *,
    destination: str | None = None,
) -> list[CandidateHandoff]:
    """List pending handoffs for client (Do procesowania). Excludes handoffs whose candidate was deleted."""
    stmt = (
        select(CandidateHandoff)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .where(CandidateHandoff.status == "pending_review")
        .where(Candidate.deleted_at.is_(None))
    )
    if client_company_id:
        stmt = stmt.where(CandidateHandoff.client_company_id == client_company_id)
    elif client_tenant_id:
        row = await db.execute(
            select(TenantLink.handoff_include_company_id).where(
                TenantLink.client_tenant_id == client_tenant_id,
                TenantLink.handoff_include_company_id.isnot(None),
            ).limit(1)
        )
        inc = row.scalar_one_or_none()
        include_company_id = str(inc) if inc else None
        if include_company_id:
            stmt = stmt.where(
                or_(
                    CandidateHandoff.client_tenant_id == client_tenant_id,
                    CandidateHandoff.client_company_id == include_company_id,
                )
            )
        else:
            stmt = stmt.where(CandidateHandoff.client_tenant_id == client_tenant_id)
    else:
        return []
    if destination:
        stmt = stmt.where(
            CandidateHandoff.destination == _normalize_handoff_destination(destination)
        )
    else:
        stmt = stmt.where(CandidateHandoff.destination != "internal_hr")
    stmt = stmt.order_by(CandidateHandoff.requested_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_pending_with_candidates(
    db: AsyncSession,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
    *,
    destination: str | None = None,
) -> list[dict]:
    """List pending handoffs with candidate summary for Do procesowania UI."""
    handoffs = await list_pending_for_client(
        db,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
        destination=destination,
    )
    if not handoffs:
        return []
    candidate_ids = list({h.candidate_id for h in handoffs})
    cand_rows = await db.execute(
        select(Candidate).where(Candidate.id.in_(candidate_ids))
    )
    by_id = {c.id: c for c in cand_rows.scalars().all()}
    result: list[dict] = []
    for h in handoffs:
        cand = by_id.get(h.candidate_id)
        if cand is not None and getattr(cand, "deleted_at", None) is not None:
            continue
        fn = cand.first_name if cand else ""
        ln = cand.last_name if cand else ""
        fn_latin = getattr(cand, "first_name_latin", None) if cand else None
        ln_latin = getattr(cand, "last_name_latin", None) if cand else None
        result.append({
            "handoff": h,
            "candidate": {
                "id": h.candidate_id,
                "first_name": fn,
                "last_name": ln,
                "first_name_latin": fn_latin,
                "last_name_latin": ln_latin,
                "email": cand.email if cand else "",
            } if cand else {
                "id": h.candidate_id,
                "first_name": "", "last_name": "",
                "first_name_latin": None, "last_name_latin": None,
                "email": "",
            },
        })
    return result


async def list_handoffs_with_candidates(
    db: AsyncSession,
    *,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
    statuses: Sequence[str] | None = None,
    from_dt: datetime | None = None,
    requested_from_dt: datetime | None = None,
    requested_to_dt: datetime | None = None,
    candidate_stage_codes: Sequence[str] | None = None,
    q: str | None = None,
    order_by: str = "requested_at",
    desc: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    List handoffs with candidate summary for Do procesowania history.

    Supports multiple statuses (pending_review / accepted / rejected / returned)
    and optional time filter (applied to reviewed_at/requested_at).

    When client_tenant_id is passed, also includes handoffs to handoff_include_company_id
    from tenant_links (for clients whose handoffs were created to a company instead of tenant).
    """
    if not client_company_id and not client_tenant_id:
        return [], 0

    include_company_id: str | None = None
    if client_tenant_id:
        row = await db.execute(
            select(TenantLink.handoff_include_company_id).where(
                TenantLink.client_tenant_id == client_tenant_id,
                TenantLink.handoff_include_company_id.isnot(None),
            ).limit(1)
        )
        inc = row.scalar_one_or_none()
        include_company_id = str(inc) if inc else None

    # When only client_company_id is provided, also look up linked client_tenant_id
    # via TenantLink.handoff_include_company_id so that history includes both
    # tenant- and company-directed handoffs for клиентов вроде Citronex.
    linked_tenant_id: str | None = None
    if client_company_id and not client_tenant_id:
        row = await db.execute(
            select(TenantLink.client_tenant_id).where(
                TenantLink.handoff_include_company_id == client_company_id,
                TenantLink.status == "active",
            ).limit(1)
        )
        linked = row.scalar_one_or_none()
        linked_tenant_id = str(linked) if linked else None

    reviewer_alias = aliased(User)

    # Inner join to exclude handoffs whose candidate was deleted by agency
    base = (
        select(CandidateHandoff, Candidate, reviewer_alias)
        .select_from(CandidateHandoff)
        .join(Candidate, Candidate.id == CandidateHandoff.candidate_id)
        .outerjoin(reviewer_alias, reviewer_alias.id == CandidateHandoff.reviewed_by_user_id)
        .where(Candidate.deleted_at.is_(None))
    )

    conditions = []
    if client_company_id:
        if linked_tenant_id:
            conditions.append(
                or_(
                    CandidateHandoff.client_company_id == client_company_id,
                    CandidateHandoff.client_tenant_id == linked_tenant_id,
                )
            )
        else:
            conditions.append(CandidateHandoff.client_company_id == client_company_id)
    elif client_tenant_id:
        if include_company_id:
            conditions.append(
                or_(
                    CandidateHandoff.client_tenant_id == client_tenant_id,
                    CandidateHandoff.client_company_id == include_company_id,
                )
            )
        else:
            conditions.append(CandidateHandoff.client_tenant_id == client_tenant_id)

    if statuses:
        conditions.append(CandidateHandoff.status.in_(list(statuses)))

    if from_dt is not None:
        # For pending we only have requested_at, for decided we have reviewed_at.
        conditions.append(
            func.coalesce(CandidateHandoff.reviewed_at, CandidateHandoff.requested_at)
            >= from_dt
        )
    if requested_from_dt is not None:
        conditions.append(CandidateHandoff.requested_at >= requested_from_dt)
    if requested_to_dt is not None:
        conditions.append(CandidateHandoff.requested_at < requested_to_dt)
    if candidate_stage_codes:
        stages = [s for s in candidate_stage_codes if s]
        if stages:
            conditions.append(Candidate.stage.in_(stages))

    # Search q: first_name, last_name, email, phone, short_id (min 2 chars)
    q_trimmed = (q or "").strip()
    if len(q_trimmed) >= 2:
        like = f"%{q_trimmed.lower()}%"
        full_name = func.lower(
            func.concat(
                func.coalesce(Candidate.first_name, ""),
                " ",
                func.coalesce(Candidate.last_name, ""),
            )
        )
        full_name_rev = func.lower(
            func.concat(
                func.coalesce(Candidate.last_name, ""),
                " ",
                func.coalesce(Candidate.first_name, ""),
            )
        )
        conditions.append(
            or_(
                func.lower(func.coalesce(Candidate.first_name, "")).like(like),
                func.lower(func.coalesce(Candidate.last_name, "")).like(like),
                full_name.like(like),
                full_name_rev.like(like),
                func.lower(func.coalesce(Candidate.email, "")).like(like),
                func.lower(func.coalesce(Candidate.phone, "")).like(like),
                func.lower(func.coalesce(Candidate.short_id, "")).like(like),
            )
        )

    if conditions:
        base = base.where(and_(*conditions))

    total_stmt = select(func.count()).select_from(base.subquery())
    total_result = await db.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)

    # order_by: requested_at | reviewed_at | candidate_name | status | stage | created_at
    order_col = CandidateHandoff.requested_at
    if order_by == "reviewed_at":
        order_col = func.coalesce(CandidateHandoff.reviewed_at, CandidateHandoff.requested_at)
    elif order_by == "candidate_name":
        order_col = func.concat(
            func.coalesce(Candidate.first_name, ""),
            " ",
            func.coalesce(Candidate.last_name, ""),
        )
    elif order_by == "status":
        order_col = CandidateHandoff.status
    elif order_by == "stage":
        order_col = func.coalesce(Candidate.stage, "")
    elif order_by == "created_at":
        order_col = Candidate.created_at
    else:
        order_col = CandidateHandoff.requested_at
    stmt = (
        base.order_by(order_col.desc() if desc else order_col.asc())
        .offset(offset)
        .limit(limit)
    )
    rows = await db.execute(stmt)

    items: list[dict] = []
    for handoff, cand, reviewer in rows.all():
        # Преобразуем reviewed_by_user_id в человеко-читаемый лейбл (ФИО / short_id / email),
        # чтобы колонка "Кто" в Do procesowania показывала имя, а не UUID.
        if reviewer is not None:
            reviewed_label = (
                getattr(reviewer, "full_name", None)
                or getattr(reviewer, "short_id", None)
                or getattr(reviewer, "email", None)
                or handoff.reviewed_by_user_id
            )
            handoff.reviewed_by_user_id = reviewed_label  # type: ignore[assignment]
        if cand is not None:
            fn = cand.first_name or ""
            ln = cand.last_name or ""
            fn_latin = getattr(cand, "first_name_latin", None)
            ln_latin = getattr(cand, "last_name_latin", None)
            extra = cand._get_extra() if hasattr(cand, "_get_extra") else {}
            personal = cand._get_personal_data() if hasattr(cand, "_get_personal_data") else {}
            if not personal and isinstance(extra, dict):
                personal = extra.get("personal_data") or extra.get("personal") or {}
            citizenship = (
                personal.get("citizenship")
                or extra.get("citizenship")
                or extra.get("country_code")
                or ""
            )
            vac = getattr(cand, "vacancy", None)
            vacancy_title = vac.title if vac and hasattr(vac, "title") else ""
            # Get docs_progress for documents column
            docs_progress_raw = getattr(cand, "docs_progress", None)
            docs_progress = {}
            if isinstance(docs_progress_raw, dict):
                docs_progress = docs_progress_raw
            elif isinstance(docs_progress_raw, str):
                try:
                    import json
                    docs_progress = json.loads(docs_progress_raw) or {}
                except Exception:
                    docs_progress = {}
            # Get experience from extra.profile.experience
            experience_list = []
            if isinstance(extra, dict):
                profile = extra.get("profile") or {}
                exp_raw = profile.get("experience") or []
                if isinstance(exp_raw, list):
                    experience_list = exp_raw
            candidate_payload = {
                "id": handoff.candidate_id,
                "first_name": fn,
                "last_name": ln,
                "first_name_latin": fn_latin,
                "last_name_latin": ln_latin,
                "email": cand.email or "",
                "phone": cand.phone or "",
                "short_id": getattr(cand, "short_id", None) or "",
                "stage": getattr(cand, "stage", None) or "",
                "citizenship": (citizenship or "").upper() or None,
                "created_at": cand.created_at.isoformat() if cand.created_at else None,
                "vacancy_title": vacancy_title,
                "manager_id": getattr(cand, "manager", None) or None,
                "extra": extra or {},
                "docs_progress": docs_progress or {},
                "experience": experience_list,
            }
        else:
            candidate_payload = {
                "id": handoff.candidate_id,
                "first_name": "",
                "last_name": "",
                "first_name_latin": None,
                "last_name_latin": None,
                "email": "",
                "phone": "",
                "short_id": "",
                "stage": "",
                "citizenship": None,
                "created_at": None,
                "vacancy_title": "",
                "manager_id": None,
                "extra": {},
                "docs_progress": {},
                "experience": [],
            }
        items.append(
            {
                "handoff": handoff,
                "candidate": candidate_payload,
            }
        )

    return items, total
