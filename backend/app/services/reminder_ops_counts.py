"""Operational reminder counts: exclude pipeline-completed candidates from actionable metrics."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.candidate_operational_sql import sql_candidate_active_operational_pipeline
from backend.app.models import Candidate, Reminder
from backend.app.models.reminder import ReminderStatus

_ACTIVE_CANDIDATE_FOR_OPS = sql_candidate_active_operational_pipeline(Candidate.stage, Candidate.status)


async def count_overdue_reminders_ops_scoped(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str | None = None,
) -> int:
    """
    Overdue reminders for dashboard/goals. Candidate reminders count only if the candidate
    is still in an active pipeline stage (not rejected / declined / employed / probation_ok).
    Lead and other entity reminders are unchanged.
    """
    stmt = (
        select(func.count())
        .select_from(Reminder)
        .outerjoin(
            Candidate,
            and_(
                Reminder.entity_type == "candidate",
                Reminder.entity_id == Candidate.id,
                Candidate.tenant_id == tenant_id,
            ),
        )
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.status == ReminderStatus.overdue,
            or_(
                Reminder.entity_type != "candidate",
                and_(
                    Candidate.id.isnot(None),
                    Candidate.deleted_at.is_(None),
                    _ACTIVE_CANDIDATE_FOR_OPS,
                ),
            ),
        )
    )
    if assignee_id:
        stmt = stmt.where(Reminder.assignee_id == assignee_id)
    return int((await db.execute(stmt)).scalar_one() or 0)
