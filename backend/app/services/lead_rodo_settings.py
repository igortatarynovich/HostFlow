"""Tenant settings for lead-stage RODO (art.14) automation — stored in ``Tenant.settings['lead_rodo_v1']``."""

from __future__ import annotations

from typing import Any, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant

LeadRodoSendMode = Literal["manual", "auto_on_lead_created", "auto_on_first_action"]

LEAD_RODO_SEND_MODES: frozenset[str] = frozenset(
    {"manual", "auto_on_lead_created", "auto_on_first_action"}
)
DEFAULT_LEAD_RODO_CHANNELS: tuple[str, ...] = ("email",)

_SETTINGS_KEY = "lead_rodo_v1"


class LeadRodoSettings:
    __slots__ = ("send_mode", "channels", "template_id", "message_template_id")

    def __init__(
        self,
        *,
        send_mode: LeadRodoSendMode = "auto_on_lead_created",
        channels: tuple[str, ...] = DEFAULT_LEAD_RODO_CHANNELS,
        template_id: Optional[str] = None,
        message_template_id: Optional[str] = None,
    ) -> None:
        self.send_mode = send_mode
        self.channels = channels
        self.template_id = (str(template_id).strip() or None) if template_id else None
        self.message_template_id = (str(message_template_id).strip() or None) if message_template_id else None

    def auto_on_lead_created(self) -> bool:
        return self.send_mode == "auto_on_lead_created"

    def auto_on_first_action(self) -> bool:
        return self.send_mode == "auto_on_first_action"


def _normalize_send_mode(_raw: Any) -> LeadRodoSendMode:
    """Art.14 is a platform legal floor: always auto-send on lead created."""
    return "auto_on_lead_created"


def _normalize_channels(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return DEFAULT_LEAD_RODO_CHANNELS
    out: list[str] = []
    for item in raw:
        ch = str(item or "").strip().lower()
        if ch and ch not in out:
            out.append(ch)
    return tuple(out) if out else DEFAULT_LEAD_RODO_CHANNELS


def lead_rodo_settings_from_tenant_dict(settings: Optional[dict[str, Any]]) -> LeadRodoSettings:
    if not isinstance(settings, dict):
        return LeadRodoSettings()
    raw = settings.get(_SETTINGS_KEY)
    if not isinstance(raw, dict):
        return LeadRodoSettings()
    return LeadRodoSettings(
        send_mode=_normalize_send_mode(raw.get("send_mode")),
        channels=_normalize_channels(raw.get("channels")),
        template_id=raw.get("template_id"),
        message_template_id=raw.get("message_template_id"),
    )


async def get_lead_rodo_settings(db: AsyncSession, tenant_id: str) -> LeadRodoSettings:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return LeadRodoSettings()
    st = tenant.settings if isinstance(tenant.settings, dict) else {}
    return lead_rodo_settings_from_tenant_dict(st)


async def persist_lead_rodo_settings(
    db: AsyncSession,
    tenant_id: str,
    *,
    send_mode: Optional[LeadRodoSendMode] = None,
    channels: Optional[list[str]] = None,
    template_id: Optional[str] = None,
    message_template_id: Optional[str] = None,
    clear_template_id: bool = False,
    clear_message_template_id: bool = False,
) -> LeadRodoSettings:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return LeadRodoSettings()
    st = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    cur = lead_rodo_settings_from_tenant_dict(st)
    block: dict[str, Any] = {
        "send_mode": cur.send_mode,
        "channels": list(cur.channels),
        "template_id": cur.template_id,
        "message_template_id": cur.message_template_id,
    }
    if send_mode is not None:
        block["send_mode"] = _normalize_send_mode(send_mode)
    if channels is not None:
        block["channels"] = list(_normalize_channels(channels))
    if clear_template_id:
        block["template_id"] = None
    elif template_id is not None:
        block["template_id"] = str(template_id).strip() or None
    if clear_message_template_id:
        block["message_template_id"] = None
    elif message_template_id is not None:
        block["message_template_id"] = str(message_template_id).strip() or None
    st[_SETTINGS_KEY] = block
    tenant.settings = st
    await db.flush()
    return lead_rodo_settings_from_tenant_dict(st)


def lead_rodo_settings_to_api_dict(cfg: LeadRodoSettings) -> dict[str, Any]:
    return {
        "lead_rodo_send_mode": cfg.send_mode,
        "lead_rodo_channels": list(cfg.channels),
        "lead_rodo_template_id": cfg.template_id,
        "lead_rodo_message_template_id": cfg.message_template_id,
    }


__all__ = [
    "DEFAULT_LEAD_RODO_CHANNELS",
    "LEAD_RODO_SEND_MODES",
    "LeadRodoSendMode",
    "LeadRodoSettings",
    "get_lead_rodo_settings",
    "lead_rodo_settings_from_tenant_dict",
    "lead_rodo_settings_to_api_dict",
    "persist_lead_rodo_settings",
]
