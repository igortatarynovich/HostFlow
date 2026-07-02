"""Manual resolution for leads in ``duplicate_review`` (operational loop)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Candidate, Lead
from backend.app.modules.leads import crud
from backend.app.modules.leads.duplicate_resolution import record_exact_duplicate_lead_intake
from backend.app.services.audit import log_activity
from backend.app.modules.leads.lead_candidate_conversion import (
    ensure_recruitment_application_for_converted_lead,
)
from backend.app.services.lead_lifecycle import apply_lead_terminal_cleanup

DUPLICATE_DECISIONS = frozenset({"attach_existing", "create_new", "ignore"})


def _append_duplicate_decision_history(
    normalized: dict[str, Any],
    *,
    actor_id: Optional[str],
    decision: str,
    note: Optional[str],
    suggested_prior: Optional[str],
    outcome: Optional[str] = None,
) -> None:
    hist = normalized.get("duplicate_decisions_history_v1")
    if not isinstance(hist, list):
        hist = []
    row: dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "actor_id": actor_id,
        "decision": decision,
        "note": (note or "").strip() or None,
        "suggested_candidate_id_prior": suggested_prior,
    }
    if outcome:
        row["outcome"] = outcome
    hist.append(row)
    normalized["duplicate_decisions_history_v1"] = hist[-50:]


async def apply_lead_duplicate_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    actor_id: Optional[str],
    decision: str,
    note: Optional[str] = None,
) -> Lead:
    """
    Apply operator decision for ``duplicate_review`` leads.

    - ``attach_existing``: link lead to suggested candidate, append intake trail, terminal cleanup.
    - ``create_new`` / ``ignore``: skip suggested id on next ingest (``duplicate_override_v1``),
      clear review state, return lead to ``needs_routing`` for ``POST /process``.
    """
    d = str(decision or "").strip().lower()
    if d not in DUPLICATE_DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INVALID_DUPLICATE_DECISION",
        )

    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if str(getattr(lead, "status", "") or "") != "duplicate_review":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LEAD_NOT_IN_DUPLICATE_REVIEW",
        )

    norm = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    dm = norm.get("duplicate_match_v1")
    suggested: Optional[str] = None
    if isinstance(dm, dict):
        raw = dm.get("suggested_candidate_id")
        if raw:
            suggested = str(raw).strip() or None
    reasons: list[str] = []
    if isinstance(dm, dict) and isinstance(dm.get("reasons"), list):
        reasons = [str(x) for x in dm["reasons"] if str(x).strip()]

    actor = str(actor_id).strip() if actor_id else None

    if d == "attach_existing":
        if not suggested:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DUPLICATE_SUGGESTION_MISSING",
            )
        cand = await db.get(Candidate, suggested)
        if cand is None or str(cand.tenant_id) != str(tenant_id) or cand.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SUGGESTED_CANDIDATE_NOT_FOUND",
            )
        _append_duplicate_decision_history(
            norm,
            actor_id=actor,
            decision=d,
            note=note,
            suggested_prior=suggested,
            outcome="attached",
        )
        norm.pop("duplicate_match_v1", None)
        norm["duplicate_resolution_v1"] = {
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "outcome": "attached",
            "candidate_id": str(cand.id),
            "actor_id": actor,
        }

        await crud.update_lead(
            db,
            lead,
            status="duplicated",
            candidate_id=str(cand.id),
            vacancy_id=lead.vacancy_id or cand.vacancy_id,
            normalized=norm,
            error=None,
        )
        await db.flush()
        await record_exact_duplicate_lead_intake(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate=cand,
            normalized=norm,
            match_reasons=reasons or ["manual_duplicate_attach"],
        )
        from backend.app.services.lead_context_carry import carry_lead_context_on_conversion

        await carry_lead_context_on_conversion(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate=cand,
            actor_id=actor,
        )
        await db.flush()
        vac_eff = lead.vacancy_id or cand.vacancy_id
        await ensure_recruitment_application_for_converted_lead(
            db,
            tenant_id=tenant_id,
            lead=lead,
            candidate=cand,
            vacancy_id=str(vac_eff) if vac_eff else None,
            recruiter_id=getattr(cand, "recruiter_id", None),
            source=str(getattr(lead, "source", None) or "meta"),
        )
        await db.flush()
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor,
            action="lead.duplicate_decision",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "decision": d,
                "candidate_id": str(cand.id),
                "note": (note or "").strip() or None,
            },
        )
        await db.flush()
        await db.commit()
        try:
            await apply_lead_terminal_cleanup(
                db,
                tenant_id=tenant_id,
                lead_id=str(lead.id),
                new_stage=getattr(lead, "stage", None),
                new_status=getattr(lead, "status", None),
                actor_id=actor,
                reason="lead_duplicate_decision_attach",
            )
            await db.commit()
        except Exception:
            await db.rollback()

        row = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
        assert row is not None
        return row

    # create_new | ignore — treat suggested match as false for this lead
    if not suggested:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="DUPLICATE_SUGGESTION_MISSING",
        )
    override = norm.get("duplicate_override_v1")
    if not isinstance(override, dict):
        override = {}
    ignored = override.get("ignored_candidate_ids")
    if not isinstance(ignored, list):
        ignored = []
    if suggested not in ignored:
        ignored.append(suggested)
    override["ignored_candidate_ids"] = ignored
    override["updated_at"] = datetime.now(timezone.utc).isoformat()
    if actor:
        override["updated_by"] = actor
    norm["duplicate_override_v1"] = override

    _append_duplicate_decision_history(
        norm,
        actor_id=actor,
        decision=d,
        note=note,
        suggested_prior=suggested,
        outcome="override_create_new" if d == "create_new" else "override_ignore",
    )
    norm.pop("duplicate_match_v1", None)
    norm["duplicate_resolution_v1"] = {
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "outcome": d,
        "ignored_candidate_id": suggested,
        "actor_id": actor,
    }

    await crud.update_lead(
        db,
        lead,
        status="needs_routing",
        candidate_id=None,
        vacancy_id=lead.vacancy_id,
        normalized=norm,
        error=None,
    )
    await db.flush()
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor,
        action="lead.duplicate_decision",
        target_type="lead",
        target_id=str(lead.id),
        payload={
            "decision": d,
            "ignored_candidate_id": suggested,
            "note": (note or "").strip() or None,
        },
    )
    await db.commit()
    row = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    assert row is not None
    return row
