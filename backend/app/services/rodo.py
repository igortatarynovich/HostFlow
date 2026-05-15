"""RODO notification service (art.14: inform candidate before first contact)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.core.config import settings
from backend.app.models.candidate import Candidate
from backend.app.models.legal_document import LegalDocument
from backend.app.models.rodo_notification import RodoNotification
from backend.app.services.audit import log_audit_event
from backend.app.services.legal_documents import get_active_legal_document
from backend.app.services.tenant_email import send_email_for_tenant


async def get_first_rodo_sent(
    db: AsyncSession,
    candidate_id: str,
) -> RodoNotification | None:
    """Get the first successful RODO notification for candidate (obowiązek informacyjny)."""
    stmt = (
        select(RodoNotification)
        .where(RodoNotification.candidate_id == candidate_id)
        .where(RodoNotification.status == "sent")
        .order_by(RodoNotification.sent_at.asc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def send_rodo_email(
    db: AsyncSession,
    *,
    candidate_id: str,
    tenant_id: str,
    actor_id: Optional[str] = None,
) -> tuple[bool, str, Optional[RodoNotification]]:
    """
    Send RODO info email to candidate. Creates immutable rodo_notification record.
    Returns (success, message, notification or None).
    """
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=actor_id,
            payload={"reason": "Candidate not found"},
        )
        return False, "Candidate not found", None

    email = (cand.email or "").strip() if cand else ""
    if not email:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=actor_id,
            payload={"reason": "Candidate has no email"},
        )
        return False, "Candidate has no email", None

    first_sent = await get_first_rodo_sent(db, candidate_id)
    if first_sent:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=actor_id,
            payload={"reason": "RODO already sent (first notification immutable)"},
        )
        return False, "RODO already sent (first notification immutable)", first_sent

    rodo_doc = await get_active_legal_document(db, tenant_id, "rodo_clause")
    if not rodo_doc:
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.rodo_sent_failed,
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=actor_id,
            payload={"reason": "No active RODO document configured"},
        )
        return False, "No active RODO document configured", None

    link = (rodo_doc.content_url or "").strip()
    if not link:
        base = (settings.frontend_url or "").strip().rstrip("/")
        link = f"{base}/legal/rodo.html" if base else "/legal/rodo.html"

    first_name = (cand.first_name or "Candidate").strip()

    # Simple plain-text body in three languages: English, Polish, Russian
    # Без декоративных разделителей, чтобы почтовые клиенты не дублировали блоки.
    body = f"""Dear {first_name},

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

    subject = "RODO / GDPR — Personal data processing information | HostFlow"

    now = datetime.now(timezone.utc)
    notification = RodoNotification(
        id=str(uuid4()),
        candidate_id=candidate_id,
        sent_at=now,
        sent_by_user_id=actor_id,
        channel="email",
        recipient=email,
        rodo_version_id=rodo_doc.version_id,
        status="sent",
    )

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
            entity_type=AuditEntityType.candidate,
            entity_id=candidate_id,
            actor_id=actor_id,
            payload={"reason": f"Email send failed: {reason}"},
        )
        return False, f"Failed to send email: {reason}", None

    db.add(notification)
    await db.flush()
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.rodo_sent,
        entity_type=AuditEntityType.rodo_notification,
        entity_id=notification.id,
        actor_id=actor_id,
        payload={"candidate_id": candidate_id, "channel": "email"},
    )
    return True, "RODO email sent", notification


def rodo_lead_audit_satisfied_from_candidate(candidate: Candidate) -> bool:
    """True when lead-stage RODO was copied onto the candidate at conversion (read-only audit)."""
    try:
        extra = candidate._get_extra()
    except Exception:
        try:
            extra = json.loads(candidate.extra or "{}")
        except Exception:
            extra = {}
    if not isinstance(extra, dict):
        return False
    audit = extra.get("rodo_lead_audit")
    if not isinstance(audit, dict):
        return False
    via = str(audit.get("via") or "").strip().lower()
    if via == "source_provided":
        return True
    if via == "satisfied":
        return True
    return bool(str(audit.get("sent_at") or "").strip())


async def candidate_rodo_compliance_satisfied(
    db: AsyncSession,
    candidate_id: str,
    *,
    candidate: Candidate | None = None,
) -> bool:
    """RODO satisfied for contact/stage gates: row-level notification **or** lead audit copy."""
    if await get_first_rodo_sent(db, candidate_id):
        return True
    cand = candidate or await db.get(Candidate, candidate_id)
    if not cand:
        return False
    return rodo_lead_audit_satisfied_from_candidate(cand)
