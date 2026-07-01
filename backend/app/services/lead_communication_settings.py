"""Tenant settings for operational lead emails — ``Tenant.settings['lead_communication_v1']``."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant

_SETTINGS_KEY = "lead_communication_v1"


class LeadCommunicationSettings:
    __slots__ = (
        "enabled",
        "send_application_received",
        "send_rejection_notice",
        "send_moving_forward_notice",
        "application_received_subject",
        "application_received_body",
        "rejection_notice_subject",
        "rejection_notice_body",
        "moving_forward_subject",
        "moving_forward_body",
        "application_received_template_id",
        "rejection_notice_template_id",
        "moving_forward_template_id",
    )

    def __init__(
        self,
        *,
        enabled: bool = False,
        send_application_received: bool = False,
        send_rejection_notice: bool = False,
        send_moving_forward_notice: bool = False,
        application_received_subject: Optional[str] = None,
        application_received_body: Optional[str] = None,
        rejection_notice_subject: Optional[str] = None,
        rejection_notice_body: Optional[str] = None,
        moving_forward_subject: Optional[str] = None,
        moving_forward_body: Optional[str] = None,
        application_received_template_id: Optional[str] = None,
        rejection_notice_template_id: Optional[str] = None,
        moving_forward_template_id: Optional[str] = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.send_application_received = bool(send_application_received)
        self.send_rejection_notice = bool(send_rejection_notice)
        self.send_moving_forward_notice = bool(send_moving_forward_notice)
        self.application_received_subject = str(application_received_subject).strip() if application_received_subject else None
        self.application_received_body = str(application_received_body).strip() if application_received_body else None
        self.rejection_notice_subject = str(rejection_notice_subject).strip() if rejection_notice_subject else None
        self.rejection_notice_body = str(rejection_notice_body).strip() if rejection_notice_body else None
        self.moving_forward_subject = str(moving_forward_subject).strip() if moving_forward_subject else None
        self.moving_forward_body = str(moving_forward_body).strip() if moving_forward_body else None
        self.application_received_template_id = (
            str(application_received_template_id).strip() if application_received_template_id else None
        )
        self.rejection_notice_template_id = (
            str(rejection_notice_template_id).strip() if rejection_notice_template_id else None
        )
        self.moving_forward_template_id = str(moving_forward_template_id).strip() if moving_forward_template_id else None


def _as_bool(raw: Any, default: bool = False) -> bool:
    if raw is True:
        return True
    if raw is False:
        return False
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "yes", "on")
    return default


def lead_communication_settings_from_tenant_dict(
    settings: Optional[dict[str, Any]],
) -> LeadCommunicationSettings:
    if not isinstance(settings, dict):
        return LeadCommunicationSettings()
    raw = settings.get(_SETTINGS_KEY)
    if not isinstance(raw, dict):
        return LeadCommunicationSettings()
    return LeadCommunicationSettings(
        enabled=_as_bool(raw.get("enabled")),
        send_application_received=_as_bool(raw.get("send_application_received")),
        send_rejection_notice=_as_bool(raw.get("send_rejection_notice")),
        send_moving_forward_notice=_as_bool(raw.get("send_moving_forward_notice")),
        application_received_subject=raw.get("application_received_subject"),
        application_received_body=raw.get("application_received_body"),
        rejection_notice_subject=raw.get("rejection_notice_subject"),
        rejection_notice_body=raw.get("rejection_notice_body"),
        moving_forward_subject=raw.get("moving_forward_subject"),
        moving_forward_body=raw.get("moving_forward_body"),
        application_received_template_id=raw.get("application_received_template_id"),
        rejection_notice_template_id=raw.get("rejection_notice_template_id"),
        moving_forward_template_id=raw.get("moving_forward_template_id"),
    )


async def get_lead_communication_settings(db: AsyncSession, tenant_id: str) -> LeadCommunicationSettings:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return LeadCommunicationSettings()
    st = tenant.settings if isinstance(tenant.settings, dict) else {}
    return lead_communication_settings_from_tenant_dict(st)


async def persist_lead_communication_settings(
    db: AsyncSession,
    tenant_id: str,
    *,
    enabled: Optional[bool] = None,
    send_application_received: Optional[bool] = None,
    send_rejection_notice: Optional[bool] = None,
    send_moving_forward_notice: Optional[bool] = None,
    application_received_subject: Optional[str] = None,
    application_received_body: Optional[str] = None,
    rejection_notice_subject: Optional[str] = None,
    rejection_notice_body: Optional[str] = None,
    moving_forward_subject: Optional[str] = None,
    moving_forward_body: Optional[str] = None,
    application_received_template_id: Optional[str] = None,
    rejection_notice_template_id: Optional[str] = None,
    moving_forward_template_id: Optional[str] = None,
) -> LeadCommunicationSettings:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return LeadCommunicationSettings()
    st = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    cur = lead_communication_settings_from_tenant_dict(st)
    block: dict[str, Any] = {
        "enabled": cur.enabled,
        "send_application_received": cur.send_application_received,
        "send_rejection_notice": cur.send_rejection_notice,
        "send_moving_forward_notice": cur.send_moving_forward_notice,
        "application_received_subject": cur.application_received_subject,
        "application_received_body": cur.application_received_body,
        "rejection_notice_subject": cur.rejection_notice_subject,
        "rejection_notice_body": cur.rejection_notice_body,
        "moving_forward_subject": cur.moving_forward_subject,
        "moving_forward_body": cur.moving_forward_body,
        "application_received_template_id": cur.application_received_template_id,
        "rejection_notice_template_id": cur.rejection_notice_template_id,
        "moving_forward_template_id": cur.moving_forward_template_id,
    }
    if enabled is not None:
        block["enabled"] = bool(enabled)
    if send_application_received is not None:
        block["send_application_received"] = bool(send_application_received)
    if send_rejection_notice is not None:
        block["send_rejection_notice"] = bool(send_rejection_notice)
    if send_moving_forward_notice is not None:
        block["send_moving_forward_notice"] = bool(send_moving_forward_notice)
    if application_received_subject is not None:
        block["application_received_subject"] = str(application_received_subject).strip() or None
    if application_received_body is not None:
        block["application_received_body"] = str(application_received_body).strip() or None
    if rejection_notice_subject is not None:
        block["rejection_notice_subject"] = str(rejection_notice_subject).strip() or None
    if rejection_notice_body is not None:
        block["rejection_notice_body"] = str(rejection_notice_body).strip() or None
    if moving_forward_subject is not None:
        block["moving_forward_subject"] = str(moving_forward_subject).strip() or None
    if moving_forward_body is not None:
        block["moving_forward_body"] = str(moving_forward_body).strip() or None
    if application_received_template_id is not None:
        block["application_received_template_id"] = str(application_received_template_id).strip() or None
    if rejection_notice_template_id is not None:
        block["rejection_notice_template_id"] = str(rejection_notice_template_id).strip() or None
    if moving_forward_template_id is not None:
        block["moving_forward_template_id"] = str(moving_forward_template_id).strip() or None
    st[_SETTINGS_KEY] = block
    tenant.settings = st
    await db.flush()
    return lead_communication_settings_from_tenant_dict(st)


def lead_communication_settings_to_api_dict(cfg: LeadCommunicationSettings) -> dict[str, Any]:
    return {
        "lead_communication_enabled": cfg.enabled,
        "send_application_received": cfg.send_application_received,
        "send_rejection_notice": cfg.send_rejection_notice,
        "send_moving_forward_notice": cfg.send_moving_forward_notice,
        "application_received_subject": cfg.application_received_subject,
        "application_received_body": cfg.application_received_body,
        "rejection_notice_subject": cfg.rejection_notice_subject,
        "rejection_notice_body": cfg.rejection_notice_body,
        "moving_forward_subject": cfg.moving_forward_subject,
        "moving_forward_body": cfg.moving_forward_body,
        "application_received_template_id": cfg.application_received_template_id,
        "rejection_notice_template_id": cfg.rejection_notice_template_id,
        "moving_forward_template_id": cfg.moving_forward_template_id,
    }


__all__ = [
    "LeadCommunicationSettings",
    "get_lead_communication_settings",
    "lead_communication_settings_from_tenant_dict",
    "lead_communication_settings_to_api_dict",
    "persist_lead_communication_settings",
]
