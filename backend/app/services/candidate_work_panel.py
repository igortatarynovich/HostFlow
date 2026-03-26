"""Aggregate payload for Candidates list work panel (R1.5 Phase D)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.reminders_v2 import ReminderOut
from backend.app.services import reminder_tasks
from backend.app.services.candidate_timeline import fetch_candidate_timeline_events

if TYPE_CHECKING:
    from backend.app.auth.deps import UserCtx
    from backend.app.models.candidate import Candidate

from backend.app.constants.spa_paths import EMAIL_LEGACY, MESSAGES_LEGACY, spa_candidate_documents
from backend.app.constants.stages import is_pipeline_completed_stage

logger = logging.getLogger(__name__)


async def _profile_ops(
    db: AsyncSession,
    tenant_id_str: str,
    candidate_id: str,
    cand_row: Candidate,
):
    from backend.app.api.v1.candidates.schemas import CandidateWorkPanelProfileOut

    contact_policy_enabled = False
    contact_attempt_count = 0
    try:
        from backend.app.services.contact_attempts import (
            count_contact_attempts,
            get_effective_contact_policy,
        )

        pol = await get_effective_contact_policy(db, tenant_id_str, cand_row)
        contact_policy_enabled = bool(pol.get("enabled"))
        contact_attempt_count = await count_contact_attempts(db, str(cand_row.id))
    except Exception:
        logger.exception("work_panel contact readiness enrich failed for candidate %s", candidate_id)

    risk_score = None
    risk_band = None
    risk_drivers: list[str] = []
    risk_updated_at = None
    risk_version = None
    try:
        now_r = datetime.now(timezone.utc)
        if is_pipeline_completed_stage(getattr(cand_row, "stage", None)):
            risk_score = 0
            risk_band = "low"
            risk_drivers = []
            risk_updated_at = now_r.isoformat()
            risk_version = "risk_model_v1"
        else:
            from backend.app.services.risk_intel_v1 import compute_candidate_risk_map_for_ids

            rmap = await compute_candidate_risk_map_for_ids(db, tenant_id_str, [str(candidate_id)], now=now_r)
            r = rmap.get(str(candidate_id))
            if r:
                risk_score = r["risk_score"]
                risk_band = r["risk_band"]
                risk_drivers = list(r.get("risk_drivers") or [])
                ru = r.get("risk_updated_at")
                risk_updated_at = ru.isoformat() if ru and hasattr(ru, "isoformat") else None
                risk_version = r.get("risk_version")
    except Exception:
        logger.exception("work_panel risk enrich failed for candidate %s", candidate_id)

    return CandidateWorkPanelProfileOut(
        contact_policy_enabled=contact_policy_enabled,
        contact_attempt_count=contact_attempt_count,
        risk_score=risk_score,
        risk_band=risk_band,
        risk_drivers=risk_drivers,
        risk_updated_at=risk_updated_at,
        risk_version=risk_version,
    )


async def load_candidate_work_panel(
    db: AsyncSession,
    tenant_id_str: str,
    candidate_id: str,
    current_user: UserCtx,
    cand_row: Candidate,
    *,
    timeline_limit: int = 80,
    assignee_scope: str = "mine",
):
    """Bundle: profile ops + reminders + timeline + comms URLs + optional documents_summary (owner checklist blockers)."""

    from backend.app.api.v1.candidates.schemas import (
        CandidateTimelineResponse,
        CandidateWorkPanelCommsOut,
        CandidateWorkPanelDocumentsSummaryOut,
        CandidateWorkPanelResponse,
    )
    from backend.app.modules.documents.router import fetch_candidate_documents_summary_response

    aid = reminder_tasks.resolve_assignee_for_reminder_list(
        explicit_assignee_id=None,
        assignee_scope=assignee_scope,
        viewer_id=str(current_user.sub),
        viewer_role=str(current_user.role),
    )

    async def reminders_task():
        rows = await reminder_tasks.list_reminders(
            db,
            tenant_id=tenant_id_str,
            assignee_id=aid,
            entity=("candidate", str(candidate_id)),
            status_in=["pending", "new", "overdue"],
        )
        return [ReminderOut.from_model(r) for r in rows]

    profile, timeline_events, reminders = await asyncio.gather(
        _profile_ops(db, tenant_id_str, candidate_id, cand_row),
        fetch_candidate_timeline_events(db, tenant_id_str, str(candidate_id), timeline_limit),
        reminders_task(),
    )

    documents_summary: CandidateWorkPanelDocumentsSummaryOut | None = None
    try:
        raw = await fetch_candidate_documents_summary_response(
            db, tenant_id_str, UUID(str(candidate_id)), owner_context=None
        )
        s = raw.get("summary") or {}
        req = s.get("required") or {}
        documents_summary = CandidateWorkPanelDocumentsSummaryOut(
            percent_ready=int(s.get("percent_ready") or 0),
            status=s.get("status") if isinstance(s.get("status"), str) else None,
            missing=[str(x) for x in (req.get("missing") or [])],
            problematic=[str(x) for x in (req.get("problematic") or [])],
            ready_types=[str(x) for x in (req.get("ready_types") or [])],
            in_progress_types=[str(x) for x in (req.get("in_progress_types") or [])],
            expiring_soon=[
                x for x in (s.get("expiring_soon") or []) if isinstance(x, dict)
            ],
        )
    except Exception:
        logger.exception("work_panel documents summary failed candidate=%s", candidate_id)

    cid = str(candidate_id)
    comms = CandidateWorkPanelCommsOut(
        messages_relative_url=f"{MESSAGES_LEGACY}?candidateId={cid}",
        email_relative_url=f"{EMAIL_LEGACY}?candidateId={cid}",
        documents_relative_url=spa_candidate_documents(cid),
    )

    return CandidateWorkPanelResponse(
        profile=profile,
        reminders=reminders,
        timeline=CandidateTimelineResponse(items=timeline_events),
        comms=comms,
        documents_summary=documents_summary,
    )
