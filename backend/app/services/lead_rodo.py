"""RODO / art.14 on Lead (primary); candidate receives audit copy on conversion only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.core.config import settings
from backend.app.models.lead import Lead
from backend.app.services.audit import log_audit_event
from backend.app.services.legal_documents import get_active_legal_document
from backend.app.services.tenant_email import send_email_for_tenant


def lead_normalized_rodo_block(normalized: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(normalized, dict):
        return {}
    raw = normalized.get("rodo")
    return raw if isinstance(raw, dict) else {}


def lead_rodo_sent_from_normalized(normalized: Optional[Dict[str, Any]]) -> bool:
    block = lead_normalized_rodo_block(normalized)
    if str(block.get("status") or "").strip().lower() == "sent":
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


async def send_lead_rodo_email(
    db: AsyncSession,
    *,
    lead: Lead,
    tenant_id: str,
    actor_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Send RODO notice to the lead contact email; persist audit under ``lead.normalized['rodo']``.
    Does not create ``RodoNotification`` (candidate row may not exist yet).
    """
    norm: Dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    email = str(norm.get("email") or "").strip()
    if not email:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={"reason": "Lead has no email in normalized"},
        )
        return False, "Lead has no email"

    if lead_rodo_sent_from_normalized(norm):
        return False, "RODO already sent for this lead"

    rodo_doc = await get_active_legal_document(db, tenant_id, "rodo_clause")
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
    subject = "RODO / GDPR — Personal data processing information | HostFlow"

    try:
        await send_email_for_tenant(
            db,
            tenant_id=tenant_id,
            to=email,
            subject=subject,
            body=body,
        )
    except Exception as e:
        reason = str(e) if str(e) else type(e).__name__
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.lead,
            entity_id=str(lead.id),
            actor_id=actor_id,
            payload={"reason": f"Email send failed: {reason}"},
        )
        return False, f"Failed to send email: {reason}"

    now = datetime.now(timezone.utc).isoformat()
    rodo_block: Dict[str, Any] = {
        "status": "sent",
        "sent_at": now,
        "channel": "email",
        "recipient": email,
        "rodo_version_id": str(rodo_doc.version_id),
    }
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
        payload={"channel": "email", "lead_id": str(lead.id)},
    )
    return True, "RODO email sent for lead"


def rodo_lead_audit_for_candidate_extra(lead_normalized: Optional[Dict[str, Any]], lead_id: str) -> Optional[Dict[str, Any]]:
    """Shape copied into ``Candidate.extra['rodo_lead_audit']`` after conversion (read-only on candidate)."""
    block = lead_normalized_rodo_block(lead_normalized)
    if not lead_rodo_sent_from_normalized(lead_normalized if isinstance(lead_normalized, dict) else {}):
        return None
    return {
        "sent_at": block.get("sent_at"),
        "channel": block.get("channel") or "email",
        "rodo_version_id": block.get("rodo_version_id"),
        "lead_id": str(lead_id),
    }


__all__ = [
    "lead_normalized_rodo_block",
    "lead_rodo_sent_from_normalized",
    "rodo_lead_audit_for_candidate_extra",
    "send_lead_rodo_email",
]
