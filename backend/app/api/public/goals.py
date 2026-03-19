from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.app.db.deps import get_db_with_tenant
from backend.app.models import Candidate, Reminder, Tenant
from backend.app.models.reminder import ReminderStatus


router = APIRouter(tags=["public-goals"])


DEFAULT_GOALS_V1 = [
    {"key": "next_action_coverage_percent", "op": ">=", "target": 90},
    {"key": "overdue_reminders", "op": "<=", "target": 0},
]


class PublicGoalsOut(BaseModel):
    generated_at: datetime
    period: dict[str, Any]
    goals: list[dict[str, Any]]
    metrics: dict[str, Any]


def _safe_settings(tenant: Tenant) -> dict[str, Any]:
    raw = tenant.settings or {}
    return raw if isinstance(raw, dict) else {}


def _get_goals_config(settings: dict[str, Any]) -> list[dict[str, Any]]:
    raw = settings.get("goals_v1")
    if isinstance(raw, list) and raw:
        return [g for g in raw if isinstance(g, dict) and str(g.get("key") or "").strip()]
    return DEFAULT_GOALS_V1


def _ensure_share_token(settings: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    token = str(settings.get("goals_share_token") or "").strip()
    rotated = False
    if not token:
        token = secrets.token_urlsafe(24)
        settings["goals_share_token"] = token
        rotated = True
    return settings, token, rotated


async def _compute_metrics(db: AsyncSession, tenant_id: str, assignee_id: Optional[str] = None) -> dict[str, Any]:
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    assignee = (assignee_id or "").strip() or None

    total_candidates = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.deleted_at.is_(None), Candidate.tenant_id == tenant_id)
        )
    ).scalar_one() or 0

    reminder_exists = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == Candidate.id,
            (Reminder.assignee_id == assignee) if assignee else True,
            Reminder.status.in_(active_statuses),
        )
        .correlate(Candidate)
    )
    no_next_action = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.deleted_at.is_(None),
                Candidate.tenant_id == tenant_id,
                ~reminder_exists,
            )
        )
    ).scalar_one() or 0

    overdue = (
        await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                (Reminder.assignee_id == assignee) if assignee else True,
                Reminder.status == ReminderStatus.overdue,
            )
        )
    ).scalar_one() or 0

    coverage = 0.0
    if int(total_candidates) > 0:
        coverage = max(0.0, min(100.0, (1.0 - (float(no_next_action) / float(total_candidates))) * 100.0))

    return {
        "total_candidates": int(total_candidates),
        "no_next_action_candidates": int(no_next_action),
        "next_action_coverage_percent": round(coverage, 2),
        "overdue_reminders": int(overdue),
    }


@router.get("/public/goals/{share_token}", response_model=PublicGoalsOut)
async def public_goals(
    share_token: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    assignee_id: Optional[str] = Query(default=None),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    if tenant.status_sharing_allowed is not True:
        raise HTTPException(status_code=403, detail="sharing_disabled")

    settings = _safe_settings(tenant)
    expected = str(settings.get("goals_share_token") or "").strip()
    if not expected or secrets.compare_digest(expected, str(share_token or "").strip()) is False:
        raise HTTPException(status_code=404, detail="not_found")

    now = datetime.now(timezone.utc)
    metrics = await _compute_metrics(db, tenant_id=tenant_id, assignee_id=assignee_id)
    goals = _get_goals_config(settings)
    return PublicGoalsOut(
        generated_at=now,
        period={"from": (now - timedelta(days=14)).isoformat(), "to": now.isoformat()},
        goals=goals,
        metrics=metrics,
    )

