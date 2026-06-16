"""Per-tenant email sending: SMTP only for business/compliance communications."""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import decrypt_secret, encrypt_secret
from backend.app.models import TenantEmailConfig
from backend.app.services.email_delivery import is_email_delivery_mock


async def get_tenant_email_config(
    db: AsyncSession,
    tenant_id: str,
) -> Optional[TenantEmailConfig]:
    """Get active email config for tenant."""
    stmt = (
        select(TenantEmailConfig)
        .where(TenantEmailConfig.tenant_id == tenant_id)
        .where(TenantEmailConfig.is_active.is_(True))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _send_smtp_sync(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
    from_email: str,
    from_name: Optional[str],
    to: str,
    subject: str,
    body: str,
) -> None:
    """Sync SMTP send. Run in thread to avoid blocking."""
    if is_email_delivery_mock():
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))

    use_starttls = use_tls and port in (587, 25)
    conn = smtplib.SMTP(host, port)
    try:
        if use_starttls:
            conn.starttls()
        if user and password:
            conn.login(user, password)
        conn.sendmail(from_email, [to], msg.as_string())
    finally:
        conn.quit()


async def send_email_smtp(
    config: TenantEmailConfig,
    to: str,
    subject: str,
    body: str,
) -> None:
    """Send email via tenant SMTP config."""
    if is_email_delivery_mock():
        return
    password = decrypt_secret(config.smtp_password_encrypted) if config.smtp_password_encrypted else None
    if not config.smtp_host or not config.from_email:
        raise ValueError("SMTP host and from_email are required")
    port = config.smtp_port or 587
    await asyncio.to_thread(
        _send_smtp_sync,
        host=config.smtp_host,
        port=port,
        user=config.smtp_user or "",
        password=password or "",
        use_tls=config.use_tls,
        from_email=config.from_email,
        from_name=config.from_name,
        to=to,
        subject=subject,
        body=body,
    )


async def send_email_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
) -> bool:
    """
    Send email via tenant SMTP configuration only.
    Raises when tenant SMTP is missing or delivery fails.
    """
    if is_email_delivery_mock():
        return True
    config = await get_tenant_email_config(db, tenant_id)
    if not config or not config.smtp_host or not config.from_email:
        raise ValueError("TENANT_EMAIL_NOT_CONFIGURED")
    await send_email_smtp(config, to=to, subject=subject, body=body)
    return True
