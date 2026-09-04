"""Automatic lead RODO (art.14) on ingest and before first gated action."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_lifecycle_email_policy import (
    PURPOSE_GDPR_NOTICE,
    is_platform_rodo_template_ref,
    resolve_lifecycle_email_policy_for_lead,
)
from backend.app.services.lead_rodo import (
    lead_rodo_sent_from_normalized,
    lead_rodo_satisfied,
    mark_lead_rodo_source_provided,
    resolve_lead_controller_identity,
    send_lead_rodo_email,
)
from backend.app.services.lead_rodo_obligation import (
    ComplianceTransitionError,
    evaluate_lead_rodo_obligation,
    notice_provided_at_source,
    stamp_obligation_evaluation,
)
from backend.app.services.lead_rodo_settings import DEFAULT_LEAD_RODO_CHANNELS

logger = logging.getLogger(__name__)


def normalized_rodo_notice_at_source(normalized: Optional[Dict[str, Any]]) -> bool:
    """Public form / intake already included the information notice — no extra outbound."""
    return notice_provided_at_source(normalized)


async def apply_lead_rodo_on_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str,
    normalized: Optional[Dict[str, Any]],
    is_new_lead: bool,
) -> None:
    """
    After a new ``Lead`` row is persisted: evaluate the information obligation
    (art.13 vs art.14) and fulfill it when delivery is required. Idempotent for
    webhook replay. Tenants cannot skip evaluation.

    ADR-031 PR-2: when Recruitment §2.4 holds and auto RODO would fire, ensure early
    Candidate shell + Application **before** send (Lead.candidate_id stays unset).
    """
    if not is_new_lead:
        return
    # Early compliance shell must not block Lead-stage art.14 (gates stay on Lead.rodo).
    if getattr(lead, "candidate_id", None) and lead_rodo_satisfied(lead):
        return

    norm = dict(normalized or {}) if isinstance(normalized, dict) else {}
    existing = lead.normalized if isinstance(lead.normalized, dict) else {}
    merged = {**norm, **({"rodo": existing["rodo"]} if isinstance(existing.get("rodo"), dict) else {})}
    evaluation = evaluate_lead_rodo_obligation(source=source, normalized=merged)
    controller_id, controller_name = await resolve_lead_controller_identity(db, lead)
    stamp_obligation_evaluation(
        lead,
        evaluation,
        controller_own_company_id=controller_id,
        controller_name=controller_name,
    )

    if evaluation.action == "no_delivery_source_provided":
        if evaluation.notice_at_source:
            try:
                mark_lead_rodo_source_provided(
                    lead,
                    actor_id=None,
                    note="notice provided at collection",
                    proof="notice_at_source",
                )
            except ComplianceTransitionError:
                logger.info(
                    "lead_rodo_source_provided_transition_rejected",
                    extra={"tenant_id": tenant_id, "lead_id": str(lead.id)},
                )
        stamp_obligation_evaluation(
            lead,
            evaluation,
            controller_own_company_id=controller_id,
            controller_name=controller_name,
        )
        await db.flush()
        return
    if evaluation.action == "review_required":
        await db.flush()
        return
    if evaluation.action in ("no_delivery_already_notified", "no_delivery_exempt"):
        await db.flush()
        return

    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=tenant_id, lead=lead, purpose=PURPOSE_GDPR_NOTICE
    )

    await _maybe_ensure_recruitment_result_before_outbound(
        db,
        tenant_id=tenant_id,
        lead=lead,
        source=source,
    )

    await _auto_send_once(
        db,
        tenant_id=tenant_id,
        lead=lead,
        decision=decision,
        trigger="obligation_evaluation",
        ingest_source=source,
    )


async def maybe_auto_send_before_gated_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> None:
    """Retry fulfillment before a gated action if delivery is still required."""
    if lead_rodo_satisfied(lead):
        return
    evaluation = evaluate_lead_rodo_obligation(
        source=str(getattr(lead, "source", "") or ""),
        normalized=lead.normalized if isinstance(lead.normalized, dict) else None,
    )
    controller_id, controller_name = await resolve_lead_controller_identity(db, lead)
    stamp_obligation_evaluation(
        lead,
        evaluation,
        controller_own_company_id=controller_id,
        controller_name=controller_name,
    )
    if evaluation.action != "delivery_required":
        if evaluation.action == "no_delivery_source_provided":
            if evaluation.notice_at_source:
                try:
                    mark_lead_rodo_source_provided(
                        lead,
                        actor_id=None,
                        note="notice provided at collection",
                        proof="notice_at_source",
                    )
                except ComplianceTransitionError:
                    logger.info(
                        "lead_rodo_source_provided_transition_rejected",
                        extra={"tenant_id": tenant_id, "lead_id": str(lead.id)},
                    )
            stamp_obligation_evaluation(
                lead,
                evaluation,
                controller_own_company_id=controller_id,
                controller_name=controller_name,
            )
        await db.flush()
        return
    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=tenant_id, lead=lead, purpose=PURPOSE_GDPR_NOTICE
    )
    await _maybe_ensure_recruitment_result_before_outbound(
        db,
        tenant_id=tenant_id,
        lead=lead,
        source=str(getattr(lead, "source", "") or "first_action"),
    )
    await _auto_send_once(
        db,
        tenant_id=tenant_id,
        lead=lead,
        decision=decision,
        trigger="first_action",
        ingest_source=str(getattr(lead, "source", "") or ""),
    )


async def _maybe_ensure_recruitment_result_before_outbound(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str,
) -> None:
    from backend.app.modules.recruitment.services.application_result_service import (
        ApplicationTransportConflictError,
    )
    from backend.app.modules.recruitment.services.compliance_outbound_ensure import (
        ComplianceOutboundEnsureError,
        maybe_ensure_compliance_outbound_for_recruitment_lead,
    )

    try:
        await maybe_ensure_compliance_outbound_for_recruitment_lead(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            source=str(source or "lead_rodo"),
        )
    except ApplicationTransportConflictError:
        # Sales-bound — leave to Sales Pipeline path (PR-1); no Recruitment Application.
        return
    except ComplianceOutboundEnsureError as exc:
        if str((exc.details or {}).get("reason") or "") == "duplicate_review":
            logger.info(
                "lead_rodo_compliance_ensure_skipped_duplicate_review",
                extra={"tenant_id": tenant_id, "lead_id": str(lead.id)},
            )
            return
        logger.info(
            "lead_rodo_compliance_ensure_skipped",
            extra={
                "tenant_id": tenant_id,
                "lead_id": str(lead.id),
                "reason": exc.message,
                "details": dict(exc.details or {}),
            },
        )


async def _auto_send_once(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    decision: Any,
    trigger: str,
    ingest_source: str,
) -> None:
    from backend.app.services.lead_lifecycle_email_policy import PolicyDecision

    assert isinstance(decision, PolicyDecision)
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    if lead_rodo_sent_from_normalized(norm) or lead_rodo_satisfied(lead):
        return

    template_ref = None if is_platform_rodo_template_ref(decision.template_ref) else decision.template_ref

    ok, msg = await send_lead_rodo_email(
        db,
        lead=lead,
        tenant_id=tenant_id,
        actor_id=None,
        channels=DEFAULT_LEAD_RODO_CHANNELS,
        template_id=None,
        message_template_id=template_ref,
        auto_trigger=trigger,
        ingest_source=ingest_source,
    )
    if not ok:
        logger.info(
            "lead_rodo_auto_send_skipped",
            extra={
                "tenant_id": tenant_id,
                "lead_id": str(lead.id),
                "trigger": trigger,
                "reason": msg,
            },
        )


__all__ = [
    "apply_lead_rodo_on_ingest",
    "maybe_auto_send_before_gated_action",
    "normalized_rodo_notice_at_source",
]
