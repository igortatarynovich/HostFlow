"""Automatic lead RODO (art.14) on ingest and before first gated action."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_lifecycle_email_policy import (
    PURPOSE_GDPR_NOTICE,
    resolve_lifecycle_email_policy_for_lead,
)
from backend.app.services.lead_rodo import (
    LEAD_RODO_REASON_POLICY_MISCONFIGURED,
    LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING,
    lead_rodo_sent_from_normalized,
    lead_rodo_satisfied,
    mark_lead_rodo_pending_policy,
    mark_lead_rodo_source_provided,
    send_lead_rodo_email,
)
from backend.app.services.lead_rodo_settings import DEFAULT_LEAD_RODO_CHANNELS

logger = logging.getLogger(__name__)

# MVP: auto-on-created applies to these ingest sources (Meta, generic webhook, import, Telegram).
_AUTO_ON_CREATED_SOURCES = frozenset(
    {
        "meta",
        "csv_import",
        "webhook",
        "import",
        "telegram_bot",
        "telegram_intake_completion",
        "lead_form",
        "public_form",
        "public-intake",
    }
)


def normalized_rodo_notice_at_source(normalized: Optional[Dict[str, Any]]) -> bool:
    """Public form / intake already included art.14 — do not send duplicate outbound notice."""
    if not isinstance(normalized, dict):
        return False
    flag = normalized.get("rodo_notice_at_source")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.strip().lower() in ("true", "1", "yes", "on"):
        return True
    nested = normalized.get("consents")
    if isinstance(nested, dict):
        rodo = nested.get("rodo") or nested.get("gdpr")
        if rodo is True:
            return True
        if isinstance(rodo, str) and rodo.strip().lower() in ("true", "1", "yes", "accepted"):
            return True
    return False


def _source_eligible_for_auto_on_created(source: str) -> bool:
    s = str(source or "").strip().lower()
    if not s:
        return False
    if s in _AUTO_ON_CREATED_SOURCES:
        return True
    return s.startswith("telegram")


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
    After a Lead row is persisted: stamp source-provided or run auto-send per policy.
    Idempotent for webhook replay (already sent / satisfied). Replays of an
    unsatisfied lead still attempt auto-send when firm mode is ``auto_on_lead_created``.

    ADR-031 PR-2: when Recruitment §2.4 holds and auto RODO would fire, ensure early
    Candidate shell + Application **before** send (Lead.candidate_id stays unset).
    """
    del is_new_lead  # retries are keyed off unsatisfied + send_mode, not insert vs update
    # Early compliance shell must not block Lead-stage art.14 (gates stay on Lead.rodo).
    if lead_rodo_satisfied(lead):
        return

    norm = dict(normalized or {}) if isinstance(normalized, dict) else {}
    if normalized_rodo_notice_at_source(norm):
        mark_lead_rodo_source_provided(lead, actor_id=None, note="rodo_notice_at_source on ingest")
        await db.flush()
        return

    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=tenant_id, lead=lead, purpose=PURPOSE_GDPR_NOTICE
    )
    if decision.send_mode != "auto_on_lead_created":
        return
    if not _source_eligible_for_auto_on_created(source):
        return

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
        trigger="lead_created",
        ingest_source=source,
    )


async def maybe_auto_send_before_gated_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> None:
    """Attempt outbound RODO before a gated action when firm mode is auto.

    Covers ``auto_on_first_action`` and heals missed ``auto_on_lead_created``
    (ingest skipped, routing incomplete, overlay drift, webhook replay).
    """
    if lead_rodo_satisfied(lead):
        return
    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=tenant_id, lead=lead, purpose=PURPOSE_GDPR_NOTICE
    )
    if decision.send_mode not in ("auto_on_lead_created", "auto_on_first_action"):
        return
    await _maybe_ensure_recruitment_result_before_outbound(
        db,
        tenant_id=tenant_id,
        lead=lead,
        source=str(getattr(lead, "source", "") or "first_action"),
    )
    trigger = (
        "lead_created"
        if decision.send_mode == "auto_on_lead_created"
        else "first_action"
    )
    await _auto_send_once(
        db,
        tenant_id=tenant_id,
        lead=lead,
        decision=decision,
        trigger=trigger,
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

    if decision.block_code == "disabled":
        return

    if decision.block_code in (
        LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING,
        LEAD_RODO_REASON_POLICY_MISCONFIGURED,
        "policy_template_missing",
        "policy_misconfigured",
    ):
        mark_lead_rodo_pending_policy(
            lead,
            reason=decision.reason or "RODO lifecycle email policy blocked send.",
            reason_code=str(decision.block_code or LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING),
        )
        await db.flush()
        return

    if not decision.send or not decision.template_ref:
        if decision.send_mode in ("auto_on_lead_created", "auto_on_first_action") and not decision.template_ref:
            mark_lead_rodo_pending_policy(
                lead,
                reason=decision.reason or "RODO auto-send enabled but template_ref is missing.",
                reason_code=LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING,
            )
            await db.flush()
        return

    ok, msg = await send_lead_rodo_email(
        db,
        lead=lead,
        tenant_id=tenant_id,
        actor_id=None,
        channels=DEFAULT_LEAD_RODO_CHANNELS,
        template_id=None,
        message_template_id=decision.template_ref,
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
