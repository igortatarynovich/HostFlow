"""Recruitment-only auto-assign gate: working hours + optional communications queue team state.

Used when creating candidates / converting leads so we only auto-assign **available**
recruiters in company scope — no HR/Fleet/calendar planner integration here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.access import UserCompanyAccess
from backend.app.models.tenant import Tenant
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.app.services.recruiter_availability_state import (
    RecruiterAvailabilityState,
    get_recruiter_availability_state,
)
from backend.app.services.working_hours_window import is_within_working_hours

logger = logging.getLogger(__name__)

# Structured audit / activity (recruitment auto-assign unassigned)
RECRUITMENT_AUTO_ASSIGN_OBSERVABILITY_SOURCE = "recruitment_auto_assign"
RECRUITMENT_AUTO_ASSIGN_UNASSIGNED_REASON = "no_available_recruiter"


def is_recruiter_available_for_new_lead_auto_assign(
    user: User,
    _tenant: Tenant | None,
    *,
    now_utc: datetime | None = None,
    canonical_state: RecruiterAvailabilityState = RecruiterAvailabilityState.available,
) -> tuple[bool, str]:
    """Return (eligible, reason_code) for **automatic** new-lead/candidate assignment.

    Gates (in order):

    1. Canonical per-tenant state in ``recruiter_availability_states`` (passed in as
       ``canonical_state``; missing DB row → ``available``). Not stored in
       ``User.extra``.
    2. ``User.extra.working_hours_v1`` via :func:`is_within_working_hours` (schedule
       window only).

    Intentionally **does not** read ``communications.managerQueue`` (comms/planner).

    ``_tenant`` is unused today; kept for call-site stability.
    """
    if canonical_state != RecruiterAvailabilityState.available:
        return (False, f"availability_{canonical_state.value}")

    ref = now_utc if now_utc is not None else datetime.now(timezone.utc)
    if not is_within_working_hours(user.extra, ref):
        return (False, "outside_working_hours")

    return (True, "")


async def user_id_eligible_as_available_recruiter_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    user_id: str,
    tenant_obj: Tenant | None = None,
    now_utc: datetime | None = None,
) -> tuple[bool, str]:
    """Active tenant recruiter with optional company access + availability (for lead fallback)."""
    uid = str(user_id or "").strip()
    if not uid:
        return (False, "missing_user_id")
    row = await db.execute(
        select(User).where(
            User.id == uid,
            User.is_active.is_(True),
            User.role == UserRole.employee,
            or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
        )
    )
    user = row.scalar_one_or_none()
    if user is None:
        return (False, "not_active_recruiter")

    if company_id:
        acc = await db.execute(
            select(UserCompanyAccess.id).where(
                UserCompanyAccess.tenant_id == tenant_id,
                UserCompanyAccess.company_id == company_id,
                UserCompanyAccess.user_id == uid,
            )
        )
        if acc.scalar_one_or_none() is None:
            return (False, "no_company_scope")

    t = tenant_obj if tenant_obj is not None else await db.get(Tenant, str(tenant_id))
    canon = await get_recruiter_availability_state(db, tenant_id=tenant_id, user_id=uid)
    ok, reason = is_recruiter_available_for_new_lead_auto_assign(
        user, t, now_utc=now_utc, canonical_state=canon
    )
    if not ok:
        return (False, reason or "not_available")
    return (True, "")


async def observe_recruitment_auto_assign_unassigned(
    db: Any,
    *,
    tenant_id: str,
    vacancy_id: str | None,
    company_id: str | None,
    context: dict[str, Any],
    candidate_id: str | None = None,
) -> None:
    """Best-effort activity + structured audit when no eligible recruiter was found."""
    try:
        from backend.app.core.audit_events import AuditEntityType, AuditEventType
        from backend.app.services.audit import log_activity, log_audit_event

        payload: dict[str, Any] = {**dict(context or {})}
        payload["tenant_id"] = str(tenant_id)
        payload["reason"] = RECRUITMENT_AUTO_ASSIGN_UNASSIGNED_REASON
        payload["source"] = RECRUITMENT_AUTO_ASSIGN_OBSERVABILITY_SOURCE
        if vacancy_id is not None:
            payload["vacancy_id"] = vacancy_id
        if company_id is not None:
            payload["company_id"] = company_id
        if candidate_id:
            payload["candidate_id"] = str(candidate_id)
        ent_type = AuditEntityType.candidate if candidate_id else AuditEntityType.tenant
        ent_id = str(candidate_id) if candidate_id else tenant_id
        await log_activity(
            db,
            tenant_id=tenant_id,
            action="recruitment_auto_assign_unassigned",
            actor_id=None,
            target_type=str(ent_type.value),
            target_id=ent_id,
            payload=payload,
        )
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.recruitment_auto_assign_unassigned,
            entity_type=ent_type,
            entity_id=ent_id,
            actor_id=None,
            payload=payload,
        )
        await db.flush()
    except Exception:
        logger.exception(
            "recruitment_auto_assign_unassigned observability failed tenant=%s",
            tenant_id,
        )
