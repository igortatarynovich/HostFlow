"""
Opt-in forward stage gate: high/critical risk without an active next-action reminder.

Configured via Tenant.settings.risk_model_v1.stage_gate (merged in resolve_risk_config).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import TERMINAL_STATUSES, is_pipeline_completed_stage
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.tenant import Tenant
from backend.app.services.automation_rules import risk_band_at_least
from backend.app.services.candidate_doc_pipeline_guard import is_forward_pipeline_move
from backend.app.services.handoff import is_client_tenant
from backend.app.services.risk_intel_v1 import compute_candidate_risk_map_for_ids, resolve_risk_config

_ACTIVE_REMINDER_STATUSES = (
    ReminderStatus.pending,
    ReminderStatus.new,
    ReminderStatus.overdue,
)


async def _tenant_risk_model_config(db: AsyncSession, tenant_id: str) -> dict:
    row = await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id).limit(1))
    settings = row.scalar_one_or_none()
    return resolve_risk_config(settings if isinstance(settings, dict) else {})


async def _count_active_candidate_reminders(db: AsyncSession, tenant_id: str, candidate_id: str) -> int:
    r = await db.execute(
        select(func.count())
        .select_from(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == str(candidate_id),
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
    )
    return int(r.scalar_one() or 0)


async def enforce_critical_risk_forward_stage_gate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    old_stage: Optional[str],
    new_stage: str,
) -> None:
    """
    When stage_gate.enabled and block_forward_without_next_action: block forward pipeline
    transitions if risk band >= min_band and the candidate has no active reminder.
    Exempt: client tenants, non-forward moves, moves into terminal stages, forward moves from pipeline-completed stages.
    """
    if await is_client_tenant(db, tenant_id):
        return
    if not is_forward_pipeline_move(old_stage, new_stage):
        return
    if is_pipeline_completed_stage(old_stage):
        return
    ns = str(new_stage or "").strip().lower()
    if ns in TERMINAL_STATUSES:
        return

    cfg = await _tenant_risk_model_config(db, tenant_id)
    sg = cfg.get("stage_gate")
    if not isinstance(sg, dict) or sg.get("enabled") is not True:
        return
    if sg.get("block_forward_without_next_action", True) is not True:
        return

    min_band = str(sg.get("min_band") or "critical").strip().lower()

    if await _count_active_candidate_reminders(db, tenant_id, candidate_id) > 0:
        return

    now = datetime.now(timezone.utc)
    rmap = await compute_candidate_risk_map_for_ids(db, tenant_id, [str(candidate_id)], now=now)
    row = rmap.get(str(candidate_id))
    if not row:
        return
    band = str(row.get("risk_band") or "").strip().lower()
    if not risk_band_at_least(band, min_band):
        return

    raise HTTPException(
        status_code=409,
        detail={
            "code": "stage_blocked_by_risk_gate",
            "message": (
                f"Cannot move stage forward: risk band is '{band}' (threshold '{min_band}') "
                "and there is no active next action. Create a reminder (next action) first, "
                "or adjust Tenant.settings.risk_model_v1.stage_gate."
            ),
            "risk_band": band,
            "risk_score": row.get("risk_score"),
            "min_band": min_band,
        },
    )
