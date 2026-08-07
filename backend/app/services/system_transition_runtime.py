"""ADR-035: fire platform system transitions (not stage writes)."""

from __future__ import annotations

import json
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
    accepted = next(
        (s for s in stages if s.code in ("accepted", "ready_for_client", "ready_for_handoff")),
        None,
    )
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


def _read_extra(candidate: Candidate) -> dict[str, Any]:
    try:
        raw = getattr(candidate, "extra", None) or "{}"
        if isinstance(raw, dict):
            return dict(raw)
        return json.loads(raw) if isinstance(raw, str) else {}
    except Exception:
        return {}


def _write_extra(candidate: Candidate, extra: dict[str, Any]) -> None:
    candidate.extra = json.dumps(extra)


async def fire_candidate_system_transition(
    db: AsyncSession,
    *,
    candidate: Candidate,
    catalog_key: str,
    tenant_id: str,
    actor_user_id: str,
    enabled_modules: set[str] | None = None,
    config_override: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Execute a catalog transition for a Candidate.

    Never sets ``stage`` to a transition key. Returns a result dict for the API.
    """
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

    cfg = dict(config_override or {})
    extra = _read_extra(candidate)
    result: dict[str, Any] = {
        "candidate_id": str(candidate.id),
        "catalog_key": key,
        "employee_id": None,
        "handoff_id": None,
    }

    # Close candidate operationally (board position freeze via lifecycle)
    candidate.lifecycle_status = st.LIFECYCLE_CLOSED

    if key == st.HANDOFF_TO_HR:
        create_employee = cfg.get("create_employee", True)
        if create_employee is False:
            extra["adr035_last_transition"] = {
                "catalog_key": key,
                "create_employee": False,
                "config": cfg,
            }
            _write_extra(candidate, extra)
        else:
            from backend.app.services.workforce_employees import handoff_from_candidate

            employee = await handoff_from_candidate(
                db,
                str(tenant_id),
                candidate,
                hire_date=None,
                actor_user_id=str(actor_user_id),
                seed_hr_bundle=True,
            )
            result["employee_id"] = str(getattr(employee, "id", None) or "") or None
            extra["adr035_last_transition"] = {
                "catalog_key": key,
                "create_employee": True,
                "employee_id": result["employee_id"],
                "config": cfg,
            }
            _write_extra(candidate, extra)

    elif key == st.HANDOFF_TO_CLIENT:
        handoff_id: str | None = None
        company_id = str(getattr(candidate, "company_id", None) or "").strip() or None
        if company_id and actor_user_id:
            # Align with legacy create_handoff stage gate (strangler)
            if (getattr(candidate, "stage", None) or "").strip().lower() not in (
                "ready_for_handoff",
                "ready_for_client",
                "accepted",
            ):
                candidate.stage = "ready_for_handoff"
            from backend.app.services.handoff import create_handoff

            handoff, err = await create_handoff(
                db,
                candidate_id=str(candidate.id),
                agency_tenant_id=str(tenant_id),
                client_company_id=company_id,
                requested_by_user_id=str(actor_user_id),
                destination="client_portal",
            )
            if err:
                # Soft: still close candidate; surface warning in result
                logger.warning(
                    "adr035 handoff_to_client create_handoff skipped candidate=%s err=%s",
                    candidate.id,
                    err,
                )
                result["handoff_warning"] = err if isinstance(err, str) else str(err)
            elif handoff is not None:
                handoff_id = str(handoff.id)
                result["handoff_id"] = handoff_id
        extra["adr035_last_transition"] = {
            "catalog_key": key,
            "create_employee": False,
            "handoff_id": handoff_id,
            "config": cfg,
        }
        _write_extra(candidate, extra)

    elif key == st.CLOSE_DECLINED:
        candidate.stage = "rejected"
        extra["adr035_last_transition"] = {"catalog_key": key}
        _write_extra(candidate, extra)

    elif key == st.CLOSE_SUCCESS:
        if not (getattr(candidate, "stage", None) or "").strip():
            candidate.stage = "accepted"
        extra["adr035_last_transition"] = {"catalog_key": key}
        _write_extra(candidate, extra)

    else:
        raise HTTPException(status_code=422, detail=f"Unsupported transition '{key}'")

    result["lifecycle_status"] = candidate.lifecycle_status
    result["stage"] = getattr(candidate, "stage", None)

    logger.info(
        "adr035_system_transition_fired candidate=%s key=%s employee=%s handoff=%s",
        getattr(candidate, "id", None),
        key,
        result.get("employee_id"),
        result.get("handoff_id"),
    )
    return result


def sync_pipeline_stage_id(candidate: Candidate, stages: list[FunnelStage]) -> None:
    """Keep pipeline_stage_id aligned with legacy stage code when possible."""
    code = (getattr(candidate, "stage", None) or "").strip()
    if not code:
        return
    match = next((s for s in stages if s.code == code), None)
    if match is not None:
        candidate.pipeline_stage_id = match.id
