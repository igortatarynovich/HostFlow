"""RODO / art.14 on Lead (primary); candidate receives audit copy on conversion only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.core.config import settings
from backend.app.models.lead import Lead
from backend.app.services.audit import log_audit_event
from backend.app.services.legal_documents import get_active_legal_document
from backend.app.services.message_hub import resolve_lead_email_message


def normalized_merging_lead_rodo(lead: Lead, normalized: Dict[str, Any]) -> Dict[str, Any]:
    """Keep ``normalized['rodo']`` when pipeline code replaces the rest of ``lead.normalized``."""
    out = dict(normalized or {})
    existing = lead.normalized if isinstance(lead.normalized, dict) else {}
    rodo = existing.get("rodo")
    if isinstance(rodo, dict) and rodo:
        out["rodo"] = dict(rodo)
    return out


def lead_normalized_rodo_block(normalized: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(normalized, dict):
        return {}
    raw = normalized.get("rodo")
    return raw if isinstance(raw, dict) else {}


def lead_rodo_satisfied_from_normalized(normalized: Optional[Dict[str, Any]]) -> bool:
    """Art.14 satisfied at lead when notice was emailed, explicitly waived as satisfied, or marked source-provided."""
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else {})
    st = str(block.get("status") or "").strip().lower()
    if st in ("sent", "satisfied", "source_provided"):
        return True
    return bool(str(block.get("sent_at") or "").strip())


def lead_rodo_notice_status_from_normalized(normalized: Optional[Dict[str, Any]]) -> str:
    """
    UI / API contract: ``sent`` | ``failed`` | ``pending_channel`` | ``manual_required`` | ``source_provided``.
    """
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else {})
    st = str(block.get("status") or "").strip().lower()
    if st == "source_provided":
        return "source_provided"
    if st in ("sent", "satisfied") or block.get("sent_at"):
        return "sent"
    if st == "failed":
        return "failed"
    if st == "pending_channel":
        return "pending_channel"
    return "manual_required"


def mark_lead_rodo_pending_channel(lead: Lead, *, reason: str = "no_channel") -> None:
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    block["status"] = "pending_channel"
    block["pending_reason"] = str(reason or "no_channel").strip()[:256]
    norm["rodo"] = block
    lead.normalized = norm


def mark_lead_rodo_failed(lead: Lead, *, reason: str) -> None:
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    block["status"] = "failed"
    block["failure_reason"] = str(reason or "").strip()[:2000]
    norm["rodo"] = block
    lead.normalized = norm


def lead_rodo_satisfied(lead: Lead) -> bool:
    return lead_rodo_satisfied_from_normalized(lead.normalized if isinstance(lead.normalized, dict) else None)


LEAD_RODO_ACTION_PROCESS = "process"
LEAD_RODO_ACTION_REQUEST_INFO = "request_info"
LEAD_RODO_ACTION_CONTACTED_STAGE = "contacted_stage"
LEAD_RODO_ACTION_COMMUNICATION_CALL = "communication_call"
LEAD_RODO_ACTION_COMMUNICATION_EMAIL = "communication_email"
LEAD_RODO_ACTION_COMMUNICATION_WHATSAPP = "communication_whatsapp"
LEAD_RODO_ACTION_REQUEST_DOCUMENTS = "request_documents"

_LEAD_RODO_GATED_ACTIONS: frozenset[str] = frozenset(
    {
        LEAD_RODO_ACTION_PROCESS,
        LEAD_RODO_ACTION_REQUEST_INFO,
        LEAD_RODO_ACTION_CONTACTED_STAGE,
        LEAD_RODO_ACTION_COMMUNICATION_CALL,
        LEAD_RODO_ACTION_COMMUNICATION_EMAIL,
        LEAD_RODO_ACTION_COMMUNICATION_WHATSAPP,
        LEAD_RODO_ACTION_REQUEST_DOCUMENTS,
    }
)


async def ensure_lead_rodo_allows_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    action: str,
) -> Optional[str]:
    """
    Return ``LEAD_RODO_REQUIRED`` when the action is blocked, else ``None``.
    May trigger auto-on-first-action send when configured.
    """
    code = lead_rodo_required_block_code(lead, action)
    if code is None:
        return None
    from backend.app.services.lead_rodo_auto import maybe_auto_send_before_gated_action

    await maybe_auto_send_before_gated_action(db, tenant_id=tenant_id, lead=lead)
    if lead_rodo_satisfied(lead):
        return None
    return "LEAD_RODO_REQUIRED"


def lead_rodo_required_block_code(lead: Lead, action: str) -> Optional[str]:
    """
    Return ``LEAD_RODO_REQUIRED`` when the action must be blocked until lead RODO is satisfied, else ``None``.

    Converted leads (``candidate_id`` set) are not gated here — candidate-level RODO applies instead.

    ``LEAD_RODO_ACTION_COMMUNICATION_*`` and ``LEAD_RODO_ACTION_REQUEST_DOCUMENTS`` are reserved for
    lead-scoped outbound APIs (e.g. contact attempts); call this helper at those boundaries.
    """
    if getattr(lead, "candidate_id", None):
        return None
    act = str(action or "").strip().lower()
    if act not in _LEAD_RODO_GATED_ACTIONS:
        return None
    if lead_rodo_satisfied(lead):
        return None
    return "LEAD_RODO_REQUIRED"


def lead_rodo_sent_from_normalized(normalized: Optional[Dict[str, Any]]) -> bool:
    """True when outbound art.14 email was already sent (blocks duplicate send; ``source_provided`` alone does not)."""
    block = lead_normalized_rodo_block(normalized)
    st = str(block.get("status") or "").strip().lower()
    if st in ("sent", "satisfied"):
        return True
    return bool(str(block.get("sent_at") or "").strip())


def _rodo_email_body(first_name: str, link: str) -> str:
    return f"""Dear {first_name},

Please find below the information on the processing of your personal data (GDPR/RODO):

{link}

Best regards,
HostFlow Team

---

Dzień dobry {first_name},

W załączeniu przekazujemy informację dotyczącą przetwarzania Twoich danych osobowych (RODO):

{link}

Pozdrawiamy,
Zespół HostFlow

---

Здравствуйте, {first_name},

Направляем информацию об обработке ваших персональных данных (GDPR/RODO):

{link}

С уважением,
Команда HostFlow"""


def _resolve_lead_email_for_channel(
    normalized: Dict[str, Any],
    channels: tuple[str, ...],
) -> tuple[Optional[str], Optional[str]]:
    """Return (email, channel_name) for the first configured channel we can use."""
    for ch in channels:
        if ch == "email":
            email = str(normalized.get("email") or "").strip()
            if email:
                return email, "email"
    return None, None


async def send_lead_rodo_email(
    db: AsyncSession,
    *,
    lead: Lead,
    tenant_id: str,
    actor_id: Optional[str] = None,
    channels: tuple[str, ...] = ("email",),
    template_id: Optional[str] = None,
    message_template_id: Optional[str] = None,
    auto_trigger: Optional[str] = None,
    ingest_source: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Send RODO notice to the lead contact email; persist audit under ``lead.normalized['rodo']``.
    Does not create ``RodoNotification`` (candidate row may not exist yet).
    """
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    email, channel = _resolve_lead_email_for_channel(norm, channels)
    if not email or not channel:
        mark_lead_rodo_pending_channel(lead, reason="no_channel")
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "reason": "Lead has no channel for RODO",
                "notice_status": "pending_channel",
                "auto_trigger": auto_trigger,
                "ingest_source": ingest_source,
            },
        )
        return False, "No email or channel for RODO"

    if lead_rodo_sent_from_normalized(norm):
        return False, "RODO already sent for this lead"

    # ADR-031 PR-2: Recruitment opaque result before outbound (SMTP still until PR-3).
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
            source=str(ingest_source or auto_trigger or "lead_rodo_manual"),
        )
    except ApplicationTransportConflictError:
        pass  # Sales-bound — not Recruitment ensure
    except ComplianceOutboundEnsureError as exc:
        if str((exc.details or {}).get("reason") or "") == "duplicate_review":
            return False, "RODO blocked: lead is in duplicate_review"
        # Missing funnel / shell create failure: continue; Pipeline bind fail-closes.

    rodo_doc = await get_active_legal_document(db, tenant_id, "rodo_clause")
    if template_id and str(template_id).strip():
        from sqlalchemy import select

        from backend.app.models.legal_document import LegalDocument

        override = (
            await db.execute(
                select(LegalDocument).where(
                    LegalDocument.tenant_id == tenant_id,
                    LegalDocument.type == "rodo_clause",
                    LegalDocument.version_id == str(template_id).strip(),
                    LegalDocument.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if override is not None:
            rodo_doc = override
    if not rodo_doc:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={"reason": "No active RODO document configured"},
        )
        return False, "No active RODO document configured"

    link = (rodo_doc.content_url or "").strip()
    if not link:
        base = (settings.frontend_url or "").strip().rstrip("/")
        link = f"{base}/legal/rodo.html" if base else "/legal/rodo.html"

    first_name = (str(norm.get("first_name") or norm.get("full_name") or "Lead")).strip() or "Lead"
    body = _rodo_email_body(first_name, link)
    resolved = await resolve_lead_email_message(
        db,
        tenant_id=tenant_id,
        template_id=message_template_id,
        fallback_subject="RODO / GDPR — Personal data processing information | HostFlow",
        fallback_body=body,
        first_name=first_name,
        rodo_link=link,
    )
    subject = resolved.subject
    body = resolved.body

    from backend.app.modules.sales.communication.compliance_pipeline import (
        SalesCompliancePipelineError,
        resolve_lead_uses_sales_compliance_pipeline,
    )
    from backend.app.modules.recruitment.communication.compliance_pipeline import (
        RecruitmentCompliancePipelineError,
        resolve_lead_uses_recruitment_compliance_pipeline,
    )

    if await resolve_lead_uses_sales_compliance_pipeline(
        db, tenant_id=str(tenant_id), lead=lead
    ):
        try:
            ok, msg = await _send_lead_rodo_via_sales_pipeline(
                db,
                tenant_id=tenant_id,
                lead=lead,
                actor_id=actor_id,
                email=email,
                channel=channel,
                subject=subject,
                body=body,
                rodo_link=link,
                rodo_version_id=str(rodo_doc.version_id),
                auto_trigger=auto_trigger,
                ingest_source=ingest_source,
                first_name=first_name,
            )
            return ok, msg
        except SalesCompliancePipelineError as exc:
            reason = exc.message
            mark_lead_rodo_failed(lead, reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.rodo_sent_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=actor_id,
                payload={
                    "reason": f"Sales pipeline bind failed: {reason}",
                    "notice_status": "failed",
                    "auto_trigger": auto_trigger,
                    "ingest_source": ingest_source,
                    "details": dict(exc.details or {}),
                },
            )
            return False, f"Failed to send email: {reason}"

    if await resolve_lead_uses_recruitment_compliance_pipeline(
        db, tenant_id=str(tenant_id), lead=lead
    ):
        try:
            ok, msg = await _send_lead_rodo_via_recruitment_pipeline(
                db,
                tenant_id=tenant_id,
                lead=lead,
                actor_id=actor_id,
                email=email,
                channel=channel,
                subject=subject,
                body=body,
                rodo_link=link,
                rodo_version_id=str(rodo_doc.version_id),
                auto_trigger=auto_trigger,
                ingest_source=ingest_source,
                first_name=first_name,
            )
            return ok, msg
        except RecruitmentCompliancePipelineError as exc:
            reason = exc.message
            mark_lead_rodo_failed(lead, reason=reason)
            await db.flush()
            await log_audit_event(
                db,
                tenant_id=tenant_id,
                event_type=AuditEventType.rodo_sent_failed,
                entity_type=AuditEntityType.lead,
                entity_id=str(lead.id),
                actor_id=actor_id,
                payload={
                    "reason": f"Recruitment pipeline bind failed: {reason}",
                    "notice_status": "failed",
                    "auto_trigger": auto_trigger,
                    "ingest_source": ingest_source,
                    "details": dict(exc.details or {}),
                },
            )
            return False, f"Failed to send email: {reason}"

    # ADR-031 PR-5: no Lead SMTP fallback — destination must resolve to Pipeline.
    reason = "communication_pipeline_required"
    mark_lead_rodo_failed(lead, reason=reason)
    await db.flush()
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.rodo_sent_failed,
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=actor_id,
        payload={
            "reason": f"Email send failed: {reason}",
            "notice_status": "failed",
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
        },
    )
    return False, f"Failed to send email: {reason}"


async def _send_lead_rodo_via_sales_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    actor_id: Optional[str],
    email: str,
    channel: str,
    subject: str,
    body: str,
    rodo_link: str,
    rodo_version_id: str,
    auto_trigger: Optional[str],
    ingest_source: Optional[str],
    first_name: str,
) -> Tuple[bool, str]:
    """ADR-031 Sales path: binder → authorize → prepare_and_send (no direct SMTP)."""
    from backend.app.communications.command import (
        CommunicationCommand,
        CommunicationOrigin,
        CommunicationRecipient,
        ResolvedLinkSnapshot,
        SendCommunicationContent,
    )
    from backend.app.communications.intent import CommunicationIntent
    from backend.app.communications.prepare_send import prepare_and_send_communication
    from backend.app.communications.send_communication import SendCommunicationError
    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
    )
    from backend.app.modules.sales.communication.compliance_pipeline import (
        PURPOSE_GDPR_NOTICE,
        ensure_sales_compliance_pipeline_binding,
    )

    binding = await ensure_sales_compliance_pipeline_binding(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        purpose=PURPOSE_GDPR_NOTICE,
        actor_user_id=actor_id,
        source="sales.lead_rodo",
    )
    auth = await authorize_outbound_communication(
        db,
        CommunicationSendRequest(
            tenant_id=str(tenant_id),
            thread_id=binding.thread_id,
            channel="email",
            communication_purpose=binding.communication_purpose,
            template=binding.template,
            locale=binding.locale,
        ),
    )
    if not auth.allowed:
        reason = str(auth.reason_code or "communication_pipeline_denied")
        mark_lead_rodo_failed(lead, reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "reason": f"Pipeline denied: {reason}",
                "notice_status": "failed",
                "auto_trigger": auto_trigger,
                "ingest_source": ingest_source,
                "authorization": auth.to_dict(),
            },
        )
        return False, f"Failed to send email: {reason}"

    command = CommunicationCommand(
        tenant_id=str(tenant_id),
        origin=CommunicationOrigin(
            entity_type="sales_inquiry",
            entity_id=binding.sales_inquiry_id,
        ),
        recipients=[
            CommunicationRecipient(
                address=email,
                label=first_name,
                recipient_type="lead",
                recipient_id=str(lead.id),
            )
        ],
        channel="email",
        intent=CommunicationIntent.GDPR_NOTICE,
        content=SendCommunicationContent(
            subject=subject,
            body_text=body,
            message_type="email",
        ),
        actor_id=actor_id,
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=[
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
        ],
        thread_id=binding.thread_id,
        purpose=binding.communication_purpose,
        delivery_purpose=binding.communication_purpose,
        template_key=binding.template.template_id,
        locale=binding.locale,
        requested_link_intents=("privacy_notice",),
        resolved_links=(
            ResolvedLinkSnapshot(
                link_intent="privacy_notice",
                public_url=rodo_link,
                variable_name="rodo_link",
            ),
        ),
        render_variables={"first_name": first_name, "rodo_link": rodo_link},
        policy_decision=auth.to_dict(),
        idempotency_key=f"lead_rodo:{lead.id}:{rodo_version_id}"[:128],
        meta={
            "source": "lead_rodo.sales_pipeline",
            "lead_id": str(lead.id),
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
        },
    )
    try:
        await prepare_and_send_communication(db, command)
    except SendCommunicationError as exc:
        reason = exc.message or str(exc.details.get("reason") if exc.details else "") or "send_failed"
        mark_lead_rodo_failed(lead, reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "reason": f"Email send failed: {reason}",
                "notice_status": "failed",
                "auto_trigger": auto_trigger,
                "ingest_source": ingest_source,
                "details": dict(exc.details or {}),
            },
        )
        return False, f"Failed to send email: {reason}"

    now = datetime.now(timezone.utc).isoformat()
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    rodo_block: Dict[str, Any] = {
        "status": "sent",
        "sent_at": now,
        "channel": channel,
        "recipient": email,
        "rodo_version_id": rodo_version_id,
        "delivery": "communication_pipeline",
        "sales_inquiry_id": binding.sales_inquiry_id,
        "thread_id": binding.thread_id,
    }
    if auto_trigger:
        rodo_block["auto_trigger"] = str(auto_trigger).strip()
    if ingest_source:
        rodo_block["ingest_source"] = str(ingest_source).strip()
    norm["rodo"] = rodo_block
    lead.normalized = norm
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.rodo_sent,
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=actor_id,
        payload={
            "channel": channel,
            "lead_id": str(lead.id),
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
            "delivery": "communication_pipeline",
            "sales_inquiry_id": binding.sales_inquiry_id,
        },
    )
    return True, "RODO email sent for lead"

async def _send_lead_rodo_via_recruitment_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    actor_id: Optional[str],
    email: str,
    channel: str,
    subject: str,
    body: str,
    rodo_link: str,
    rodo_version_id: str,
    auto_trigger: Optional[str],
    ingest_source: Optional[str],
    first_name: str,
) -> Tuple[bool, str]:
    """ADR-031 Recruitment path: binder → authorize → prepare_and_send (no direct SMTP)."""
    from backend.app.communications.command import (
        CommunicationCommand,
        CommunicationOrigin,
        CommunicationRecipient,
        ResolvedLinkSnapshot,
        SendCommunicationContent,
    )
    from backend.app.communications.intent import CommunicationIntent
    from backend.app.communications.prepare_send import prepare_and_send_communication
    from backend.app.communications.send_communication import SendCommunicationError
    from backend.app.communications.send_pipeline import (
        CommunicationSendRequest,
        authorize_outbound_communication,
    )
    from backend.app.modules.recruitment.communication.compliance_pipeline import (
        PURPOSE_GDPR_NOTICE,
        ensure_recruitment_compliance_pipeline_binding,
    )

    binding = await ensure_recruitment_compliance_pipeline_binding(
        db,
        tenant_id=str(tenant_id),
        lead=lead,
        purpose=PURPOSE_GDPR_NOTICE,
        actor_user_id=actor_id,
        source="recruitment.lead_rodo",
    )
    auth = await authorize_outbound_communication(
        db,
        CommunicationSendRequest(
            tenant_id=str(tenant_id),
            thread_id=binding.thread_id,
            channel="email",
            communication_purpose=binding.communication_purpose,
            template=binding.template,
            locale=binding.locale,
        ),
    )
    if not auth.allowed:
        reason = str(auth.reason_code or "communication_pipeline_denied")
        mark_lead_rodo_failed(lead, reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "reason": f"Pipeline denied: {reason}",
                "notice_status": "failed",
                "auto_trigger": auto_trigger,
                "ingest_source": ingest_source,
                "authorization": auth.to_dict(),
            },
        )
        return False, f"Failed to send email: {reason}"

    command = CommunicationCommand(
        tenant_id=str(tenant_id),
        origin=CommunicationOrigin(
            entity_type="application",
            entity_id=binding.application_id,
        ),
        recipients=[
            CommunicationRecipient(
                address=email,
                label=first_name,
                recipient_type="lead",
                recipient_id=str(lead.id),
            )
        ],
        channel="email",
        intent=CommunicationIntent.GDPR_NOTICE,
        content=SendCommunicationContent(
            subject=subject,
            body_text=body,
            message_type="email",
        ),
        actor_id=actor_id,
        own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
        related_entities=[
            CommunicationOrigin(entity_type="lead", entity_id=str(lead.id)),
            CommunicationOrigin(entity_type="candidate", entity_id=binding.candidate_id),
        ],
        thread_id=binding.thread_id,
        purpose=binding.communication_purpose,
        delivery_purpose=binding.communication_purpose,
        template_key=binding.template.template_id,
        locale=binding.locale,
        requested_link_intents=("privacy_notice",),
        resolved_links=(
            ResolvedLinkSnapshot(
                link_intent="privacy_notice",
                public_url=rodo_link,
                variable_name="rodo_link",
            ),
        ),
        render_variables={"first_name": first_name, "rodo_link": rodo_link},
        policy_decision=auth.to_dict(),
        idempotency_key=f"lead_rodo:{lead.id}:{rodo_version_id}"[:128],
        meta={
            "source": "lead_rodo.recruitment_pipeline",
            "lead_id": str(lead.id),
            "application_id": binding.application_id,
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
        },
    )
    try:
        await prepare_and_send_communication(db, command)
    except SendCommunicationError as exc:
        reason = (
            exc.message
            or str(exc.details.get("reason") if exc.details else "")
            or "send_failed"
        )
        mark_lead_rodo_failed(lead, reason=reason)
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "reason": f"Email send failed: {reason}",
                "notice_status": "failed",
                "auto_trigger": auto_trigger,
                "ingest_source": ingest_source,
                "details": dict(exc.details or {}),
            },
        )
        return False, f"Failed to send email: {reason}"

    now = datetime.now(timezone.utc).isoformat()
    norm_out: Dict[str, Any] = (
        dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    )
    rodo_block_out: Dict[str, Any] = {
        "status": "sent",
        "sent_at": now,
        "channel": channel,
        "recipient": email,
        "rodo_version_id": rodo_version_id,
        "delivery": "communication_pipeline",
        "application_id": binding.application_id,
        "thread_id": binding.thread_id,
    }
    if auto_trigger:
        rodo_block_out["auto_trigger"] = str(auto_trigger).strip()
    if ingest_source:
        rodo_block_out["ingest_source"] = str(ingest_source).strip()
    norm_out["rodo"] = rodo_block_out
    lead.normalized = norm_out
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.rodo_sent,
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=actor_id,
        payload={
            "channel": channel,
            "lead_id": str(lead.id),
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
            "delivery": "communication_pipeline",
            "application_id": binding.application_id,
        },
    )
    return True, "RODO email sent for lead"


def rodo_lead_audit_for_candidate_extra(lead_normalized: Optional[Dict[str, Any]], lead_id: str) -> Optional[Dict[str, Any]]:
    """Shape copied into ``Candidate.extra['rodo_lead_audit']`` after conversion (read-only on candidate)."""
    if not isinstance(lead_normalized, dict):
        return None
    if not lead_rodo_satisfied_from_normalized(lead_normalized):
        return None
    block = lead_normalized_rodo_block(lead_normalized)
    st = str(block.get("status") or "").strip().lower()
    base: Dict[str, Any] = {"lead_id": str(lead_id)}
    if st == "source_provided":
        return {
            **base,
            "via": "source_provided",
            "source_provided_at": block.get("source_provided_at"),
            "source_provided_by": block.get("source_provided_by"),
        }
    if st == "satisfied":
        return {**base, "via": "satisfied"}
    if not lead_rodo_sent_from_normalized(lead_normalized):
        return None
    return {
        **base,
        "sent_at": block.get("sent_at"),
        "channel": block.get("channel") or "email",
        "rodo_version_id": block.get("rodo_version_id"),
    }


def mark_lead_rodo_source_provided(
    lead: Lead,
    *,
    actor_id: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """Stamp ``normalized['rodo'].status = source_provided`` (e.g. public intake already included art.14)."""
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    prev = lead_normalized_rodo_block(norm)
    block: Dict[str, Any] = {**prev} if prev else {}
    now = datetime.now(timezone.utc).isoformat()
    block["status"] = "source_provided"
    block["source_provided_at"] = now
    if actor_id:
        block["source_provided_by"] = str(actor_id).strip()
    if note:
        block["source_provided_note"] = str(note).strip()[:2000]
    norm["rodo"] = block
    lead.normalized = norm


__all__ = [
    "normalized_merging_lead_rodo",
    "ensure_lead_rodo_allows_action",
    "LEAD_RODO_ACTION_COMMUNICATION_CALL",
    "LEAD_RODO_ACTION_COMMUNICATION_EMAIL",
    "LEAD_RODO_ACTION_COMMUNICATION_WHATSAPP",
    "LEAD_RODO_ACTION_CONTACTED_STAGE",
    "LEAD_RODO_ACTION_PROCESS",
    "LEAD_RODO_ACTION_REQUEST_DOCUMENTS",
    "LEAD_RODO_ACTION_REQUEST_INFO",
    "lead_normalized_rodo_block",
    "lead_rodo_notice_status_from_normalized",
    "lead_rodo_required_block_code",
    "mark_lead_rodo_failed",
    "mark_lead_rodo_pending_channel",
    "lead_rodo_satisfied",
    "lead_rodo_satisfied_from_normalized",
    "lead_rodo_sent_from_normalized",
    "mark_lead_rodo_source_provided",
    "rodo_lead_audit_for_candidate_extra",
    "send_lead_rodo_email",
]
