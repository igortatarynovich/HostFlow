"""Mailbox DSN / bounce → Lead.normalized.rodo undelivered write-back.

SMTP ``sent`` only means accept. Gmail/Interia DSNs (\"Адрес не найден\",
\"Пока не доставлено\", SPF unsafe) must reopen the art.14 gate so operators
cannot convert until notice is re-sent or marked source-provided.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.lead import Lead
from backend.app.services.audit import log_audit_event
from backend.app.services.lead_rodo import (
    LEAD_RODO_REASON_DEFERRED,
    LEAD_RODO_REASON_DELIVERY_FAILED,
    LEAD_RODO_REASON_INVALID_RECIPIENT,
    LEAD_RODO_REASON_SPF_REJECTED,
    lead_normalized_rodo_block,
    mark_lead_rodo_undelivered,
)

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)

_BOUNCE_HINTS = (
    "адрес не найден",
    "address not found",
    "пока не доставлено",
    "not yet delivered",
    "mail delivery failed",
    "delivery status notification",
    "undeliverable",
    "mailer-daemon",
    "mail delivery subsystem",
    "does not exist",
    "nosuchuser",
    "5.1.1",
    "spf unsafe",
    "recipient address rejected",
)


@dataclass(frozen=True, slots=True)
class ParsedRodoDeliveryFeedback:
    recipient_email: str
    outcome: str  # deferred | failed
    reason_code: str
    reason: str


def looks_like_delivery_failure_notice(
    *,
    subject: str | None = None,
    body_text: str | None = None,
    from_address: str | None = None,
) -> bool:
    blob = " ".join(
        x
        for x in (
            str(subject or ""),
            str(body_text or ""),
            str(from_address or ""),
        )
        if x
    ).lower()
    return any(h in blob for h in _BOUNCE_HINTS)


def parse_rodo_delivery_feedback(
    *,
    subject: str | None = None,
    body_text: str | None = None,
    from_address: str | None = None,
    exclude_addresses: set[str] | None = None,
) -> ParsedRodoDeliveryFeedback | None:
    """Extract recipient + outcome from a provider DSN / Gmail bounce notice."""
    if not looks_like_delivery_failure_notice(
        subject=subject, body_text=body_text, from_address=from_address
    ):
        return None

    subject_s = str(subject or "")
    body = str(body_text or "")
    full = f"{subject_s}\n{body}"
    full_l = full.lower()

    exclude = {a.strip().lower() for a in (exclude_addresses or set()) if a}
    exclude.update(
        {
            "mailer-daemon@google.com",
            "mailer-daemon@googlemail.com",
            "postmaster@google.com",
        }
    )

    recipient: str | None = None
    m = re.search(
        r"(?:адрес|address|получател[еюы]|recipient)\s*[:=]?\s*"
        r"<?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})>?",
        full,
        re.IGNORECASE,
    )
    if m:
        recipient = m.group(1).strip().lower()
    if not recipient:
        for em in _EMAIL_RE.findall(full):
            low = em.strip().lower()
            if low in exclude:
                continue
            if any(
                x in low
                for x in ("mailer-daemon", "postmaster", "hostflow.cc", "google.com")
            ):
                continue
            recipient = low
            break
    if not recipient:
        return None

    if "spf unsafe" in full_l or "deferred due to spf" in full_l:
        return ParsedRodoDeliveryFeedback(
            recipient_email=recipient,
            outcome="deferred",
            reason_code=LEAD_RODO_REASON_SPF_REJECTED,
            reason="Recipient server deferred delivery due to SPF (address may be valid).",
        )
    deferred_hints = (
        "пока не доставлено" in full_l
        or "not yet delivered" in full_l
        or "4.4.0" in full_l
        or "will keep trying" in full_l
        or "будет повторять" in full_l
        or ("temporary" in full_l and ("error" in full_l or "defer" in full_l))
    )
    permanent_hints = (
        "5.1.1" in full_l
        or "nosuchuser" in full_l
        or "does not exist" in full_l
        or "адрес не найден" in full_l
        or "address not found" in full_l
    )
    if deferred_hints and not permanent_hints:
        return ParsedRodoDeliveryFeedback(
            recipient_email=recipient,
            outcome="deferred",
            reason_code=LEAD_RODO_REASON_DEFERRED,
            reason="Delivery temporarily delayed by the recipient server.",
        )
    if permanent_hints:
        return ParsedRodoDeliveryFeedback(
            recipient_email=recipient,
            outcome="failed",
            reason_code=LEAD_RODO_REASON_INVALID_RECIPIENT,
            reason="Email address not found or does not accept mail.",
        )
    return ParsedRodoDeliveryFeedback(
        recipient_email=recipient,
        outcome="failed",
        reason_code=LEAD_RODO_REASON_DELIVERY_FAILED,
        reason="RODO notice delivery failed (provider bounce).",
    )


async def _find_leads_for_rodo_recipient(
    db: AsyncSession,
    *,
    tenant_id: str,
    recipient_email: str,
) -> list[Lead]:
    email = str(recipient_email or "").strip().lower()
    if not email or "@" not in email:
        return []
    stmt = (
        select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.candidate_id.is_(None),
            or_(
                func.lower(Lead.normalized["rodo"]["recipient"].as_string()) == email,
                func.lower(Lead.normalized["email"].as_string()) == email,
                func.lower(Lead.payload["email"].as_string()) == email,
            ),
        )
        .order_by(Lead.created_at.desc())
        .limit(25)
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: list[Lead] = []
    for lead in rows:
        block = lead_normalized_rodo_block(
            lead.normalized if isinstance(lead.normalized, dict) else {}
        )
        st = str(block.get("status") or "").strip().lower()
        if st in ("sent", "satisfied", "failed", "deferred", "undelivered") or block.get(
            "sent_at"
        ):
            out.append(lead)
    return out


async def apply_rodo_delivery_feedback_to_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    feedback: ParsedRodoDeliveryFeedback,
    provider_event_id: str | None = None,
    actor_id: str | None = None,
) -> list[str]:
    """Mark matching leads undelivered/deferred. Returns updated lead ids."""
    leads = await _find_leads_for_rodo_recipient(
        db, tenant_id=tenant_id, recipient_email=feedback.recipient_email
    )
    updated: list[str] = []
    event_id = (provider_event_id or "").strip() or f"dsn:{uuid4()}"
    for lead in leads:
        block = lead_normalized_rodo_block(
            lead.normalized if isinstance(lead.normalized, dict) else {}
        )
        prev_event = str(block.get("delivery_feedback_event_id") or "").strip()
        if prev_event and prev_event == event_id:
            continue
        # Idempotent: same outcome+code already applied → skip audit spam.
        if (
            str(block.get("status") or "").strip().lower()
            == ("deferred" if feedback.outcome == "deferred" else "failed")
            and str(block.get("failure_reason_code") or "").strip().lower()
            == feedback.reason_code
            and str(block.get("failure_reason") or "").strip() == feedback.reason
        ):
            continue
        mark_lead_rodo_undelivered(
            lead,
            reason=feedback.reason,
            reason_code=feedback.reason_code,
            outcome=feedback.outcome,
            provider_event_id=event_id,
        )
        await db.flush()
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={
                "source": "delivery_feedback",
                "outcome": feedback.outcome,
                "reason_code": feedback.reason_code,
                "reason": feedback.reason,
                "recipient": feedback.recipient_email,
                "provider_event_id": event_id,
            },
        )
        updated.append(str(lead.id))
    return updated


async def maybe_apply_rodo_delivery_feedback_from_inbound(
    db: AsyncSession,
    *,
    tenant_id: str,
    subject: str | None = None,
    body_text: str | None = None,
    from_address: str | None = None,
    external_message_ref: str | None = None,
    inbox_address: str | None = None,
    actor_id: str | None = None,
) -> list[str]:
    """Best-effort: if inbound looks like a DSN, reopen RODO on matching leads."""
    exclude: set[str] = set()
    if inbox_address:
        exclude.add(str(inbox_address).strip().lower())
    feedback = parse_rodo_delivery_feedback(
        subject=subject,
        body_text=body_text,
        from_address=from_address,
        exclude_addresses=exclude,
    )
    if feedback is None:
        return []
    try:
        return await apply_rodo_delivery_feedback_to_leads(
            db,
            tenant_id=tenant_id,
            feedback=feedback,
            provider_event_id=external_message_ref,
            actor_id=actor_id,
        )
    except Exception:
        logger.exception(
            "lead_rodo delivery feedback failed tenant=%s recipient=%s",
            tenant_id,
            feedback.recipient_email,
        )
        return []


async def maybe_apply_rodo_delivery_feedback_from_delivery(
    db: AsyncSession,
    *,
    tenant_id: str,
    purpose: str | None,
    recipient_email: str | None,
    canonical_status: str | None,
    reason_code: str | None = None,
    safe_message: str | None = None,
    provider_event_id: str | None = None,
    actor_id: str | None = None,
) -> list[str]:
    """Wire from delivery diagnostics when gdpr_notice reaches a terminal negative."""
    purpose_l = str(purpose or "").strip().lower()
    if purpose_l not in {"gdpr_notice", "rodo", "rodo_notice"}:
        return []
    status_l = str(canonical_status or "").strip().lower()
    from backend.app.communications.delivery_canon import TERMINAL_NEGATIVE

    if status_l not in TERMINAL_NEGATIVE:
        return []
    email = str(recipient_email or "").strip().lower()
    if not email or "@" not in email:
        return []
    code = str(reason_code or "").strip().lower()
    if code in {"invalid_recipient", "undeliverable"}:
        reason_code_out = LEAD_RODO_REASON_INVALID_RECIPIENT
        reason = safe_message or "Email address not found or does not accept mail."
        outcome = "failed"
    elif code in {"temporary_transport_error", "rate_limit", "provider_unavailable"}:
        reason_code_out = LEAD_RODO_REASON_DEFERRED
        reason = safe_message or "Delivery temporarily delayed by the recipient server."
        outcome = "deferred"
    else:
        reason_code_out = LEAD_RODO_REASON_DELIVERY_FAILED
        reason = safe_message or f"RODO notice delivery failed ({status_l})."
        outcome = "failed"
    feedback = ParsedRodoDeliveryFeedback(
        recipient_email=email,
        outcome=outcome,
        reason_code=reason_code_out,
        reason=str(reason)[:2000],
    )
    return await apply_rodo_delivery_feedback_to_leads(
        db,
        tenant_id=tenant_id,
        feedback=feedback,
        provider_event_id=provider_event_id,
        actor_id=actor_id,
    )


__all__ = [
    "ParsedRodoDeliveryFeedback",
    "apply_rodo_delivery_feedback_to_leads",
    "looks_like_delivery_failure_notice",
    "maybe_apply_rodo_delivery_feedback_from_delivery",
    "maybe_apply_rodo_delivery_feedback_from_inbound",
    "parse_rodo_delivery_feedback",
]
