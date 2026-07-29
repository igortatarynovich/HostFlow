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
    # C0.3: delivery/skip failures use communication.delivery.failed (not lead.communication.failed).
    if failed:
        return AuditEventType.communication_delivery_failed
    if event_type == EVENT_APPLICATION_RECEIVED:
        return AuditEventType.lead_communication_application_received_sent
    if event_type == EVENT_LEAD_REJECTED:
        return AuditEventType.lead_communication_rejection_sent
    return AuditEventType.lead_communication_moving_forward_sent


def _delivery_failure_payload(
    *,
    event_type: str,
    reason_code: str,
    notice_status: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Operator-safe failure facts (C0.3). Never emit bare failed without reason_code."""
    out: Dict[str, Any] = {
        "event_type": event_type,
        "reason_code": reason_code,
        "reason": reason_code,
        "notice_status": notice_status,
        "source": "lead_communications",
        "fact_source": "communication.delivery",
    }
    if extra:
        out.update(extra)
    return out


def _stamp_event(
    lead: Lead,
    event_type: str,
    *,
    status: str,
    channel: Optional[str] = None,
    recipient: Optional[str] = None,
    reason: Optional[str] = None,
    reason_code: Optional[str] = None,
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
    if reason_code:
        rec["failure_reason_code"] = str(reason_code).strip().lower()[:64]
        if reason_code.startswith("policy_"):
            rec["policy_blocked"] = True
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

    from backend.app.services.lead_lifecycle_email_policy import (
        OPS_EVENT_TO_PURPOSE,
        resolve_lifecycle_email_policy_for_lead,
    )

    purpose_key = OPS_EVENT_TO_PURPOSE.get(ev)
    if not purpose_key:
        return False
    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=tenant_id, lead=lead, purpose=purpose_key
    )
    if decision.block_code == "disabled" or not decision.enabled:
        return False
    if decision.block_code in ("policy_template_missing", "policy_misconfigured") or (
        decision.enabled and not decision.template_ref
    ):
        _stamp_event(
            lead,
            ev,
            status="failed",
            reason=decision.reason or "Lifecycle email policy blocked send.",
            reason_code=str(decision.block_code or "policy_template_missing"),
        )
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code=str(decision.block_code or "policy_template_missing"),
                notice_status="failed",
                extra={"detail": decision.reason, "policy": decision.to_dict()},
            ),
        )
        return False
    if not decision.send:
        return False

    # Keep cfg for optional subject/body overlays from tenant preset during migration.
    cfg = cfg or await get_lead_communication_settings(db, tenant_id)

    norm = _lead_norm_for_communication(lead, pipeline_normalized)
    if communication_event_sent(norm, ev):
        return False

    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
        template_metadata_from_mapping,
    )
    from backend.app.modules.recruitment.communication.compliance_pipeline import (
        RecruitmentCompliancePipelineError,
        ensure_recruitment_compliance_pipeline_binding,
        purpose_for_ops_event as recruitment_purpose_for_ops_event,
        resolve_lead_uses_recruitment_compliance_pipeline,
    )
    from backend.app.modules.recruitment.services.compliance_outbound_ensure import (
        ComplianceOutboundEnsureError,
        maybe_ensure_compliance_outbound_for_recruitment_lead,
    )
    from backend.app.modules.sales.communication.compliance_pipeline import (
        SalesCompliancePipelineError,
        ensure_sales_compliance_pipeline_binding,
        purpose_for_ops_event as sales_purpose_for_ops_event,
        resolve_lead_uses_sales_compliance_pipeline,
    )

    thread = str(thread_id or "").strip()
    purpose = str(communication_purpose or "").strip()
    template = template_metadata_from_mapping(
        template_metadata if isinstance(template_metadata, dict) else None
    )
    sales_inquiry_id: Optional[str] = None
    application_id: Optional[str] = None
    use_sales_pipeline = False
    use_recruitment_pipeline = False
    sales_bound = await resolve_lead_uses_sales_compliance_pipeline(
        db, tenant_id=str(tenant_id), lead=lead
    )
    recruitment_bound = (
        False
        if sales_bound
        else await resolve_lead_uses_recruitment_compliance_pipeline(
            db, tenant_id=str(tenant_id), lead=lead
        )
    )

    if (not thread or not purpose or template is None) and sales_bound:
        sales_purpose = sales_purpose_for_ops_event(ev)
        if sales_purpose is None:
            _stamp_event(
                lead,
                ev,
                status="skipped",
                reason="communication_pipeline_required",
            )
            await db.flush()
            return False
        try:
            binding = await ensure_sales_compliance_pipeline_binding(
                db,
                tenant_id=str(tenant_id),
                lead=lead,
                purpose=sales_purpose,
                locale=str(locale).strip() if locale else None,
                source="sales.lead_communications",
            )
        except SalesCompliancePipelineError as exc:
            reason = str((exc.details or {}).get("reason") or exc.message)
            _stamp_event(lead, ev, status="skipped", reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.communication_delivery_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=None,
                payload=_delivery_failure_payload(
                    event_type=ev,
                    reason_code="authentication_configuration",
                    notice_status="skipped",
                    extra={"detail": reason, "details": dict(exc.details or {})},
                ),
            )
            return False
        thread = binding.thread_id
        purpose = binding.communication_purpose
        template = binding.template
        sales_inquiry_id = binding.sales_inquiry_id
        use_sales_pipeline = True

    if (not thread or not purpose or template is None) and recruitment_bound:
        rec_purpose = recruitment_purpose_for_ops_event(ev)
        if rec_purpose is None:
            _stamp_event(
                lead,
                ev,
                status="skipped",
                reason="communication_pipeline_required",
            )
            await db.flush()
            return False
        try:
            await maybe_ensure_compliance_outbound_for_recruitment_lead(
                db,
                tenant_id=str(tenant_id),
                lead=lead,
                source="recruitment.lead_communications",
            )
            binding = await ensure_recruitment_compliance_pipeline_binding(
                db,
                tenant_id=str(tenant_id),
                lead=lead,
                purpose=rec_purpose,
                locale=str(locale).strip() if locale else None,
                source="recruitment.lead_communications",
            )
        except ComplianceOutboundEnsureError as exc:
            reason = str((exc.details or {}).get("reason") or exc.message)
            _stamp_event(lead, ev, status="skipped", reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.communication_delivery_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=None,
                payload=_delivery_failure_payload(
                    event_type=ev,
                    reason_code="authentication_configuration",
                    notice_status="skipped",
                    extra={"detail": reason, "details": dict(exc.details or {})},
                ),
            )
            return False
        except RecruitmentCompliancePipelineError as exc:
            reason = str((exc.details or {}).get("reason") or exc.message)
            _stamp_event(lead, ev, status="skipped", reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.communication_delivery_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=None,
                payload=_delivery_failure_payload(
                    event_type=ev,
                    reason_code="authentication_configuration",
                    notice_status="skipped",
                    extra={"detail": reason, "details": dict(exc.details or {})},
                ),
            )
            return False
        thread = binding.thread_id
        purpose = binding.communication_purpose
        template = binding.template
        application_id = binding.application_id
        use_recruitment_pipeline = True

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
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code="authentication_configuration",
                notice_status="skipped",
                extra={"detail": "communication_pipeline_required"},
            ),
        )
        return False

    if sales_bound:
        use_sales_pipeline = True
    elif recruitment_bound:
        use_recruitment_pipeline = True

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
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code="consent_policy_denial"
                if "consent" in reason or "policy" in reason
                else "authentication_configuration",
                notice_status="skipped",
                extra={"detail": reason, "authorization": auth.to_dict()},
            ),
        )
        return False

    email = _resolve_lead_email(lead, pipeline_normalized)
    if not email:
        _stamp_event(lead, ev, status="pending_channel", reason="no_email")
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code="invalid_recipient",
                notice_status="pending_channel",
                extra={"detail": "no_email"},
            ),
        )
        return False

    first_name = _first_name(_lead_norm_for_communication(lead, pipeline_normalized))
    default_subject, default_body = _email_bodies(ev, first_name, cfg)
    resolved = await resolve_lead_email_message(
        db,
        tenant_id=tenant_id,
        template_id=decision.template_ref,
        fallback_subject=default_subject,
        fallback_body=default_body,
        first_name=first_name,
    )
    # ADR-033: enabled purpose must not silently send HostFlow marketing copy.
    if not resolved.template_id:
        _stamp_event(
            lead,
            ev,
            status="failed",
            reason="Lifecycle email template_ref could not be resolved.",
            reason_code="policy_misconfigured",
        )
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code="policy_misconfigured",
                notice_status="failed",
                extra={"template_ref": decision.template_ref},
            ),
        )
        return False
    subject = resolved.subject
    body = resolved.body

    if use_sales_pipeline:
        send_coro = _send_ops_via_sales_pipeline(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            event_type=ev,
            email=email,
            first_name=first_name,
            subject=subject,
            body=body,
            thread_id=thread,
            purpose=purpose,
            template_id=getattr(template, "template_id", None),
            locale=str(locale).strip() if locale else None,
            sales_inquiry_id=sales_inquiry_id,
            policy_decision=auth.to_dict(),
        )
    elif use_recruitment_pipeline:
        send_coro = _send_ops_via_recruitment_pipeline(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            event_type=ev,
            email=email,
            first_name=first_name,
            subject=subject,
            body=body,
            thread_id=thread,
            purpose=purpose,
            template_id=getattr(template, "template_id", None),
            locale=str(locale).strip() if locale else None,
            application_id=application_id,
            policy_decision=auth.to_dict(),
        )
    else:
        send_coro = None

    if send_coro is not None:
        try:
            await send_coro
        except Exception as exc:
            from backend.app.communications.send_communication import SendCommunicationError

            if isinstance(exc, SendCommunicationError):
                reason = (
                    exc.message
                    or str((exc.details or {}).get("reason") or "")
                    or "send_failed"
                )
            else:
                reason = str(exc) if str(exc) else type(exc).__name__
            _stamp_event(lead, ev, status="failed", channel="email", recipient=email, reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.communication_delivery_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=None,
                payload=_delivery_failure_payload(
                    event_type=ev,
                    reason_code="send_failed",
                    notice_status="failed",
                    extra={"detail": reason[:500]},
                ),
            )
            logger.info(
                "lead_communication_send_failed",
                extra={
                    "tenant_id": tenant_id,
                    "lead_id": str(lead.id),
                    "event_type": ev,
                    "reason": reason,
                },
            )
            return False
    else:
        # ADR-031 PR-5: no Lead SMTP fallback when destination unbound / unselected.
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
            event_type=AuditEventType.communication_delivery_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=None,
            payload=_delivery_failure_payload(
                event_type=ev,
                reason_code="authentication_configuration",
                notice_status="skipped",
                extra={"detail": "communication_pipeline_required"},
            ),
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
        payload={
            "event_type": ev,
            "channel": "email",
            "recipient": email,
            "delivery": "communication_pipeline",
            **({"sales_inquiry_id": sales_inquiry_id} if sales_inquiry_id else {}),
            **({"application_id": application_id} if application_id else {}),
        },
    )
    return True


async def _send_ops_via_sales_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    event_type: str,
    email: str,
    first_name: str,
    subject: str,
    body: str,
    thread_id: str,
    purpose: str,
    template_id: Optional[str],
    locale: Optional[str],
    sales_inquiry_id: Optional[str],
    policy_decision: Dict[str, Any],
) -> None:
    """ADR-031 Sales ops path: Intent follow_up → prepare_and_send (no direct SMTP)."""
    from sqlalchemy import select

    from backend.app.communications.command import (
        CommunicationCommand,
        CommunicationOrigin,
        CommunicationRecipient,
        SendCommunicationContent,
    )
    from backend.app.communications.intent import CommunicationIntent
    from backend.app.communications.prepare_send import prepare_and_send_communication
    from backend.app.models.sales_inquiry import SalesInquiry

    si_id = str(sales_inquiry_id or "").strip()
    if not si_id:
        link = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw_link = link.get("intake_result_link_v1") if isinstance(link, dict) else None
        if isinstance(raw_link, dict):
            si_id = str(raw_link.get("sales_inquiry_id") or "").strip()
    if not si_id:
        row = await db.scalar(
            select(SalesInquiry)
            .where(SalesInquiry.tenant_id == tenant_id, SalesInquiry.lead_id == str(lead.id))
            .limit(1)
        )
        if row is not None:
            si_id = str(row.id)
    if not si_id:
        raise RuntimeError("sales_inquiry_id required for Sales pipeline ops send")

    command = CommunicationCommand(
        tenant_id=tenant_id,
        origin=CommunicationOrigin(entity_type="sales_inquiry", entity_id=si_id),
        recipients=[
            CommunicationRecipient(
                address=email,
                label=first_name,
                recipient_type="lead",
                recipient_id=str(lead.id),
            )
        ],
        channel="email",
        intent=CommunicationIntent.FOLLOW_UP,
        content=SendCommunicationContent(
            subject=subject,
            body_text=body,
            message_type="email",
        ),
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=[
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
        ],
        thread_id=thread_id,
        purpose=purpose,
        delivery_purpose=purpose,
        template_key=str(template_id or "").strip() or None,
        locale=locale,
        policy_decision=policy_decision,
        idempotency_key=f"lead_ops:{lead.id}:{event_type}"[:128],
        meta={
            "source": "lead_communications.sales_pipeline",
            "lead_id": str(lead.id),
            "event_type": event_type,
        },
    )
    await prepare_and_send_communication(db, command)


async def _send_ops_via_recruitment_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    event_type: str,
    email: str,
    first_name: str,
    subject: str,
    body: str,
    thread_id: str,
    purpose: str,
    template_id: Optional[str],
    locale: Optional[str],
    application_id: Optional[str],
    policy_decision: Dict[str, Any],
) -> None:
    """ADR-031 Recruitment ops path: Intent follow_up → prepare_and_send (no direct SMTP)."""
    from sqlalchemy import select

    from backend.app.communications.command import (
        CommunicationCommand,
        CommunicationOrigin,
        CommunicationRecipient,
        SendCommunicationContent,
    )
    from backend.app.communications.intent import CommunicationIntent
    from backend.app.communications.prepare_send import prepare_and_send_communication
    from backend.app.models.recruitment_application import RecruitmentApplication

    app_id = str(application_id or "").strip()
    if not app_id:
        link = lead.normalized if isinstance(lead.normalized, dict) else {}
        raw_link = link.get("intake_result_link_v1") if isinstance(link, dict) else None
        if isinstance(raw_link, dict):
            app_id = str(raw_link.get("application_id") or "").strip()
    if not app_id:
        row = await db.scalar(
            select(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.lead_id == str(lead.id),
            )
            .limit(1)
        )
        if row is not None:
            app_id = str(row.id)
    if not app_id:
        raise RuntimeError("application_id required for Recruitment pipeline ops send")

    command = CommunicationCommand(
        tenant_id=tenant_id,
        origin=CommunicationOrigin(entity_type="application", entity_id=app_id),
        recipients=[
            CommunicationRecipient(
                address=email,
                label=first_name,
                recipient_type="lead",
                recipient_id=str(lead.id),
            )
        ],
        channel="email",
        intent=CommunicationIntent.FOLLOW_UP,
        content=SendCommunicationContent(
            subject=subject,
            body_text=body,
            message_type="email",
        ),
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=[
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
        ],
        thread_id=thread_id,
        purpose=purpose,
        delivery_purpose=purpose,
        template_key=str(template_id or "").strip() or None,
        locale=locale,
        policy_decision=policy_decision,
        idempotency_key=f"lead_ops:{lead.id}:{event_type}"[:128],
        meta={
            "source": "lead_communications.recruitment_pipeline",
            "lead_id": str(lead.id),
            "event_type": event_type,
            "application_id": app_id,
        },
    )
    await prepare_and_send_communication(db, command)


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
