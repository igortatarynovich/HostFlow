"""RODO information obligation on Lead (evaluate + fulfill); candidate receives audit copy on conversion only."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.core.config import settings
from backend.app.models.lead import Lead
from backend.app.services.audit import log_audit_event
from backend.app.services.lead_lifecycle_email_policy import (
    PLATFORM_RODO_CLAUSE_VERSION_ID,
    PLATFORM_RODO_PUBLIC_PATH,
    is_platform_rodo_template_ref,
)
from backend.app.services.lead_rodo_obligation import (
    ComplianceTransitionError,
    apply_compliance_transition,
    current_compliance_state,
    has_assessment_proof,
    has_delivery_proof,
    has_exemption_proof,
    notice_provided_at_source,
)
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


# Negative delivery outcomes block gates even when ``sent_at`` remains for audit.
LEAD_RODO_NEGATIVE_STATUSES: frozenset[str] = frozenset(
    {
        "failed",
        "deferred",
        "undelivered",
        "pending_channel",
        "pending_policy",
        "review_required",
        "delivery_required",
        "delivery_failed",
    }
)

LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING = "policy_template_missing"
LEAD_RODO_REASON_POLICY_MISCONFIGURED = "policy_misconfigured"

# Human-facing reason codes written by delivery feedback (mailbox DSN / callbacks).
LEAD_RODO_REASON_INVALID_RECIPIENT = "invalid_recipient"
LEAD_RODO_REASON_SPF_REJECTED = "spf_rejected"
LEAD_RODO_REASON_DEFERRED = "deferred"
LEAD_RODO_REASON_DELIVERY_FAILED = "delivery_failed"


def lead_rodo_satisfied_from_normalized(normalized: Optional[Dict[str, Any]]) -> bool:
    """Information obligation closed only with proof — never by compliance_state alone.

    SMTP ``sent`` counts until a delivery problem is recorded. Temporary deferral
    also blocks. Source-provided requires assessment evidence; exemption requires
    a valid reason code. Webhook/notify is not fulfillment proof.
    """
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else {})
    cs = current_compliance_state(block)
    if cs in ("review_required", "delivery_required", "delivery_failed") or not cs:
        return False
    if cs == "delivered":
        return has_delivery_proof(block)
    if cs == "compliant":
        return has_assessment_proof(block)
    if cs == "exempt":
        return has_exemption_proof(block)
    return False


def lead_rodo_notice_status_from_normalized(normalized: Optional[Dict[str, Any]]) -> str:
    """
    UI / API contract:
    ``sent`` | ``failed`` | ``deferred`` | ``pending_channel`` | ``manual_required``
    | ``source_provided`` | ``exempt`` | ``review_required`` | ``delivery_required``.
    """
    block = lead_normalized_rodo_block(normalized if isinstance(normalized, dict) else {})
    st = str(block.get("status") or "").strip().lower()
    if st == "source_provided":
        return "source_provided"
    if st == "exempt":
        return "exempt"
    if st == "review_required":
        return "review_required"
    if st == "delivery_required":
        return "delivery_required"
    if st == "delivery_failed":
        return "failed"
    if st == "deferred":
        return "deferred"
    if st in ("failed", "undelivered"):
        return "failed"
    if st == "pending_channel":
        return "pending_channel"
    if st == "pending_policy":
        return "pending_policy"
    if st in ("sent", "satisfied") or block.get("sent_at"):
        return "sent"
    return "manual_required"


def mark_lead_rodo_pending_channel(lead: Lead, *, reason: str = "no_channel") -> None:
    from sqlalchemy.orm.attributes import flag_modified

    now = datetime.now(timezone.utc).isoformat()
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    _merge_delivery_evidence(
        block,
        state="delivery_failed",
        failure_reason=str(reason or "no_channel").strip()[:256],
        recorded_at=now,
    )
    if not apply_compliance_transition(block, "delivery_failed"):
        return
    block["status"] = "pending_channel"
    block["pending_reason"] = str(reason or "no_channel").strip()[:256]
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


def mark_lead_rodo_pending_policy(
    lead: Lead,
    *,
    reason: str,
    reason_code: str = LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING,
) -> None:
    """Fail-closed RODO when lifecycle email policy cannot resolve a template (ADR-033)."""
    from sqlalchemy.orm.attributes import flag_modified

    code = str(reason_code or LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING).strip().lower()[:64]
    if code not in (
        LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING,
        LEAD_RODO_REASON_POLICY_MISCONFIGURED,
    ):
        code = LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING
    now = datetime.now(timezone.utc).isoformat()
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    _merge_delivery_evidence(
        block,
        state="delivery_failed",
        failure_reason=str(reason or "").strip()[:2000],
        failure_reason_code=code,
        recorded_at=now,
    )
    if not apply_compliance_transition(block, "delivery_failed"):
        return
    block["status"] = "pending_policy"
    block["failure_reason"] = str(reason or "").strip()[:2000]
    block["failure_reason_code"] = code
    block["policy_blocked"] = True
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


def mark_lead_rodo_failed(lead: Lead, *, reason: str, attempts: Optional[list] = None) -> None:
    from sqlalchemy.orm.attributes import flag_modified

    now = datetime.now(timezone.utc).isoformat()
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    extra: Dict[str, Any] = {
        "state": "delivery_failed",
        "failure_reason": str(reason or "").strip()[:2000],
        "recorded_at": now,
    }
    if attempts:
        extra["attempts"] = attempts
    _merge_delivery_evidence(block, **extra)
    if not apply_compliance_transition(block, "delivery_failed"):
        return
    block["status"] = "failed"
    block["failure_reason"] = str(reason or "").strip()[:2000]
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


def mark_lead_rodo_undelivered(
    lead: Lead,
    *,
    reason: str,
    reason_code: str = LEAD_RODO_REASON_DELIVERY_FAILED,
    outcome: str = "failed",
    provider_event_id: str | None = None,
) -> None:
    """Record post-accept delivery problem (bounce / deferral). Clears gate satisfaction.

    ``outcome``:
    - ``deferred`` — temporary (e.g. Gmail «Пока не доставлено»); still blocks conversion
    - ``failed`` / ``undelivered`` — permanent or operator-visible failure
    """
    now = datetime.now(timezone.utc).isoformat()
    oc = str(outcome or "failed").strip().lower()
    if oc not in ("deferred", "failed", "undelivered"):
        oc = "failed"
    status = "deferred" if oc == "deferred" else "failed"
    code = str(reason_code or LEAD_RODO_REASON_DELIVERY_FAILED).strip().lower()[:64]
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    _merge_delivery_evidence(
        block,
        state="delivery_failed",
        failure_reason=str(reason or "").strip()[:2000],
        failure_reason_code=code,
        delivery_outcome=oc,
        recorded_at=now,
        provider_event_id=str(provider_event_id).strip()[:255] if provider_event_id else None,
    )
    if not apply_compliance_transition(block, "delivery_failed"):
        return
    from sqlalchemy.orm.attributes import flag_modified

    block["status"] = status
    block["failure_reason"] = str(reason or "").strip()[:2000]
    block["failure_reason_code"] = code
    block["delivery_outcome"] = oc
    block["undelivered_at"] = now
    if provider_event_id:
        block["delivery_feedback_event_id"] = str(provider_event_id).strip()[:255]
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


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
    """True when outbound art.14 email was already sent (blocks duplicate send; ``source_provided`` alone does not).

    Negative delivery outcomes (``failed`` / ``deferred`` / ``undelivered``) allow retry even if
    ``sent_at`` is still present for audit.
    """
    block = lead_normalized_rodo_block(normalized)
    st = str(block.get("status") or "").strip().lower()
    if st in LEAD_RODO_NEGATIVE_STATUSES:
        return False
    if st in ("sent", "satisfied"):
        return True
    return bool(str(block.get("sent_at") or "").strip())


def _rodo_email_body(first_name: str, link: str, controller_name: str) -> str:
    firm = (controller_name or "").strip() or "the data controller"
    return f"""Dear {first_name},

{firm} is the controller of your personal data. This message fulfills the GDPR/RODO information obligation.

Please find below the information on the processing of your personal data:

{link}

Best regards,
{firm}

---

Dzień dobry {first_name},

Administratorem Twoich danych osobowych jest {firm}. Ta wiadomość realizuje obowiązek informacyjny RODO.

W załączeniu przekazujemy informację dotyczącą przetwarzania Twoich danych osobowych:

{link}

Pozdrawiamy,
{firm}

---

Здравствуйте, {first_name},

Администратором (контролёром) ваших персональных данных является {firm}. Это сообщение исполняет информационную обязанность GDPR/RODO.

Направляем информацию об обработке ваших персональных данных:

{link}

С уважением,
{firm}"""


async def resolve_lead_controller_identity(
    db: AsyncSession,
    lead: Lead,
) -> tuple[Optional[str], str]:
    """OwnCompany is the named controller; HostFlow is delivery infrastructure only."""
    from backend.app.models.own_company import OwnCompany

    oc_id = str(getattr(lead, "own_company_id", None) or "").strip() or None
    if not oc_id:
        return None, ""
    row = await db.get(OwnCompany, oc_id)
    if row is None:
        return oc_id, ""
    name = str(getattr(row, "legal_name", None) or getattr(row, "name", None) or "").strip()
    return oc_id, name


def _notice_content_hash(*, body: str, link: str) -> str:
    return hashlib.sha256(f"{link}\n{body}".encode("utf-8")).hexdigest()


def _merge_delivery_evidence(block: Dict[str, Any], **fields: Any) -> None:
    prev = block.get("delivery_evidence")
    evidence: Dict[str, Any] = dict(prev) if isinstance(prev, dict) else {}
    for key, value in fields.items():
        if value is None or value == "":
            continue
        evidence[str(key)] = value
    block["delivery_evidence"] = evidence


def _stamp_lead_rodo_sent(
    lead: Lead,
    *,
    email: str,
    channel: str,
    rodo_version_id: str,
    auto_trigger: Optional[str],
    ingest_source: Optional[str],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Merge a successful SMTP send onto the evaluation block (keep obligation / controller).

    ``delivery_failed`` → ``delivered`` only after proof is on the block. Webhook/notify
    cannot close the obligation.
    """
    from sqlalchemy.orm.attributes import flag_modified

    now = datetime.now(timezone.utc).isoformat()
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: Dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    extra_fields = dict(extra or {})
    evidence_keys = (
        "controller_name",
        "controller_own_company_id",
        "from_email",
        "delivery_via",
        "template_id",
        "template_key",
        "notice_hash",
        "attempts",
        "thread_id",
        "application_id",
        "sales_inquiry_id",
    )
    evidence: Dict[str, Any] = {
        "state": "delivered",
        "recipient": email,
        "channel": channel,
        "sent_at": now,
        "notice_version_id": rodo_version_id,
        "path": "communication_pipeline",
    }
    for key in evidence_keys:
        val = extra_fields.get(key)
        if val is None or val == "":
            continue
        evidence[key] = val
    _merge_delivery_evidence(block, **evidence)
    if extra:
        for key, value in extra.items():
            if value is None or value == "":
                continue
            block[str(key)] = value
    if auto_trigger:
        block["auto_trigger"] = str(auto_trigger).strip()
    if ingest_source:
        block["ingest_source"] = str(ingest_source).strip()
    block["channel"] = channel
    block["recipient"] = email
    block["rodo_version_id"] = rodo_version_id
    block["delivery"] = "communication_pipeline"
    if apply_compliance_transition(block, "delivered"):
        block["status"] = "sent"
        block["sent_at"] = now
    else:
        _merge_delivery_evidence(
            block,
            state="delivery_failed",
            failure_reason="webhook_is_not_gdpr_proof",
            recorded_at=now,
        )
        if apply_compliance_transition(block, "delivery_failed"):
            block["status"] = "failed"
            block["failure_reason"] = "webhook_is_not_gdpr_proof"
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")


def _attempts_from_send_error(exc: Any) -> Optional[list]:
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return None
    raw = details.get("attempts")
    return list(raw) if isinstance(raw, list) else None


def _delivery_fields_from_send_result(result: Any) -> Dict[str, Any]:
    if result is None:
        return {}
    out: Dict[str, Any] = {}
    via = getattr(result, "delivery_via", None)
    from_email = getattr(result, "from_email", None)
    attempts = getattr(result, "delivery_attempts", None)
    if via:
        out["delivery_via"] = str(via)
    if from_email:
        out["from_email"] = str(from_email)
    if attempts:
        out["attempts"] = list(attempts)
    return out


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


def _platform_rodo_content_url() -> str:
    base = (settings.frontend_url or "https://hostflow.cc").strip().rstrip("/")
    return f"{base}{PLATFORM_RODO_PUBLIC_PATH}"


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

    if is_platform_rodo_template_ref(message_template_id):
        message_template_id = None

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
    if rodo_doc:
        link = (rodo_doc.content_url or "").strip()
        rodo_version_id = str(rodo_doc.version_id)
        if not link:
            link = _platform_rodo_content_url()
    else:
        link = _platform_rodo_content_url()
        rodo_version_id = PLATFORM_RODO_CLAUSE_VERSION_ID

    first_name = (str(norm.get("first_name") or norm.get("full_name") or "Lead")).strip() or "Lead"
    controller_id, controller_name = await resolve_lead_controller_identity(db, lead)
    body = _rodo_email_body(first_name, link, controller_name)
    resolved = await resolve_lead_email_message(
        db,
        tenant_id=tenant_id,
        template_id=message_template_id,
        fallback_subject="RODO / GDPR — Personal data processing information",
        fallback_body=body,
        first_name=first_name,
        rodo_link=link,
        controller_name=controller_name or None,
    )
    # Tenant template is optional. Broken refs fall back to the platform art.14 body.
    if message_template_id and not resolved.template_id:
        resolved = await resolve_lead_email_message(
            db,
            tenant_id=tenant_id,
            template_id=None,
            fallback_subject="RODO / GDPR — Personal data processing information",
            fallback_body=body,
            first_name=first_name,
            rodo_link=link,
            controller_name=controller_name or None,
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
                rodo_version_id=rodo_version_id,
                auto_trigger=auto_trigger,
                ingest_source=ingest_source,
                first_name=first_name,
                controller_own_company_id=controller_id,
                controller_name=controller_name,
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
                rodo_version_id=rodo_version_id,
                auto_trigger=auto_trigger,
                ingest_source=ingest_source,
                first_name=first_name,
                controller_own_company_id=controller_id,
                controller_name=controller_name,
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
    controller_own_company_id: Optional[str] = None,
    controller_name: Optional[str] = None,
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
        render_variables={
            "first_name": first_name,
            "rodo_link": rodo_link,
            "controller_name": controller_name or "",
        },
        policy_decision=auth.to_dict(),
        idempotency_key=f"lead_rodo:{lead.id}:{rodo_version_id}"[:128],
        meta={
            "source": "lead_rodo.sales_pipeline",
            "lead_id": str(lead.id),
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
        },
    )
    try:
        send_result = await prepare_and_send_communication(db, command)
    except SendCommunicationError as exc:
        reason = exc.message or str(exc.details.get("reason") if exc.details else "") or "send_failed"
        mark_lead_rodo_failed(lead, reason=reason, attempts=_attempts_from_send_error(exc))
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

    delivery_fields = _delivery_fields_from_send_result(send_result)
    _stamp_lead_rodo_sent(
        lead,
        email=email,
        channel=channel,
        rodo_version_id=rodo_version_id,
        auto_trigger=auto_trigger,
        ingest_source=ingest_source,
        extra={
            "sales_inquiry_id": binding.sales_inquiry_id,
            "thread_id": binding.thread_id,
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
            "template_key": binding.template.template_id,
            "notice_hash": _notice_content_hash(body=body, link=rodo_link),
            **delivery_fields,
        },
    )
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
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
            "rodo_version_id": rodo_version_id,
            **delivery_fields,
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
    controller_own_company_id: Optional[str] = None,
    controller_name: Optional[str] = None,
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
        render_variables={
            "first_name": first_name,
            "rodo_link": rodo_link,
            "controller_name": controller_name or "",
        },
        policy_decision=auth.to_dict(),
        idempotency_key=f"lead_rodo:{lead.id}:{rodo_version_id}"[:128],
        meta={
            "source": "lead_rodo.recruitment_pipeline",
            "lead_id": str(lead.id),
            "application_id": binding.application_id,
            "auto_trigger": auto_trigger,
            "ingest_source": ingest_source,
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
        },
    )
    try:
        send_result = await prepare_and_send_communication(db, command)
    except SendCommunicationError as exc:
        reason = (
            exc.message
            or str(exc.details.get("reason") if exc.details else "")
            or "send_failed"
        )
        mark_lead_rodo_failed(lead, reason=reason, attempts=_attempts_from_send_error(exc))
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

    delivery_fields = _delivery_fields_from_send_result(send_result)
    _stamp_lead_rodo_sent(
        lead,
        email=email,
        channel=channel,
        rodo_version_id=rodo_version_id,
        auto_trigger=auto_trigger,
        ingest_source=ingest_source,
        extra={
            "application_id": binding.application_id,
            "thread_id": binding.thread_id,
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
            "template_key": binding.template.template_id,
            "notice_hash": _notice_content_hash(body=body, link=rodo_link),
            **delivery_fields,
        },
    )
    await db.flush()

    if not auto_trigger:
        from backend.app.modules.leads.intake_lifecycle import mark_recruitment_intake_in_progress

        mark_recruitment_intake_in_progress(
            lead,
            actor=actor_id,
            last_action="rodo_sent",
        )
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
            "controller_own_company_id": controller_own_company_id,
            "controller_name": controller_name,
            "rodo_version_id": rodo_version_id,
            **delivery_fields,
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
    if st == "exempt":
        return {
            **base,
            "via": "exempt",
            "exemption_code": block.get("exemption_code"),
            "article": block.get("article"),
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
    proof: str = "operator_attestation",
) -> None:
    """Close as ``compliant`` only with assessment evidence — never a silent resolve.

    ``proof="notice_at_source"`` — ingest captured that the person saw the notice.
    ``proof="operator_attestation"`` — explicit operator action; ``actor_id`` is required.
    """
    from sqlalchemy.orm.attributes import flag_modified

    proof_kind = str(proof or "operator_attestation").strip().lower()
    actor = str(actor_id or "").strip() or None
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    prev = lead_normalized_rodo_block(norm)
    block: Dict[str, Any] = {**prev} if prev else {}
    cs = current_compliance_state(block)
    if cs in ("delivered", "exempt"):
        return
    if proof_kind == "operator_attestation":
        if not actor:
            raise ComplianceTransitionError(
                "RODO_OPERATOR_REQUIRED",
                "Covered at source is an operator attestation and requires an actor",
            )
    elif proof_kind == "notice_at_source":
        assessment_prev = block.get("assessment") if isinstance(block.get("assessment"), dict) else {}
        if not (
            notice_provided_at_source(norm)
            or (isinstance(assessment_prev, dict) and assessment_prev.get("notice_at_source") is True)
        ):
            raise ComplianceTransitionError(
                "RODO_SOURCE_PROOF_MISSING",
                "notice_at_source proof is missing from the lead assessment",
            )
    else:
        raise ComplianceTransitionError(
            "RODO_UNKNOWN_PROOF",
            "Covered at source requires notice_at_source or operator_attestation",
        )

    now = datetime.now(timezone.utc).isoformat()
    assessment: Dict[str, Any] = (
        dict(block["assessment"]) if isinstance(block.get("assessment"), dict) else {}
    )
    assessment["state"] = "compliant"
    assessment["reason_code"] = (
        "source_provided_operator" if proof_kind == "operator_attestation" else "notice_at_source"
    )
    assessment["notice_at_source"] = proof_kind == "notice_at_source" or bool(
        assessment.get("notice_at_source")
    )
    assessment["proof"] = proof_kind
    assessment["evaluated_at"] = now
    if actor:
        assessment["actor_id"] = actor
    if note:
        assessment["note"] = str(note).strip()[:2000]
    block["assessment"] = assessment
    block["source_provided_at"] = now
    if actor:
        block["source_provided_by"] = actor
    if note:
        block["source_provided_note"] = str(note).strip()[:2000]
    if not apply_compliance_transition(block, "compliant"):
        raise ComplianceTransitionError(
            "RODO_TRANSITION_REJECTED",
            "Cannot close this obligation as compliant without assessment proof",
        )
    block["status"] = "source_provided"
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")
    if actor:
        from backend.app.modules.leads.intake_lifecycle import mark_recruitment_intake_in_progress

        mark_recruitment_intake_in_progress(
            lead,
            actor=actor,
            last_action="rodo_source_provided",
        )


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
    "LEAD_RODO_NEGATIVE_STATUSES",
    "LEAD_RODO_REASON_DEFERRED",
    "LEAD_RODO_REASON_DELIVERY_FAILED",
    "LEAD_RODO_REASON_INVALID_RECIPIENT",
    "LEAD_RODO_REASON_POLICY_MISCONFIGURED",
    "LEAD_RODO_REASON_POLICY_TEMPLATE_MISSING",
    "LEAD_RODO_REASON_SPF_REJECTED",
    "lead_normalized_rodo_block",
    "lead_rodo_notice_status_from_normalized",
    "lead_rodo_required_block_code",
    "mark_lead_rodo_failed",
    "mark_lead_rodo_pending_channel",
    "mark_lead_rodo_pending_policy",
    "mark_lead_rodo_undelivered",
    "lead_rodo_satisfied",
    "lead_rodo_satisfied_from_normalized",
    "lead_rodo_sent_from_normalized",
    "resolve_lead_controller_identity",
    "ComplianceTransitionError",
    "mark_lead_rodo_source_provided",
    "rodo_lead_audit_for_candidate_extra",
    "send_lead_rodo_email",
]
