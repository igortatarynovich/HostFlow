"""Explicit conversion use-case: Lead processing → Candidate dossier (v1 / v1.1).

Wraps ``create_candidate_full`` so ingestion does not scatter INSERT semantics.
See ``docs/specs/workflows/lead-conversion-contract.md`` and
``docs/specs/workflows/lead-ingestion-external-id-idempotency.md`` (lookup +
``uq_leads_tenant_source_external_id`` + optional ``IntegrityError`` recovery in
``process_normalized_lead``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.core.audit_events import AuditEntityType
from backend.app.models import Candidate, Lead, RecruitmentApplication
from backend.app.services.audit import log_audit_event
from backend.app.services.recruitment_application_service import (
    ensure_recruitment_application_for_lead_intent,
)

CONVERSION_CONTRACT_VERSION = "lead-conversion-contract@1"


async def ensure_recruitment_application_for_converted_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    candidate: Candidate,
    vacancy_id: Optional[str] = None,
    recruiter_id: Optional[str] = None,
    source: Optional[str] = None,
) -> Optional[RecruitmentApplication]:
    """Record vacancy/pool intent after conversion; see ``recruitment_application_service``."""
    src = (source or "").strip() or str(getattr(lead, "source", None) or "meta").strip() or "meta"
    return await ensure_recruitment_application_for_lead_intent(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        lead=lead,
        vacancy_id=vacancy_id,
        source=src,
        recruiter_id=recruiter_id,
    )


def _duplicate_result_label(level: str) -> str:
    """Map internal duplicate tier to lead-conversion-contract vocabulary."""
    m = (level or "none").strip().lower()
    if m == "none":
        return "no_duplicate"
    if m == "exact":
        return "exact_duplicate"
    if m == "probable":
        return "possible_duplicate"
    return m


def _assignment_state_value(candidate: Candidate) -> str:
    raw = getattr(candidate, "assignment_state", None)
    return str(raw) if raw is not None else ""


async def _emit_candidate_created_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    lead: Lead,
    source_channel: str,
    owner_company_id: Optional[str],
    duplicate_result: str,
    conversion_reason: str,
    idempotent_replay: bool,
) -> None:
    ext = getattr(lead, "external_id", None)
    payload: Dict[str, Any] = {
        "event_name": "candidate_created",
        "conversion_contract_version": CONVERSION_CONTRACT_VERSION,
        "source_lead_id": str(lead.id),
        "source_channel": source_channel,
        "owner_company_id": owner_company_id,
        "external_id": str(ext).strip() if ext not in (None, "") else None,
        "duplicate_result": duplicate_result,
        "assignment_state": _assignment_state_value(candidate),
        "creation_mode": "auto",
        "conversion_reason": conversion_reason,
        "actor_type": "system",
        "vacancy_id": str(candidate.vacancy_id) if getattr(candidate, "vacancy_id", None) else None,
        "recruiter_id": str(candidate.recruiter_id) if getattr(candidate, "recruiter_id", None) else None,
        "idempotent_replay": idempotent_replay,
    }
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type="candidate_created",
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate.id),
        actor_id=None,
        payload=payload,
    )


async def create_candidate_from_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    candidate_payload: Dict[str, Any],
    source_channel: str,
    duplicate_match_level: str,
    conversion_reason: str,
) -> Candidate:
    """Single path for creating a Candidate from lead processing / manual reroute.

    Does not alter assignment cascade logic after INSERT (callers keep
    ``record_candidate_reassignment`` as today).

    Idempotency (no extra migration): (1) if ``lead.candidate_id`` already points
    to a live tenant-scoped row, return it and emit audit with
    ``idempotent_replay=True`` instead of inserting again; (2) deduplication of
    lead rows for the same webhook is handled in ``process_normalized_lead`` via
    ``get_lead_by_external_id`` and DB partial unique index on
    ``(tenant_id, source, external_id)``.
    """
    duplicate_result = _duplicate_result_label(duplicate_match_level)

    linked_id = getattr(lead, "candidate_id", None)
    if linked_id:
        res = await db.execute(
            select(Candidate).where(
                Candidate.id == str(linked_id),
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            from backend.app.services.lead_context_carry import carry_lead_context_on_conversion

            await carry_lead_context_on_conversion(
                db,
                tenant_id=tenant_id,
                lead=lead,
                candidate=existing,
                actor_id=None,
            )
            oc = getattr(existing, "own_company_id", None) or getattr(lead, "own_company_id", None)
            await _emit_candidate_created_audit(
                db,
                tenant_id=tenant_id,
                candidate=existing,
                lead=lead,
                source_channel=source_channel,
                owner_company_id=str(oc) if oc else None,
                duplicate_result=duplicate_result,
                conversion_reason=conversion_reason,
                idempotent_replay=True,
            )
            return existing

    candidate = await create_candidate_full(
        db=db,
        tenant_id=tenant_id,
        payload=candidate_payload,
        actor_id=None,
        acl=None,
        source_lead=lead,
    )
    if not getattr(lead, "candidate_id", None):
        lead.candidate_id = str(candidate.id)
        await db.flush()
    oc = getattr(candidate, "own_company_id", None) or getattr(lead, "own_company_id", None)
    await _emit_candidate_created_audit(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
        lead=lead,
        source_channel=source_channel,
        owner_company_id=str(oc) if oc else None,
        duplicate_result=duplicate_result,
        conversion_reason=conversion_reason,
        idempotent_replay=False,
    )
    from backend.app.services.lead_communications import maybe_send_moving_forward_notice

    await maybe_send_moving_forward_notice(db, tenant_id=tenant_id, lead=lead)
    return candidate
