"""Reusable message hub primitives for email templates and rendering.

Phase 1 (compat mode): this hub reuses lead template storage and keeps existing
call contracts untouched. It centralizes variable rendering and fallback logic
so current flows (RODO + lead operational emails) can share one engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.lead_message_templates import get_lead_message_template_by_id


@dataclass(frozen=True)
class ResolvedMessage:
    subject: str
    body: str
    template_id: Optional[str] = None


def render_message_text(
    text: str,
    *,
    first_name: Optional[str] = None,
    rodo_link: Optional[str] = None,
    controller_name: Optional[str] = None,
) -> str:
    """Render known placeholders in a safe, backward-compatible way."""
    out = str(text or "")
    if first_name is not None:
        out = out.replace("{first_name}", str(first_name))
    if rodo_link is not None:
        out = out.replace("{rodo_link}", str(rodo_link))
    if controller_name is not None:
        out = out.replace("{controller_name}", str(controller_name))
    return out


async def resolve_lead_email_message(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_id: Optional[str],
    fallback_subject: str,
    fallback_body: str,
    first_name: Optional[str] = None,
    rodo_link: Optional[str] = None,
    controller_name: Optional[str] = None,
) -> ResolvedMessage:
    """Resolve template (if active) and render placeholders, else fallback."""
    subject = str(fallback_subject or "")
    body = str(fallback_body or "")
    used_template_id: Optional[str] = None

    tpl = await get_lead_message_template_by_id(db, tenant_id, template_id)
    if tpl is not None:
        if tpl.subject:
            subject = tpl.subject
        if tpl.body:
            body = tpl.body
        used_template_id = tpl.id

    return ResolvedMessage(
        subject=render_message_text(
            subject,
            first_name=first_name,
            rodo_link=rodo_link,
            controller_name=controller_name,
        ),
        body=render_message_text(
            body,
            first_name=first_name,
            rodo_link=rodo_link,
            controller_name=controller_name,
        ),
        template_id=used_template_id,
    )

