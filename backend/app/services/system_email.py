"""System email (info@hostflow.cc): password reset, invites, platform notifications."""

from __future__ import annotations

from typing import Optional

from backend.app.core.settings import settings
from backend.app.services.tenant_email import _send_smtp_sync
from backend.app.services import notifications as outbound
import asyncio


def _get_system_smtp_config() -> Optional[dict]:
    """Return system SMTP config from env, or None if not configured."""
    host = (settings.system_smtp_host or "").strip()
    from_email = (settings.system_from_email or "").strip()
    if not host or not from_email:
        return None
    return {
        "host": host,
        "port": settings.system_smtp_port or 587,
        "user": (settings.system_smtp_user or "").strip(),
        "password": (settings.system_smtp_password or "").strip(),
        "from_email": from_email,
        "from_name": (settings.system_from_name or "HostFlow").strip(),
    }


async def send_system_email(
    to: str,
    subject: str,
    body: str,
) -> bool:
    """
    Send email from platform (info@hostflow.cc).
    Uses SYSTEM_SMTP_* env vars. Falls back to webhook if SMTP not configured.
    """
    to = (to or "").strip()
    if not to or "@" not in to:
        return False

    config = _get_system_smtp_config()
    if config:
        try:
            await asyncio.to_thread(
                _send_smtp_sync,
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                use_tls=True,
                from_email=config["from_email"],
                from_name=config["from_name"] or None,
                to=to,
                subject=subject,
                body=body,
            )
            return True
        except Exception:
            pass

    await outbound.notify(to=to, subject=subject, text=body)
    return True
