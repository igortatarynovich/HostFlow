from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.db.candidate_operational_sql import sql_candidate_active_operational_pipeline
from backend.app.models import Candidate, Reminder, Tenant
from backend.app.services.reminder_ops_counts import count_overdue_reminders_ops_scoped
from backend.app.models.reminder import ReminderStatus


router = APIRouter(tags=["goals"])


DEFAULT_GOALS_V1: list[dict[str, Any]] = [
    {"key": "next_action_coverage_percent", "op": ">=", "target": 90, "label": "Next action coverage %"},
    {"key": "overdue_reminders", "op": "<=", "target": 0, "label": "Overdue reminders"},
]


class GoalRule(BaseModel):
    key: Literal[
        "next_action_coverage_percent",
        "overdue_reminders",
        "no_next_action_candidates",
        "total_candidates",
    ]
    op: Literal[">=", "<=", "=="] = ">="
    target: float
    label: Optional[str] = None


class GoalsConfigIn(BaseModel):
    goals: list[GoalRule] = Field(default_factory=list)


class GoalsOut(BaseModel):
    generated_at: datetime
    goals: list[dict[str, Any]]
    metrics: dict[str, Any]
    share_url: Optional[str] = None


def _safe_settings(tenant: Tenant) -> dict[str, Any]:
    raw = tenant.settings or {}
    return raw if isinstance(raw, dict) else {}


def _get_goals_config(settings: dict[str, Any]) -> list[dict[str, Any]]:
    raw = settings.get("goals_v1")
    if isinstance(raw, list) and raw:
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            out.append(item)
        if out:
            return out
    return DEFAULT_GOALS_V1


def _ensure_share_token(settings: dict[str, Any]) -> tuple[dict[str, Any], str, bool]:
    token = str(settings.get("goals_share_token") or "").strip()
    rotated = False
    if not token:
        token = secrets.token_urlsafe(24)
        settings["goals_share_token"] = token
        rotated = True
    return settings, token, rotated


async def _compute_metrics(db: AsyncSession, tenant_id: str, assignee_id: str) -> dict[str, Any]:
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    active_stage = sql_candidate_active_operational_pipeline(Candidate.stage, Candidate.status)

    total_candidates = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(Candidate.deleted_at.is_(None), Candidate.tenant_id == tenant_id)
        )
    ).scalar_one() or 0

    active_pipeline_candidates = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.deleted_at.is_(None),
                Candidate.tenant_id == tenant_id,
                active_stage,
            )
        )
    ).scalar_one() or 0

    reminder_exists = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == Candidate.id,
            Reminder.assignee_id == assignee_id,
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
                active_stage,
                ~reminder_exists,
            )
        )
    ).scalar_one() or 0

    overdue = await count_overdue_reminders_ops_scoped(
        db, tenant_id=tenant_id, assignee_id=assignee_id
    )

    coverage = 0.0
    if int(active_pipeline_candidates) > 0:
        coverage = max(
            0.0,
            min(100.0, (1.0 - (float(no_next_action) / float(active_pipeline_candidates))) * 100.0),
        )

    return {
        "total_candidates": int(total_candidates),
        "active_pipeline_candidates": int(active_pipeline_candidates),
        "no_next_action_candidates": int(no_next_action),
        "next_action_coverage_percent": round(coverage, 2),
        "overdue_reminders": int(overdue),
    }


@router.get("/analytics/goals", response_model=GoalsOut)
async def get_goals(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    settings = _safe_settings(tenant)
    goals = _get_goals_config(settings)
    metrics = await _compute_metrics(db, tenant_id=tenant_id, assignee_id=str(ctx.sub))

    share_url = None
    if tenant.status_sharing_allowed is True:
        settings2, token, rotated = _ensure_share_token(settings)
        if rotated:
            tenant.settings = settings2
            await db.commit()
        share_url = f"/api/v1/public/goals/{token}"

    return GoalsOut(generated_at=datetime.now(timezone.utc), goals=goals, metrics=metrics, share_url=share_url)


@router.put("/analytics/goals", response_model=GoalsOut)
async def put_goals(
    body: GoalsConfigIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
):
    if str(ctx.role or "").lower() not in {"administrator", "superadmin", "admin", "supervisor", "owner"}:
        raise HTTPException(status_code=403, detail="forbidden")
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    settings = _safe_settings(tenant)
    settings["goals_v1"] = [g.model_dump(exclude_none=True) for g in body.goals]
    tenant.settings = settings
    await db.commit()

    goals = _get_goals_config(settings)
    metrics = await _compute_metrics(db, tenant_id=tenant_id, assignee_id=str(ctx.sub))
    return GoalsOut(generated_at=datetime.now(timezone.utc), goals=goals, metrics=metrics, share_url=None)

