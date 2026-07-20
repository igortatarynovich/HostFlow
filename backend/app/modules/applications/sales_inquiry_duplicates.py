"""Sales Inquiry ↔ Inquiry duplicate hints (phone + email).

Recruitment already dedups Lead→Candidate by phone. Client inquiries need the
same signal across *other client leads* so operators do not treat two Meta
forms from one firm as two unrelated deals.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.modules.applications.mappers import lead_to_sales_inquiry
from backend.app.modules.applications.schemas import ApplicationOut
from backend.app.services.contact_identifiers import normalize_email, normalize_phone_digits


MatchReason = Literal["phone", "email", "phone_and_email"]


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def client_inquiry_phone_digits(lead: Lead) -> Optional[str]:
    normalized = _record(getattr(lead, "normalized", None))
    contact = _record(normalized.get("contact_person"))
    raw = (
        _text(contact.get("phone"))
        or _text(normalized.get("phone"))
        or _text(getattr(lead, "phone", None))
    )
    return normalize_phone_digits(raw)


def client_inquiry_emails(lead: Lead) -> set[str]:
    normalized = _record(getattr(lead, "normalized", None))
    contact = _record(normalized.get("contact_person"))
    payload = _record(getattr(lead, "payload", None))
    contact_p = _record(payload.get("contact"))
    raw_values = [
        contact.get("email"),
        normalized.get("email"),
        getattr(lead, "email", None),
        contact_p.get("email"),
        payload.get("email"),
    ]
    out: set[str] = set()
    for raw in raw_values:
        email = normalize_email(_text(raw))
        if email:
            out.add(email)
    return out


def phones_operational_match(a: str, b: str) -> bool:
    """Intl/national tolerant match (same semantics as recruitment lead dedup)."""
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 9 and b.endswith(a[-min(9, len(a)) :]):
        return True
    if len(b) >= 9 and a.endswith(b[-min(9, len(b)) :]):
        return True
    return False


def _match_reason(*, phone_hit: bool, email_hit: bool) -> Optional[MatchReason]:
    if phone_hit and email_hit:
        return "phone_and_email"
    if phone_hit:
        return "phone"
    if email_hit:
        return "email"
    return None


async def find_possible_duplicate_sales_inquiries(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    own_company_id: Optional[str] = None,
    limit: int = 10,
) -> list[tuple[ApplicationOut, MatchReason]]:
    """
    Other open/active-ish client inquiries sharing phone and/or email.

    Phone is the primary signal for Meta ads noise (same person, different emails).
    """
    self_id = str(lead.id)
    self_phone = client_inquiry_phone_digits(lead)
    self_emails = client_inquiry_emails(lead)
    if not self_phone and not self_emails:
        return []

    stmt = (
        sa.select(Lead)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.lead_type == "client",
            Lead.lead_target_type == "client_lead",
            Lead.id != self_id,
        )
        .order_by(sa.desc(Lead.created_at))
        .limit(3000)
    )
    if own_company_id:
        stmt = stmt.where(Lead.own_company_id == str(own_company_id))

    rows: Sequence[Lead] = (await db.execute(stmt)).scalars().all()
    hits: list[tuple[ApplicationOut, MatchReason, Any]] = []
    for row in rows:
        phone_hit = bool(
            self_phone
            and (other := client_inquiry_phone_digits(row))
            and phones_operational_match(self_phone, other)
        )
        other_emails = client_inquiry_emails(row)
        email_hit = bool(self_emails and other_emails and (self_emails & other_emails))
        reason = _match_reason(phone_hit=phone_hit, email_hit=email_hit)
        if not reason:
            continue
        hits.append((lead_to_sales_inquiry(row), reason, getattr(row, "created_at", None)))
        if len(hits) >= max(1, min(int(limit), 20)):
            break

    return [(app, reason) for app, reason, _ in hits]
