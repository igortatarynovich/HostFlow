"""User invite email delivery (system SMTP)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from backend.app.core.settings import settings
from backend.app.services.system_email import send_system_email

logger = logging.getLogger(__name__)


def build_invite_accept_link(token: str) -> str:
    base = (settings.frontend_url or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/invite/accept?token={token}"


def build_invite_email_body(*, token: str, expires_at: Optional[datetime]) -> str:
    link = build_invite_accept_link(token)
    exp_str = expires_at.strftime("%Y-%m-%d %H:%M") if expires_at else ""
    body = (
        "Dzień dobry,\n\n"
        "Otrzymujesz zaproszenie do dołączenia do HostFlow.\n\n"
    )
    if link:
        body += f"Link do akceptacji (ważny do {exp_str}):\n{link}\n\n"
    else:
        body += f"Token (ważny do {exp_str}): {token}\n\n"
    body += "Pozdrawiamy,\nZespół HostFlow"
    return body


async def send_user_invite_email(
    *,
    to: str,
    token: str,
    expires_at: Optional[datetime],
) -> bool:
    """Send invite email; returns False when delivery failed or was suppressed."""
    try:
        sent = await send_system_email(
            to=to,
            subject="HostFlow – zaproszenie do zespołu",
            body=build_invite_email_body(token=token, expires_at=expires_at),
        )
        if not sent:
            logger.warning("invite email not delivered to=%s", to)
        return sent
    except Exception:
        logger.exception("invite email failed to=%s", to)
        return False
