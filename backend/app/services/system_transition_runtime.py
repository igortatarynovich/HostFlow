"""ADR-035: fire platform system transitions (not stage writes)."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants import system_transitions as st
from backend.app.models.candidate import Candidate
from backend.app.models.funnel import Funnel, FunnelStage, FunnelTransitionEdge

logger = logging.getLogger(__name__)


async def list_edges_for_funnel(db: AsyncSession, funnel_id: str) -> list[FunnelTransitionEdge]:
    res = await db.execute(
        select(FunnelTransitionEdge)
        .where(FunnelTransitionEdge.funnel_id == funnel_id)
        .order_by(FunnelTransitionEdge.order)
    )
    return list(res.scalars().all())


async def ensure_default_recruitment_transitions(
    db: AsyncSession,
    *,
    funnel: Funnel,
    hr_enabled: bool,
) -> None:
    """Wire catalog exits on a new candidate pipeline instance (idempotent)."""
    existing = await list_edges_for_funnel(db, funnel.id)
    have = {(e.catalog_key, e.from_stage_id) for e in existing}

    stages_res = await db.execute(
        select(FunnelStage).where(FunnelStage.funnel_id == funnel.id).order_by(FunnelStage.order)
    )
    stages = list(stages_res.scalars().all())
    accepted = next((s for s in stages if s.code in ("accepted", "ready_for_client", "ready_for_handoff")), None)
    from_id = accepted.id if accepted else (stages[-1].id if stages else None)

    keys: list[str] = [st.CLOSE_DECLINED, st.HANDOFF_TO_CLIENT]
    if hr_enabled:
        keys.insert(0, st.HANDOFF_TO_HR)
    keys.append(st.CLOSE_SUCCESS)

    order = 0
    for key in keys:
        pair = (key, from_id)
        if pair in have or any(e.catalog_key == key for e in existing):
            continue
        db.add(
            FunnelTransitionEdge(
                id=str(uuid4()),
                funnel_id=funnel.id,
                catalog_key=key,
                from_stage_id=from_id,
                order=order,
                config_json={},
            )
        )
        order += 1


async def fire_candidate_system_transition(
    db: AsyncSession,
    *,
    candidate: Candidate,
    catalog_key: str,
    enabled_modules: set[str] | None = None,
    config_override: Optional[dict[str, Any]] = None,
) -> Candidate:
    """Execute a catalog transition for a Candidate. Never sets stage=transition."""
    key = str(catalog_key or "").strip()
    tdef = st.get_transition(key)
    if tdef is None:
        raise HTTPException(status_code=422, detail=f"Unknown system transition '{key}'")
    if tdef.source_module not in ("*", "recruitment") or tdef.source_object_type not in (
        "*",
        "candidate",
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Transition '{key}' is not valid for Recruitment/Candidate",
        )
    req = tdef.requires_enabled_module
    enabled = {m.lower() for m in (enabled_modules or set())}
    if req and req not in enabled:
        raise HTTPException(
            status_code=422,
            detail=f"Transition '{key}' requires module '{req}' enabled for company",
        )

    life = (getattr(candidate, "lifecycle_status", None) or st.LIFECYCLE_ACTIVE).lower()
    if life in (st.LIFECYCLE_CLOSED, st.LIFECYCLE_ARCHIVED):
        raise HTTPException(status_code=409, detail="Candidate is closed (read-only)")

    # Close candidate operationally
    candidate.lifecycle_status = st.LIFECYCLE_CLOSED

    if key == st.HANDOFF_TO_HR:
        # Materialization remains existing handoff_from_candidate path (callers).
        # Mark intent on extra for strangler consumers.
        extra = {}
        try:
            import json

            raw = getattr(candidate, "extra", None) or "{}"
            extra = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
        except Exception:
            extra = {}
        extra["adr035_last_transition"] = {
            "catalog_key": key,
            "create_employee": True,
            "config": config_override or {},
        }
        import json

        candidate.extra = json.dumps(extra)
    elif key == st.HANDOFF_TO_CLIENT:
        try:
            import json

            raw = getattr(candidate, "extra", None) or "{}"
            extra = json.loads(raw) if isinstance(raw, str) else dict(raw or {})
            extra["adr035_last_transition"] = {"catalog_key": key, "create_employee": False}
            candidate.extra = json.dumps(extra)
        except Exception:
            pass
    elif key in (st.CLOSE_SUCCESS, st.CLOSE_DECLINED):
        if key == st.CLOSE_DECLINED and not candidate.stage:
            candidate.stage = "rejected"

    logger.info(
        "adr035_system_transition_fired candidate=%s key=%s",
        getattr(candidate, "id", None),
        key,
    )
    return candidate


def sync_pipeline_stage_id(candidate: Candidate, stages: list[FunnelStage]) -> None:
    """Keep pipeline_stage_id aligned with legacy stage code when possible."""
    code = (getattr(candidate, "stage", None) or "").strip()
    if not code:
        return
    match = next((s for s in stages if s.code == code), None)
    if match is not None:
        candidate.pipeline_stage_id = match.id
