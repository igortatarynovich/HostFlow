"""Manual vacancy confirmation for intake routing (Intake Resolution MVP — slice 1).

Recruiter explicitly commits which vacancy applies before conversion. Stamps
``normalized.intake_vacancy_confirm_v1`` so ``process_normalized_lead`` can
triage-bypass assisted / fit gates without silent automation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.app.models.user import Role
from backend.app.modules.leads import crud
from backend.app.modules.leads.service._helpers import (
    LeadProcessingError,
    _build_lead_outcome,
    _emit_lead_event,
    _load_tenant_business_type,
)
from backend.app.services.audit import log_activity

_ALLOWED_CONFIRM_STATUSES = frozenset({"new", "needs_routing", "failed"})
_MANUAL_SOURCES = frozenset({"meta", "csv_import"})
_ERRORS_CLEARED_ON_CONFIRM = frozenset(
    {"VACANCY_NOT_RESOLVED", "LEAD_FIT_NO_MATCH", "LEAD_FIT_NEEDS_INFO"}
)


async def confirm_lead_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    vacancy_id: str,
    actor_sub: Optional[str],
) -> Lead:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if not lead:
        raise LeadProcessingError("not_found", "LEAD_NOT_FOUND")

    src = str(getattr(lead, "source", "") or "").strip().lower()
    if src not in _MANUAL_SOURCES:
        raise LeadProcessingError("invalid", "LEAD_SOURCE_NOT_CONFIRMABLE")

    st = str(getattr(lead, "status", "") or "").strip().lower()
    if st not in _ALLOWED_CONFIRM_STATUSES:
        raise LeadProcessingError("invalid", "LEAD_STATUS_NOT_CONFIRMABLE")

    if getattr(lead, "candidate_id", None):
        raise LeadProcessingError("invalid", "LEAD_ALREADY_CONVERTED")

    scope_oc = str(getattr(lead, "own_company_id", None) or "").strip() or None
    vacancy = await crud.resolve_vacancy_by_id(
        db, tenant_id, vacancy_id, scoped_own_company_id=scope_oc
    )
    if vacancy is None:
        vacancy = await crud.resolve_vacancy_by_id(
            db, tenant_id, vacancy_id, scoped_own_company_id=None
        )
    if vacancy is None:
        raise LeadProcessingError("needs_routing", "VACANCY_NOT_FOUND")

    if str(vacancy.tenant_id) != str(tenant_id):
        raise LeadProcessingError("needs_routing", "VACANCY_NOT_FOUND")

    norm = dict(lead.normalized or {})
    prev_confirm = norm.get("intake_vacancy_confirm_v1")
    prev_vid: Optional[str] = None
    if isinstance(prev_confirm, dict):
        prev_vid = str(prev_confirm.get("vacancy_id") or "").strip() or None

    now_iso = datetime.now(timezone.utc).isoformat()
    norm["vacancy_id"] = str(vacancy.id)
    norm["resolved_vacancy_id"] = str(vacancy.id)
    norm["intake_vacancy_confirm_v1"] = {
        "vacancy_id": str(vacancy.id),
        "confirmed_at": now_iso,
        "confirmed_by": str(actor_sub).strip() if actor_sub else None,
    }

    err = getattr(lead, "error", None)
    err_s = str(err).strip() if err else ""
    new_error = None if err_s in _ERRORS_CLEARED_ON_CONFIRM else (err if err else None)

    lead.vacancy_id = str(vacancy.id)
    lead.company_id = vacancy.company_id
    v_oci = getattr(vacancy, "own_company_id", None)
    if v_oci:
        lead.own_company_id = str(v_oci)
    lead.normalized = norm
    lead.error = new_error

    await db.flush()

    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=str(actor_sub).strip() if actor_sub else None,
            action="lead.vacancy_confirmed",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "vacancy_id": str(vacancy.id),
                "previous_confirmed_vacancy_id": prev_vid,
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
    event_type = (
        "lead.vacancy_changed"
        if prev_vid and prev_vid != str(vacancy.id)
        else "lead.vacancy_confirmed"
    )
    await _emit_lead_event(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type=event_type,
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
