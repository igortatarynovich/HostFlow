"""Lead intake resolution decisions (MVP slice 2) — qualify, reject, pool, request_info, duplicate_review.

These are **intake** outcomes, not candidate pipeline stages. Persistence lives in
``normalized.intake_resolution_v1``; reject also syncs CRM ``stage=lost`` +
``lead_lost_reason_v1`` without replacing intake semantics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.app.models.user import Role
from backend.app.modules.leads import crud
from backend.app.modules.leads.schemas import lead_vacancy_routing_aux
from backend.app.modules.leads.service._helpers import (
    LeadProcessingError,
    _build_lead_outcome,
    _emit_lead_event,
    _load_tenant_business_type,
)
from backend.app.services.lead_rodo import (
    LEAD_RODO_ACTION_PROCESS,
    LEAD_RODO_ACTION_REQUEST_INFO,
    ensure_lead_rodo_allows_action,
)
from backend.app.services.audit import log_activity
from backend.app.services.recruitment_application_service import _explicit_pool_intent

INTAKE_DECISION_QUALIFY = "qualify"
INTAKE_DECISION_REJECT = "reject"
INTAKE_DECISION_POOL = "pool"
INTAKE_DECISION_REQUEST_INFO = "request_info"
INTAKE_DECISION_DUPLICATE_REVIEW = "duplicate_review"

INTAKE_REJECT_REASON_CODES: frozenset[str] = frozenset(
    {
        "insufficient_experience",
        "missing_documents",
        "unsupported_citizenship",
        "language_mismatch",
        "invalid_contact",
        "no_response",
        "salary_mismatch",
        "unsuitable_route",
        "duplicate_spam",
        "not_interested",
        "other",
    }
)

_INTAKE_EVENT_BY_DECISION: Dict[str, str] = {
    INTAKE_DECISION_QUALIFY: "lead.intake_qualified",
    INTAKE_DECISION_REJECT: "lead.intake_rejected",
    INTAKE_DECISION_POOL: "lead.intake_pooled",
    INTAKE_DECISION_REQUEST_INFO: "lead.intake_info_requested",
    INTAKE_DECISION_DUPLICATE_REVIEW: "lead.intake_duplicate_review_requested",
}

_ALLOWED_LEAD_STATUSES = frozenset({"new", "needs_routing", "failed", "duplicate_review"})
_CLIENT_LEAD_INTAKE_STATUSES = _ALLOWED_LEAD_STATUSES | frozenset({"processed"})
_MANUAL_SOURCES = frozenset({"meta", "csv_import"})
CLIENT_LEAD_NOT_CANDIDATE = "CLIENT_LEAD_NOT_CANDIDATE"


def is_client_lead(lead: Lead) -> bool:
    lt = str(getattr(lead, "lead_type", "") or "").strip().lower()
    ltt = str(getattr(lead, "lead_target_type", "") or "").strip().lower()
    return lt == "client" and ltt == "client_lead"


def client_lead_rejection_finalized(lead: Lead) -> bool:
    """True when client lead rejection is fully persisted (status + intake stamp)."""
    if not is_client_lead(lead):
        return False
    st = str(getattr(lead, "status", "") or "").strip().lower()
    if st == "rejected":
        return True
    norm: Dict[str, Any] = lead.normalized if isinstance(lead.normalized, dict) else {}
    ir = norm.get("intake_resolution_v1")
    if isinstance(ir, dict) and str(ir.get("status") or "").strip().lower() == "rejected":
        return True
    return False


def client_lead_is_terminal(lead: Lead) -> bool:
    """UI / gating: client lead closed (including stage=lost before legacy rows are finalized)."""
    if client_lead_rejection_finalized(lead):
        return True
    if not is_client_lead(lead):
        return False
    if str(getattr(lead, "stage", "") or "").strip().lower() == "lost":
        return True
    return False


def lead_intake_terminal(lead: Lead) -> bool:
    """True when intake/CRM closed the lead — no repeat reject or lost transition."""
    if client_lead_rejection_finalized(lead):
        return True
    st = str(getattr(lead, "status", "") or "").strip().lower()
    if st == "rejected":
        return True
    err = str(getattr(lead, "error", "") or "").strip()
    if err == "INTAKE_REJECTED":
        return True
    norm: Dict[str, Any] = lead.normalized if isinstance(lead.normalized, dict) else {}
    ir = norm.get("intake_resolution_v1")
    if isinstance(ir, dict) and str(ir.get("status") or "").strip().lower() == "rejected":
        return True
    if str(getattr(lead, "stage", "") or "").strip().lower() == "lost" and norm.get("lead_lost_reason_v1"):
        return True
    return False


def apply_client_lead_rejection(
    lead: Lead,
    *,
    reason_code: Optional[str],
    note: Optional[str],
    actor_sub: Optional[str],
) -> None:
    """Terminalize a B2B client lead — not a candidate pipeline reject, but same intake stamp."""
    norm = dict(lead.normalized or {})
    rc_raw = str(reason_code or "").strip()
    intake_rc = rc_raw if rc_raw in INTAKE_REJECT_REASON_CODES else "other"
    _stamp_intake_resolution_v1(
        norm,
        status="rejected",
        reason_code=intake_rc,
        note=str(note).strip() if note else None,
        actor_sub=actor_sub,
        last_decision=INTAKE_DECISION_REJECT,
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    lr_block: Dict[str, Any] = {"at": now_iso, "code": rc_raw or intake_rc}
    if actor_sub:
        lr_block["set_by"] = str(actor_sub).strip()
    if note:
        lr_block["note"] = str(note).strip()
    norm["lead_lost_reason_v1"] = lr_block
    lead.stage = "lost"
    lead.status = "rejected"
    lead.error = "INTAKE_REJECTED"
    lead.normalized = norm


def pool_intake_manual_convert_ready(lead: Lead, normalized: Dict[str, Any]) -> bool:
    """True when explicit pool intent + intake resolution allow conversion without a committed vacancy."""
    if getattr(lead, "vacancy_id", None):
        return False
    if not _explicit_pool_intent(lead):
        return False
    ir = normalized.get("intake_resolution_v1")
    if not isinstance(ir, dict):
        return False
    st = str(ir.get("status") or "").strip().lower()
    return st in ("pooled", "qualified")


def _stamp_intake_resolution_v1(
    norm: Dict[str, Any],
    *,
    status: str,
    reason_code: Optional[str],
    note: Optional[str],
    actor_sub: Optional[str],
    last_decision: str,
) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    norm["intake_resolution_v1"] = {
        "status": status,
        "reason_code": reason_code,
        "decided_at": now_iso,
        "decided_by": str(actor_sub).strip() if actor_sub else None,
        "note": str(note).strip() if note else None,
        "last_decision": last_decision,
    }


async def manual_process_block_code(
    db: AsyncSession,
    tenant_id: str,
    lead: Lead,
) -> Optional[str]:
    """Return a stable machine code if ``POST .../process`` must be blocked, else None."""
    if getattr(lead, "candidate_id", None):
        return None
    if is_client_lead(lead):
        if client_lead_rejection_finalized(lead):
            return "INTAKE_REJECTED"
        return CLIENT_LEAD_NOT_CANDIDATE
    src = str(getattr(lead, "source", "") or "").strip().lower()
    if src not in _MANUAL_SOURCES:
        rodo = await ensure_lead_rodo_allows_action(
            db, tenant_id=tenant_id, lead=lead, action=LEAD_RODO_ACTION_PROCESS
        )
        if rodo:
            return rodo
        return None

    norm: Dict[str, Any] = lead.normalized if isinstance(lead.normalized, dict) else {}
    ir = norm.get("intake_resolution_v1")
    if isinstance(ir, dict) and str(ir.get("status") or "").strip().lower() == "rejected":
        return "INTAKE_REJECTED"

    if isinstance(ir, dict) and str(ir.get("status") or "").strip().lower() == "info_requested":
        return "INTAKE_INFO_REQUESTED"

    idv = norm.get("intake_identity_v1")
    if isinstance(idv, dict) and str(idv.get("status") or "").strip().lower() == "unclear":
        return "INTAKE_IDENTITY_UNCLEAR"

    lst = str(getattr(lead, "status", "") or "").strip().lower()
    if lst == "duplicate_review":
        return "DUPLICATE_REVIEW_PENDING"
    pool = _explicit_pool_intent(lead)
    has_vac = bool(getattr(lead, "vacancy_id", None))

    if pool and not has_vac:
        if not pool_intake_manual_convert_ready(lead, norm):
            return "INTAKE_POOL_PATH_REQUIRED"
        rodo = await ensure_lead_rodo_allows_action(
            db, tenant_id=tenant_id, lead=lead, action=LEAD_RODO_ACTION_PROCESS
        )
        return rodo if rodo else None

    if has_vac:
        _, vac_confirmed = lead_vacancy_routing_aux(norm, getattr(lead, "vacancy_id", None))
        if not vac_confirmed:
            return "VACANCY_NOT_CONFIRMED"
        rodo = await ensure_lead_rodo_allows_action(
            db, tenant_id=tenant_id, lead=lead, action=LEAD_RODO_ACTION_PROCESS
        )
        return rodo if rodo else None

    return "INTAKE_ROUTING_INCOMPLETE"


async def apply_lead_intake_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    decision: str,
    actor_sub: Optional[str],
    reason_code: Optional[str] = None,
    note: Optional[str] = None,
    funnel_id: Optional[str] = None,
) -> Lead:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if not lead:
        raise LeadProcessingError("not_found", "LEAD_NOT_FOUND")

    src = str(getattr(lead, "source", "") or "").strip().lower()
    if src not in _MANUAL_SOURCES:
        raise LeadProcessingError("invalid", "LEAD_SOURCE_INTAKE_DECISION_UNSUPPORTED")

    st = str(getattr(lead, "status", "") or "").strip().lower()
    allowed_statuses = (
        _CLIENT_LEAD_INTAKE_STATUSES if is_client_lead(lead) else _ALLOWED_LEAD_STATUSES
    )
    if st not in allowed_statuses:
        raise LeadProcessingError("invalid", "LEAD_STATUS_INTAKE_DECISION_UNSUPPORTED")

    if getattr(lead, "candidate_id", None):
        raise LeadProcessingError("invalid", "LEAD_ALREADY_CONVERTED")

    norm = dict(lead.normalized or {})
    prev_ir = norm.get("intake_resolution_v1")
    if isinstance(prev_ir, dict) and str(prev_ir.get("status") or "").strip().lower() == "rejected":
        raise LeadProcessingError("invalid", "LEAD_INTAKE_ALREADY_REJECTED")
    if lead_intake_terminal(lead):
        raise LeadProcessingError("invalid", "LEAD_INTAKE_ALREADY_REJECTED")

    dec = str(decision or "").strip().lower()
    note_s = str(note).strip() if note else None
    rc = str(reason_code).strip() if reason_code else None

    if dec == INTAKE_DECISION_REJECT:
        if not rc or rc not in INTAKE_REJECT_REASON_CODES:
            raise LeadProcessingError("invalid", "INTAKE_REJECT_REASON_REQUIRED")
        if is_client_lead(lead):
            apply_client_lead_rejection(
                lead,
                reason_code=rc,
                note=note_s,
                actor_sub=actor_sub,
            )
        else:
            _stamp_intake_resolution_v1(
                norm,
                status="rejected",
                reason_code=rc,
                note=note_s,
                actor_sub=actor_sub,
                last_decision=dec,
            )
            lead.stage = "lost"
            lr_block: Dict[str, Any] = {
                "at": datetime.now(timezone.utc).isoformat(),
                "code": f"intake_{rc}",
            }
            if actor_sub:
                lr_block["set_by"] = str(actor_sub).strip()
            if note_s:
                lr_block["note"] = note_s
            norm["lead_lost_reason_v1"] = lr_block
            lead.error = "INTAKE_REJECTED"
            lead.status = "rejected"
            lead.normalized = norm
        await db.flush()
        from backend.app.services.lead_communications import maybe_send_lead_rejected_notice
        from backend.app.services.lead_lifecycle import apply_lead_terminal_cleanup

        await maybe_send_lead_rejected_notice(db, tenant_id=tenant_id, lead=lead)
        await apply_lead_terminal_cleanup(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            new_stage=getattr(lead, "stage", None),
            new_status=getattr(lead, "status", None),
            actor_id=str(actor_sub).strip() if actor_sub else None,
            reason="lead_intake_rejected",
        )

    elif dec == INTAKE_DECISION_QUALIFY:
        _stamp_intake_resolution_v1(
            norm,
            status="qualified",
            reason_code=None,
            note=note_s,
            actor_sub=actor_sub,
            last_decision=dec,
        )
        cur_st = str(getattr(lead, "stage", "") or "").strip().lower()
        if cur_st in ("", "new", "lost"):
            lead.stage = "qualified"
        lead.normalized = norm
        await db.flush()

    elif dec == INTAKE_DECISION_POOL:
        norm["recruitment_pool_intent_v1"] = True
        from backend.app.services.recruitment_funnel_assignment import assign_recruitment_funnel_to_lead

        explicit_fid = str(funnel_id).strip() if funnel_id else None
        try:
            await assign_recruitment_funnel_to_lead(
                db,
                tenant_id=tenant_id,
                lead=lead,
                explicit_funnel_id=explicit_fid or None,
                pipeline_type="lead",
            )
        except HTTPException as exc:
            raise LeadProcessingError(
                "invalid" if exc.status_code == 403 else "invalid",
                str(exc.detail),
            ) from exc
        _stamp_intake_resolution_v1(
            norm,
            status="pooled",
            reason_code=None,
            note=note_s,
            actor_sub=actor_sub,
            last_decision=dec,
        )
        lead.normalized = norm
        await db.flush()

    elif dec == INTAKE_DECISION_REQUEST_INFO:
        if await ensure_lead_rodo_allows_action(
            db, tenant_id=tenant_id, lead=lead, action=LEAD_RODO_ACTION_REQUEST_INFO
        ):
            raise LeadProcessingError("invalid", "LEAD_RODO_REQUIRED")
        _stamp_intake_resolution_v1(
            norm,
            status="info_requested",
            reason_code=None,
            note=note_s,
            actor_sub=actor_sub,
            last_decision=dec,
        )
        lead.normalized = norm
        await db.flush()

    elif dec == INTAKE_DECISION_DUPLICATE_REVIEW:
        _stamp_intake_resolution_v1(
            norm,
            status="duplicate_review_requested",
            reason_code=None,
            note=note_s,
            actor_sub=actor_sub,
            last_decision=dec,
        )
        lead.status = "duplicate_review"
        lead.error = "INTAKE_DUPLICATE_REVIEW_REQUESTED"
        lead.normalized = norm
        await db.flush()

    else:
        raise LeadProcessingError("invalid", "INTAKE_DECISION_UNKNOWN")

    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=str(actor_sub).strip() if actor_sub else None,
            action=f"lead.intake_decision.{dec}",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "decision": dec,
                "reason_code": rc,
                "note": note_s,
            },
        )
    except Exception:
        pass

    business_type = await _load_tenant_business_type(db, tenant_id, getattr(lead, "own_company_id", None))
    outcome_entity_type, outcome_entity_id, outcome_entity_name = _build_lead_outcome(
        business_type=business_type,
        company_id=lead.company_id,
        company_name=None,
        candidate_id=None,
        candidate_name=None,
    )
    ev = _INTAKE_EVENT_BY_DECISION.get(dec)
    if ev:
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type=ev,
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type=outcome_entity_type,
            outcome_entity_id=outcome_entity_id,
            outcome_entity_name=outcome_entity_name,
            user_ids=[actor_sub] if actor_sub else None,
        )
    await db.commit()
    await db.refresh(lead)
    return lead
