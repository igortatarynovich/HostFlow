"""Outcome executor — entity creation gated by Decision Layer (P4/P5B)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.decision_layer import DecisionResult, IngestDisposition
from backend.app.models import Candidate, Company, Lead
from backend.app.models.additional_service import ServiceOrder
from backend.app.modules.leads import crud
from backend.app.modules.leads.duplicate_resolution import record_exact_duplicate_lead_intake
from backend.app.modules.leads.lead_candidate_conversion import create_candidate_from_lead_conversion
from backend.app.modules.leads.lead_client_conversion import create_client_from_lead_conversion
from backend.app.modules.leads.lead_service_order_conversion import create_service_order_from_lead_conversion
from backend.app.modules.leads.recruiter_validation import validate_tenant_recruiter_id
from backend.app.services.lead_lifecycle import apply_lead_terminal_cleanup
from backend.app.services.recruiter_assignment import record_candidate_reassignment


@dataclass(frozen=True)
class OutcomeExecutionResult:
    entity_type: str
    entity_id: str
    idempotent_replay: bool = False


async def apply_blocked_duplicate_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    decision: DecisionResult,
    resolved_company_id: Optional[str],
) -> str:
    """Attach lead to existing candidate — no new Candidate INSERT."""
    duplicate = decision.duplicate_match.candidate
    if duplicate is None:
        raise ValueError("blocked_duplicate requires duplicate candidate")
    await crud.update_lead(
        db,
        lead,
        status="duplicated",
        candidate_id=str(duplicate.id),
        vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
        normalized=normalized,
        error=None,
    )
    await record_exact_duplicate_lead_intake(
        db,
        tenant_id=tenant_id,
        lead=lead,
        candidate=duplicate,
        normalized=normalized,
        match_reasons=list(decision.duplicate_match.reasons),
    )
    from backend.app.services.lead_context_carry import carry_lead_context_on_conversion

    await carry_lead_context_on_conversion(
        db,
        tenant_id=tenant_id,
        lead=lead,
        candidate=duplicate,
        actor_id=None,
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
            actor_id=None,
            reason="lead_converted_to_candidate",
        )
        await db.commit()
    except Exception:
        await db.rollback()
    return str(duplicate.id)


async def execute_create_candidate_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source: str,
    candidate_payload: dict[str, Any],
    decision: DecisionResult,
    rule_recruiter_id: Optional[str] = None,
    vacancy_recruiter_id: Optional[str] = None,
    fallback_recruiter_id: Optional[str] = None,
) -> Candidate:
    """Single Candidate creation path from Decision Layer create_candidate disposition."""
    if decision.disposition != IngestDisposition.create_candidate.value:
        raise ValueError(f"execute_create_candidate_outcome requires create_candidate, got {decision.disposition}")
    if not decision.may_create_candidate:
        raise ValueError("Decision Layer blocked candidate creation")

    duplicate_level = decision.duplicate_match.level if decision.duplicate_match else "none"
    candidate = await create_candidate_from_lead_conversion(
        db,
        tenant_id=tenant_id,
        lead=lead,
        candidate_payload=candidate_payload,
        source_channel=str(source),
        duplicate_match_level=duplicate_level,
        conversion_reason="outcome_decision_create_candidate",
    )

    rule_rid = await validate_tenant_recruiter_id(db, tenant_id, rule_recruiter_id) if rule_recruiter_id else None
    if rule_rid:
        await record_candidate_reassignment(
            db,
            candidate,
            new_recruiter_id=rule_rid,
            reason="lead_rule",
            actor=None,
            actor_kind="system",
            note=f"lead_id={lead.id}",
        )
    elif not getattr(candidate, "recruiter_id", None) and vacancy_recruiter_id:
        await record_candidate_reassignment(
            db,
            candidate,
            new_recruiter_id=vacancy_recruiter_id,
            reason="lead_vacancy",
            actor=None,
            actor_kind="system",
            note=f"lead_id={lead.id};vacancy_id={candidate_payload.get('vacancy_id')}",
        )
    elif not getattr(candidate, "recruiter_id", None) and fallback_recruiter_id:
        await record_candidate_reassignment(
            db,
            candidate,
            new_recruiter_id=fallback_recruiter_id,
            reason="lead_fallback",
            actor=None,
            actor_kind="system",
            note=f"lead_id={lead.id}",
        )
    await db.flush()
    return candidate


async def execute_create_client_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source: str,
    decision: DecisionResult,
) -> tuple[Company, bool]:
    """Create Client company from Decision Layer create_client disposition."""
    if decision.disposition != IngestDisposition.create_client.value:
        raise ValueError(f"execute_create_client_outcome requires create_client, got {decision.disposition}")
    if not decision.may_create_client:
        raise ValueError("Decision Layer blocked client creation")
    return await create_client_from_lead_conversion(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source_channel=str(source),
        conversion_reason="outcome_decision_create_client",
    )


async def execute_create_service_order_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source: str,
    decision: DecisionResult,
) -> tuple[ServiceOrder, bool]:
    """Create ServiceOrder from Decision Layer create_service_order disposition."""
    if decision.disposition != IngestDisposition.create_service_order.value:
        raise ValueError(
            f"execute_create_service_order_outcome requires create_service_order, got {decision.disposition}"
        )
    if not decision.may_create_service_order:
        raise ValueError("Decision Layer blocked service order creation")
    return await create_service_order_from_lead_conversion(
        db,
        tenant_id=tenant_id,
        lead=lead,
        normalized=normalized,
        source_channel=str(source),
        conversion_reason="outcome_decision_create_service_order",
    )


async def execute_outcome_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: dict[str, Any],
    source: str,
    decision: DecisionResult,
    candidate_payload: Optional[dict[str, Any]] = None,
    rule_recruiter_id: Optional[str] = None,
    vacancy_recruiter_id: Optional[str] = None,
    fallback_recruiter_id: Optional[str] = None,
) -> Optional[OutcomeExecutionResult]:
    """Provider-agnostic outcome dispatcher — source channel is opaque metadata only."""
    disposition = decision.disposition

    if disposition == IngestDisposition.create_candidate.value:
        if candidate_payload is None:
            raise ValueError("candidate_payload required for create_candidate outcome")
        prior_candidate_id = getattr(lead, "candidate_id", None)
        candidate = await execute_create_candidate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized=normalized,
            source=source,
            candidate_payload=candidate_payload,
            decision=decision,
            rule_recruiter_id=rule_recruiter_id,
            vacancy_recruiter_id=vacancy_recruiter_id,
            fallback_recruiter_id=fallback_recruiter_id,
        )
        idempotent = prior_candidate_id is not None and str(prior_candidate_id) == str(candidate.id)
        return OutcomeExecutionResult(
            entity_type="candidate",
            entity_id=str(candidate.id),
            idempotent_replay=idempotent,
        )

    if disposition == IngestDisposition.create_client.value:
        client, idempotent = await execute_create_client_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized=normalized,
            source=source,
            decision=decision,
        )
        entity_id = str(client.id) if client is not None else str(getattr(lead, "client_account_id", "") or "")
        if not entity_id:
            raise ValueError("Client conversion produced no entity id")
        return OutcomeExecutionResult(
            entity_type="client",
            entity_id=entity_id,
            idempotent_replay=idempotent,
        )

    if disposition == IngestDisposition.create_service_order.value:
        order, idempotent = await execute_create_service_order_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized=normalized,
            source=source,
            decision=decision,
        )
        return OutcomeExecutionResult(
            entity_type="service_order",
            entity_id=str(order.id),
            idempotent_replay=idempotent,
        )

    return None
