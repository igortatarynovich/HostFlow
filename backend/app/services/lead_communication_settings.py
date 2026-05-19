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
    )

    def __init__(
        self,
        *,
        enabled: bool = False,
        send_application_received: bool = False,
        send_rejection_notice: bool = False,
        send_moving_forward_notice: bool = False,
    ) -> None:
        self.enabled = bool(enabled)
        self.send_application_received = bool(send_application_received)
        self.send_rejection_notice = bool(send_rejection_notice)
        self.send_moving_forward_notice = bool(send_moving_forward_notice)


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
    }
    if enabled is not None:
        block["enabled"] = bool(enabled)
    if send_application_received is not None:
        block["send_application_received"] = bool(send_application_received)
    if send_rejection_notice is not None:
        block["send_rejection_notice"] = bool(send_rejection_notice)
    if send_moving_forward_notice is not None:
        block["send_moving_forward_notice"] = bool(send_moving_forward_notice)
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
    }


__all__ = [
    "LeadCommunicationSettings",
    "get_lead_communication_settings",
    "lead_communication_settings_from_tenant_dict",
    "lead_communication_settings_to_api_dict",
    "persist_lead_communication_settings",
]
