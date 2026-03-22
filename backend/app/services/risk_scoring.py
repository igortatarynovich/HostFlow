from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import pow
from typing import Dict, List, Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.communication import CommunicationThread
from backend.app.models.reminder import Reminder, ReminderStatus


@dataclass(frozen=True)
class CandidateRisk:
    risk_score: int  # 0..100
    risk_band: str  # low|medium|high|critical
    risk_updated_at: datetime
    risk_drivers: List[str]
    risk_version: str


def _clamp_int(v: float, lo: int = 0, hi: int = 100) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return int(round(v))


def _half_life_score(t: float, half_life: float) -> float:
    """
    Convert delay `t` to a rising score in [0..100] with exponential decay:
      decay = 0.5^(t / half_life)
      score = 100 * (1 - decay)
    """
    if half_life <= 0:
        return 0.0
    if t <= 0:
        return 0.0
    decay = pow(0.5, t / half_life)
    return 100.0 * (1.0 - decay)


def _band_from_score(score: int) -> str:
    if score < 35:
        return "low"
    if score < 65:
        return "medium"
    if score < 85:
        return "high"
    return "critical"


async def compute_candidate_risk_scores(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidates_by_id: Dict[str, Candidate],
    now: datetime,
    # The "current" logic is a transparent v1 heuristic; keep config in one place.
    half_life_engagement_hours: float = 36.0,
    half_life_stage_days: float = 7.0,
    half_life_next_action_hours: float = 24.0,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),  # engagement, stage, next_action
) -> Dict[str, CandidateRisk]:
    """
    Minimal v1 risk scoring:
      - engagement delay risk: candidate.created_at -> any outbound after it?
      - stage stagnation risk: days since last stage change into current stage
      - next-action discipline risk:
          - no active reminder -> time since candidate.updated_at
          - overdue reminder(s) -> lateness based score
    """
    if not candidates_by_id:
        return {}

    ids = [str(cid) for cid in candidates_by_id.keys() if str(cid)]
    if not ids:
        return {}

    risk_version = "risk_model_v1"
    now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)

    def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    # ---- 1) Communication: last outbound after candidate creation?
    comm_stmt = (
        select(
            CommunicationThread.entity_id.label("candidate_id"),
            func.max(CommunicationThread.last_outbound_at).label("last_outbound_at"),
            func.max(CommunicationThread.last_inbound_at).label("last_inbound_at"),
        )
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.entity_type == "candidate",
            CommunicationThread.entity_id.in_(ids),
        )
        .group_by(CommunicationThread.entity_id)
    )
    comm_rows = (await db.execute(comm_stmt)).all()
    comm_by_id: Dict[str, dict] = {}
    for row in comm_rows:
        comm_by_id[str(row.candidate_id)] = {
            "last_outbound_at": row.last_outbound_at,
            "last_inbound_at": row.last_inbound_at,
        }

    # ---- 2) Next action: active reminders + overdue counts
    active_statuses = (ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue)
    overdue_cond = or_(
        Reminder.status == ReminderStatus.overdue,
        Reminder.due_at < now_utc,
    )

    rem_stmt = (
        select(
            Reminder.entity_id.label("candidate_id"),
            func.count(Reminder.id).label("active_count"),
            func.sum(case((overdue_cond, 1), else_=0)).label("overdue_count"),
            func.min(case((overdue_cond, Reminder.due_at), else_=None)).label("min_overdue_due_at"),
        )
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "candidate",
            Reminder.entity_id.in_(ids),
            Reminder.status.in_(active_statuses),
        )
        .group_by(Reminder.entity_id)
    )
    rem_stmt = rem_stmt  # keep name for readability
    rem_rows = (await db.execute(rem_stmt)).all()
    rem_by_id: Dict[str, dict] = {}
    for row in rem_rows:
        rem_by_id[str(row.candidate_id)] = {
            "active_count": int(row.active_count or 0),
            "overdue_count": int(row.overdue_count or 0),
            "min_overdue_due_at": row.min_overdue_due_at,
        }

    # ---- 3) Stage stagnation: max `at` for current stage
    stage_stmt = (
        select(
            CandidateStageHistory.candidate_id.label("candidate_id"),
            CandidateStageHistory.to_code.label("to_code"),
            CandidateStageHistory.at.label("at"),
        )
        .where(
            CandidateStageHistory.tenant_id == tenant_id,
            CandidateStageHistory.candidate_id.in_(ids),
        )
    )
    stage_rows = (await db.execute(stage_stmt)).all()
    stage_entries_by_id: Dict[str, list] = {}
    for row in stage_rows:
        stage_entries_by_id.setdefault(str(row.candidate_id), []).append((row.to_code, row.at))

    # ---- 4) Build risk per candidate
    w_eng, w_stage, w_next = weights
    out: Dict[str, CandidateRisk] = {}

    for cid, cand in candidates_by_id.items():
        cid = str(cid)
        created_at = _to_utc(getattr(cand, "created_at", None)) or now_utc
        updated_at = _to_utc(getattr(cand, "updated_at", None)) or now_utc
        current_stage = cand.stage

        # 1) Engagement component
        comm = comm_by_id.get(cid) or {}
        last_outbound_at = comm.get("last_outbound_at")
        contacted = False
        if last_outbound_at is not None:
            try:
                contacted = _to_utc(last_outbound_at) > created_at
            except Exception:
                contacted = False

        if contacted:
            engagement_score = 0.0
            engagement_driver = None
        else:
            delay_hours = max(0.0, (now_utc - created_at).total_seconds() / 3600.0)
            engagement_score = _half_life_score(delay_hours, half_life_engagement_hours)
            engagement_driver = f"No first outbound after creation: {int(round(delay_hours))}h"

        # 2) Stage stagnation component
        stage_score = 0.0
        stage_driver = None
        if current_stage:
            latest_stage_at: Optional[datetime] = None
            for to_code, at in stage_entries_by_id.get(cid, []):
                if to_code != current_stage:
                    continue
                if latest_stage_at is None or at > latest_stage_at:
                    latest_stage_at = _to_utc(at) or at
            if latest_stage_at is None:
                latest_stage_at = created_at
            delay_days = max(0.0, (now_utc - latest_stage_at).total_seconds() / 86400.0)
            stage_score = _half_life_score(delay_days, half_life_stage_days)
            stage_driver = f"Stuck in stage '{current_stage}': {delay_days:.1f}d"

        # 3) Next-action discipline component
        rem = rem_by_id.get(cid) or {}
        active_count = int(rem.get("active_count") or 0)
        overdue_count = int(rem.get("overdue_count") or 0)
        next_action_score = 0.0
        next_action_driver = None
        if active_count <= 0:
            inactivity_hours = max(0.0, (now_utc - updated_at).total_seconds() / 3600.0)
            next_action_score = _half_life_score(inactivity_hours, half_life_next_action_hours)
            next_action_driver = f"No active next action: {int(round(inactivity_hours))}h since update"
        else:
            if overdue_count > 0:
                min_overdue_due_at = rem.get("min_overdue_due_at")
                if min_overdue_due_at is None:
                    lateness_hours = half_life_next_action_hours
                else:
                    lateness_hours = max(0.0, (now_utc - min_overdue_due_at).total_seconds() / 3600.0)
                next_action_score = _half_life_score(lateness_hours, half_life_next_action_hours)
                next_action_driver = f"{overdue_count} overdue next action(s)"
            else:
                next_action_score = 0.0
                next_action_driver = "Next action scheduled"

        overall = _clamp_int(w_eng * engagement_score + w_stage * stage_score + w_next * next_action_score)

        # Choose top drivers by component contribution
        drivers: List[str] = []
        comp = [
            (engagement_score, engagement_driver),
            (stage_score, stage_driver),
            (next_action_score, next_action_driver),
        ]
        comp_sorted = sorted([x for x in comp if x[0] > 0.01 and x[1]], key=lambda x: x[0], reverse=True)
        for _, d in comp_sorted[:3]:
            if d:
                drivers.append(d)
        if not drivers:
            drivers = ["At risk drivers not detected yet"]

        out[cid] = CandidateRisk(
            risk_score=overall,
            risk_band=_band_from_score(overall),
            risk_updated_at=now_utc,
            risk_drivers=drivers,
            risk_version=risk_version,
        )

    return out

