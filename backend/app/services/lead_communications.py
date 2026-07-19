"""Operational candidate messaging on Lead (separate from RODO / art. 14)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.lead import Lead
from backend.app.services.audit import log_audit_event
from backend.app.services.lead_communication_settings import (
    LeadCommunicationSettings,
    get_lead_communication_settings,
)
from backend.app.services.message_hub import resolve_lead_email_message
from backend.app.intake_platform.constants import SUBMISSIONS_V1_KEY
from backend.app.services.tenant_email import send_email_for_tenant

logger = logging.getLogger(__name__)

COMMUNICATION_NORMALIZED_KEY = "lead_communication_v1"

EVENT_APPLICATION_RECEIVED = "application_received"
EVENT_LEAD_REJECTED = "lead_rejected"
EVENT_MOVING_FORWARD = "moving_forward"

_COMMUNICATION_EVENTS = frozenset(
    {EVENT_APPLICATION_RECEIVED, EVENT_LEAD_REJECTED, EVENT_MOVING_FORWARD}
)


def normalized_merging_lead_persisted_blocks(lead: Lead, normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve immutable/normalized blocks when pipeline rewrites normalized."""
    from backend.app.services.lead_rodo import normalized_merging_lead_rodo

    out = normalized_merging_lead_rodo(lead, normalized)
    existing = lead.normalized if isinstance(lead.normalized, dict) else {}
    comm = existing.get(COMMUNICATION_NORMALIZED_KEY)
    if isinstance(comm, dict):
        out[COMMUNICATION_NORMALIZED_KEY] = dict(comm)
    submissions = existing.get(SUBMISSIONS_V1_KEY)
    if isinstance(submissions, list):
        out[SUBMISSIONS_V1_KEY] = list(submissions)
    for key in ("intake_attribution_v1", "intake_submit_resolution_v1", "public_intake_draft_v1"):
        if key in existing and key not in out:
            out[key] = existing[key]
    return out


def lead_communication_block(normalized: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(normalized, dict):
        return {}
    raw = normalized.get(COMMUNICATION_NORMALIZED_KEY)
    return raw if isinstance(raw, dict) else {}


def communication_event_record(
    normalized: Optional[Dict[str, Any]],
    event_type: str,
) -> Dict[str, Any]:
    block = lead_communication_block(normalized)
    raw = block.get(event_type)
    return raw if isinstance(raw, dict) else {}


def communication_event_sent(normalized: Optional[Dict[str, Any]], event_type: str) -> bool:
    rec = communication_event_record(normalized, event_type)
    return str(rec.get("status") or "").strip().lower() == "sent"


def _lead_norm_for_communication(
    lead: Lead,
    pipeline_normalized: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    if isinstance(pipeline_normalized, dict):
        merged = dict(pipeline_normalized)
        merged.pop(COMMUNICATION_NORMALIZED_KEY, None)
        merged.pop("rodo", None)
        norm.update(merged)
    return norm


def _resolve_lead_email(
    lead: Lead,
    pipeline_normalized: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    norm = _lead_norm_for_communication(lead, pipeline_normalized)
    email = str(norm.get("email") or "").strip()
    return email or None


def _first_name(normalized: Dict[str, Any]) -> str:
    return (
        str(normalized.get("first_name") or normalized.get("full_name") or "Candidate").strip() or "Candidate"
    )


def _default_email_bodies(event_type: str, first_name: str) -> tuple[str, str]:
    if event_type == EVENT_APPLICATION_RECEIVED:
        subject = "We received your application | HostFlow"
        body = f"""Hello {first_name},

Thank you for your application. We have received your details and our recruitment team will review them.

Best regards,
HostFlow Team

---

Dzień dobry {first_name},

Dziękujemy za zgłoszenie. Otrzymaliśmy Twoje dane — nasz zespół rekrutacyjny je przeanalizuje.

Pozdrawiamy,
Zespół HostFlow"""
    elif event_type == EVENT_LEAD_REJECTED:
        subject = "Update on your application | HostFlow"
        body = f"""Hello {first_name},

Thank you for your interest. After reviewing your application we will not be proceeding with your candidacy at this time.

Best regards,
HostFlow Team

---

Dzień dobry {first_name},

Dziękujemy za zainteresowanie. Po weryfikacji zgłoszenia nie kontynuujemy rekrutacji w tym momencie.

Pozdrawiamy,
Zespół HostFlow"""
    else:
        subject = "Next steps in your application | HostFlow"
        body = f"""Hello {first_name},

We are moving forward with your application. Our team will contact you about the next steps, including any documents we may need.

Best regards,
HostFlow Team

---

Dzień dobry {first_name},

Przechodzimy do kolejnego etapu rekrutacji. Skontaktujemy się w sprawie dalszych kroków, w tym dokumentów, jeśli będą potrzebne.

Pozdrawiamy,
Zespół HostFlow"""
    return subject, body


def _email_bodies(event_type: str, first_name: str, cfg: LeadCommunicationSettings) -> tuple[str, str]:
    subject, body = _default_email_bodies(event_type, first_name)
    if event_type == EVENT_APPLICATION_RECEIVED:
        return cfg.application_received_subject or subject, cfg.application_received_body or body
    if event_type == EVENT_LEAD_REJECTED:
        return cfg.rejection_notice_subject or subject, cfg.rejection_notice_body or body
    return cfg.moving_forward_subject or subject, cfg.moving_forward_body or body


def _template_id_for_event(cfg: LeadCommunicationSettings, event_type: str) -> Optional[str]:
    if event_type == EVENT_APPLICATION_RECEIVED:
        return cfg.application_received_template_id
    if event_type == EVENT_LEAD_REJECTED:
        return cfg.rejection_notice_template_id
    if event_type == EVENT_MOVING_FORWARD:
        return cfg.moving_forward_template_id
    return None


def _audit_type_for_event(event_type: str, *, failed: bool) -> AuditEventType:
    if failed:
        return AuditEventType.lead_communication_failed
    if event_type == EVENT_APPLICATION_RECEIVED:
        return AuditEventType.lead_communication_application_received_sent
    if event_type == EVENT_LEAD_REJECTED:
        return AuditEventType.lead_communication_rejection_sent
    return AuditEventType.lead_communication_moving_forward_sent


def _stamp_event(
    lead: Lead,
    event_type: str,
    *,
    status: str,
    channel: Optional[str] = None,
    recipient: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = dict(lead_communication_block(norm))
    rec: Dict[str, Any] = {
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if channel:
        rec["channel"] = channel
    if recipient:
        rec["recipient"] = recipient
    if reason:
        rec["failure_reason"] = str(reason)[:2000]
    block[event_type] = rec
    norm[COMMUNICATION_NORMALIZED_KEY] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


def lead_communication_rail_summary(normalized: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    UI hint: aggregate last operational communication state.
    Returns ``{tone, labels}`` where tone is ``ok`` | ``warn`` | ``neutral``.
    """
    block = lead_communication_block(normalized)
    labels: list[str] = []
    has_failed = False
    has_skipped = False
    for ev in _COMMUNICATION_EVENTS:
        rec = block.get(ev)
        if not isinstance(rec, dict):
            continue
        st = str(rec.get("status") or "").strip().lower()
        if st == "sent":
            labels.append(f"{ev}:sent")
        elif st == "failed":
            has_failed = True
            labels.append(f"{ev}:failed")
        elif st in ("skipped", "pending_channel"):
            has_skipped = True
            labels.append(f"{ev}:{st}")
    if not labels:
        return {"tone": "neutral", "labels": []}
    tone = "warn" if has_failed else ("neutral" if has_skipped and not any(":sent" in x for x in labels) else "ok")
    return {"tone": tone, "labels": labels}


async def maybe_send_lead_communication(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    event_type: str,
    cfg: Optional[LeadCommunicationSettings] = None,
    pipeline_normalized: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None,
    communication_purpose: Optional[str] = None,
    template_metadata: Optional[Dict[str, Any]] = None,
    locale: Optional[str] = None,
) -> bool:
    """
    Send one operational email if tenant flags allow. Idempotent per ``event_type``.
    Returns True when sent, False otherwise (skipped/failed/already sent).

    C5: transport is unreachable without Communication Pipeline authorization
    (thread result link → context → policy → template metadata).
    """
    ev = str(event_type or "").strip()
    if ev not in _COMMUNICATION_EVENTS:
        return False

    cfg = cfg or await get_lead_communication_settings(db, tenant_id)
    if not cfg.enabled:
        return False
    if ev == EVENT_APPLICATION_RECEIVED and not cfg.send_application_received:
        return False
    if ev == EVENT_LEAD_REJECTED and not cfg.send_rejection_notice:
        return False
    if ev == EVENT_MOVING_FORWARD and not cfg.send_moving_forward_notice:
        return False

    norm = _lead_norm_for_communication(lead, pipeline_normalized)
    if communication_event_sent(norm, ev):
        return False

    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
        template_metadata_from_mapping,
    )

    thread = str(thread_id or "").strip()
    purpose = str(communication_purpose or "").strip()
    template = template_metadata_from_mapping(
        template_metadata if isinstance(template_metadata, dict) else None
    )
    if not thread or not purpose or template is None:
        _stamp_event(
            lead,
            ev,
            status="skipped",
            reason="communication_pipeline_required",
        )
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.lead_communication_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload={
                "event_type": ev,
                "reason": "communication_pipeline_required",
                "notice_status": "skipped",
            },
        )
        return False

    auth = await authorize_outbound_communication(
        db,
        CommunicationSendRequest(
            tenant_id=str(tenant_id),
            thread_id=thread,
            channel="email",
            communication_purpose=purpose,
            template=template,
            locale=str(locale).strip() if locale else None,
        ),
    )
    if not auth.allowed:
        reason = str(auth.reason_code or "communication_pipeline_denied")
        _stamp_event(lead, ev, status="skipped", reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.lead_communication_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload={
                "event_type": ev,
                "reason": reason,
                "notice_status": "skipped",
                "authorization": auth.to_dict(),
            },
        )
        return False

    email = _resolve_lead_email(lead, pipeline_normalized)
    if not email:
        _stamp_event(lead, ev, status="pending_channel", reason="no_email")
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.lead_communication_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload={"event_type": ev, "reason": "no_email", "notice_status": "pending_channel"},
        )
        return False

    first_name = _first_name(_lead_norm_for_communication(lead, pipeline_normalized))
    default_subject, default_body = _email_bodies(ev, first_name, cfg)
    resolved = await resolve_lead_email_message(
        db,
        tenant_id=tenant_id,
        template_id=_template_id_for_event(cfg, ev),
        fallback_subject=default_subject,
        fallback_body=default_body,
        first_name=first_name,
    )
    subject = resolved.subject
    body = resolved.body
    try:
        await send_email_for_tenant(
            db,
            tenant_id=tenant_id,
            to=email,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        reason = str(exc) if str(exc) else type(exc).__name__
        _stamp_event(lead, ev, status="failed", channel="email", recipient=email, reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.lead_communication_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload={"event_type": ev, "reason": reason, "notice_status": "failed"},
        )
        logger.info(
            "lead_communication_send_failed",
            extra={"tenant_id": tenant_id, "lead_id": str(lead.id), "event_type": ev, "reason": reason},
        )
        return False

    _stamp_event(lead, ev, status="sent", channel="email", recipient=email)
    await db.flush()
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=_audit_type_for_event(ev, failed=False),
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=None,
        payload={"event_type": ev, "channel": "email", "recipient": email},
    )
    return True


async def maybe_send_application_received_on_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    is_new_lead: bool,
    pipeline_normalized: Optional[Dict[str, Any]] = None,
) -> None:
    if getattr(lead, "candidate_id", None):
        return
    # Compatibility guard: in some replay/import paths a lead may already exist
    # but still miss the initial communication stamp. We allow one backfill run
    # when the event is absent, while preserving strict idempotency.
    if not is_new_lead and communication_event_record(lead.normalized, EVENT_APPLICATION_RECEIVED):
        return
    await maybe_send_lead_communication(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type=EVENT_APPLICATION_RECEIVED,
        pipeline_normalized=pipeline_normalized,
    )


async def maybe_send_lead_rejected_notice(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> None:
    await maybe_send_lead_communication(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type=EVENT_LEAD_REJECTED,
    )


async def maybe_send_moving_forward_notice(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> None:
    await maybe_send_lead_communication(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type=EVENT_MOVING_FORWARD,
    )


__all__ = [
    "COMMUNICATION_NORMALIZED_KEY",
    "EVENT_APPLICATION_RECEIVED",
    "EVENT_LEAD_REJECTED",
    "EVENT_MOVING_FORWARD",
    "communication_event_sent",
    "lead_communication_block",
    "lead_communication_rail_summary",
    "maybe_send_application_received_on_ingest",
    "maybe_send_lead_rejected_notice",
    "maybe_send_lead_communication",
    "maybe_send_moving_forward_notice",
    "normalized_merging_lead_persisted_blocks",
]
