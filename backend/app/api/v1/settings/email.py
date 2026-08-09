"""Email (SMTP) settings API. Per-tenant configuration."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.core.crypto import encrypt_secret
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import TenantEmailConfig
from backend.app.services.tenant_email import get_tenant_email_config, send_email_smtp

router = APIRouter(prefix="/email", tags=["settings-email"], redirect_slashes=False)


class EmailConfigOut(BaseModel):
    id: str
    tenant_id: str
    provider: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    from_email: str
    from_name: Optional[str] = None
    use_tls: bool
    is_active: bool
    has_password: bool = False


class EmailConfigUpdate(BaseModel):
    smtp_host: Optional[str] = Field(None, max_length=256)
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = Field(None, max_length=256)
    smtp_password: Optional[str] = Field(None, max_length=512)
    from_email: EmailStr
    from_name: Optional[str] = Field(None, max_length=128)
    use_tls: bool = True
    is_active: bool = True


class EmailTestRequest(BaseModel):
    to: EmailStr = Field(..., description="Email address to send test to")


@router.get("", response_model=Optional[EmailConfigOut])
async def get_email_config(
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
    __: None = Depends(require_trust_admin()),
):
    """Get email (SMTP) configuration for current tenant."""
    db, tenant_id = db_tenant
    config = await get_tenant_email_config(db, str(tenant_id))
    if not config:
        return None
    return EmailConfigOut(
        id=config.id,
        tenant_id=config.tenant_id,
        provider=config.provider,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        from_email=config.from_email,
        from_name=config.from_name,
        use_tls=config.use_tls,
        is_active=config.is_active,
        has_password=bool(config.smtp_password_encrypted),
    )


@router.put("", response_model=EmailConfigOut)
async def upsert_email_config(
    payload: EmailConfigUpdate,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
    __: None = Depends(require_trust_admin()),
):
    """Create or update email (SMTP) configuration."""
    import uuid

    db, tenant_id = db_tenant
    tid = str(tenant_id)
    stmt = select(TenantEmailConfig).where(TenantEmailConfig.tenant_id == tid)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.smtp_host = payload.smtp_host if payload.smtp_host is not None else config.smtp_host
        config.smtp_port = payload.smtp_port if payload.smtp_port is not None else config.smtp_port
        config.smtp_user = payload.smtp_user if payload.smtp_user is not None else config.smtp_user
        if payload.smtp_password is not None:
            config.smtp_password_encrypted = encrypt_secret(payload.smtp_password)
        config.from_email = payload.from_email
        config.from_name = payload.from_name
        config.use_tls = payload.use_tls
        config.is_active = payload.is_active
    else:
        config = TenantEmailConfig(
            id=str(uuid.uuid4()),
            tenant_id=tid,
            provider="smtp",
            smtp_host=payload.smtp_host or "",
            smtp_port=payload.smtp_port or 587,
            smtp_user=payload.smtp_user,
            smtp_password_encrypted=encrypt_secret(payload.smtp_password) if payload.smtp_password else None,
            from_email=payload.from_email,
            from_name=payload.from_name,
            use_tls=payload.use_tls,
            is_active=payload.is_active,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return EmailConfigOut(
        id=config.id,
        tenant_id=config.tenant_id,
        provider=config.provider,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_user=config.smtp_user,
        from_email=config.from_email,
        from_name=config.from_name,
        use_tls=config.use_tls,
        is_active=config.is_active,
        has_password=bool(config.smtp_password_encrypted),
    )


@router.post("/test")
async def send_test_email(
    payload: EmailTestRequest,
    db_tenant=Depends(get_db_with_tenant),
    _: UserCtx = Depends(get_current_user),
    __: None = Depends(require_trust_admin()),
):
    """Send a test email to verify SMTP configuration."""
    db, tenant_id = db_tenant
    config = await get_tenant_email_config(db, str(tenant_id))
    if not config or not config.smtp_host:
        raise HTTPException(
            status_code=400,
            detail="Email not configured. Please set up SMTP first.",
        )
    try:
        await send_email_smtp(
            config,
            to=payload.to,
            subject="HostFlow – test email",
            body="This is a test email from HostFlow. If you received it, your SMTP settings are working correctly.",
        )
    except Exception as e:
        logger.exception("Email test failed: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send email: {str(e)}",
        ) from e
    return {"ok": True, "message": "Test email sent"}
