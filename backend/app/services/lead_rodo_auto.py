"""Automatic lead RODO (art.14) on ingest and before first gated action."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_rodo import (
    lead_rodo_sent_from_normalized,
    lead_rodo_satisfied,
    mark_lead_rodo_source_provided,
    send_lead_rodo_email,
)
from backend.app.services.lead_rodo_settings import LeadRodoSettings, get_lead_rodo_settings

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
    After a new ``Lead`` row is persisted: stamp source-provided or run auto-send per tenant settings.
    Idempotent for webhook replay (existing lead / already sent).

    ADR-031 PR-2: when Recruitment §2.4 holds and auto RODO would fire, ensure early
    Candidate shell + Application **before** send (Lead.candidate_id stays unset).
    """
    if not is_new_lead:
        return
    # Early compliance shell must not block Lead-stage art.14 (gates stay on Lead.rodo).
    if getattr(lead, "candidate_id", None) and lead_rodo_satisfied(lead):
        return

    norm = dict(normalized or {}) if isinstance(normalized, dict) else {}
    if normalized_rodo_notice_at_source(norm):
        mark_lead_rodo_source_provided(lead, actor_id=None, note="rodo_notice_at_source on ingest")
        await db.flush()
        return

    cfg = await get_lead_rodo_settings(db, tenant_id)
    if not cfg.auto_on_lead_created():
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
        cfg=cfg,
        trigger="lead_created",
        ingest_source=source,
    )


async def maybe_auto_send_before_gated_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> None:
    """When mode is auto_on_first_action, attempt outbound RODO before blocking the action."""
    if lead_rodo_satisfied(lead):
        return
    cfg = await get_lead_rodo_settings(db, tenant_id)
    if not cfg.auto_on_first_action():
        return
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
        cfg=cfg,
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
    cfg: LeadRodoSettings,
    trigger: str,
    ingest_source: str,
) -> None:
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    if lead_rodo_sent_from_normalized(norm) or lead_rodo_satisfied(lead):
        return

    ok, msg = await send_lead_rodo_email(
        db,
        lead=lead,
        tenant_id=tenant_id,
        actor_id=None,
        channels=cfg.channels,
        template_id=cfg.template_id,
        message_template_id=cfg.message_template_id,
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
