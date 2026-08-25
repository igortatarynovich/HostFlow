"""C2.1 PR-3 — Template Registry (single SoT for Intent/Channel/Capability → Template).

Durable bindings on published TemplateVersions are authoritative for catalog membership.
IntentDefinition.allowed_template_keys (when non-empty) is an additional platform gate
until seed intents fully migrate to bindings-only.

No module imports. Does not send, render, or mutate Thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.communications.intent_registry import (
    UnknownIntentRegistryError,
    get_intent_definition,
)
from backend.app.models.communication_template import (
    TEMPLATE_STATUS_ACTIVE,
    VERSION_STATUS_PUBLISHED,
    CommunicationTemplate,
    CommunicationTemplateVersion,
)

# Platform capability → channels (SoT for Capability → Template axis).
CAPABILITY_CHANNELS: dict[str, frozenset[str]] = {
    "email": frozenset({"email"}),
    "sms": frozenset({"sms"}),
    "whatsapp": frozenset({"whatsapp"}),
    "messenger": frozenset({"whatsapp", "telegram", "messenger"}),
}


@dataclass(frozen=True, slots=True)
class TemplateRegistryEntry:
    template_id: str
    template_key: str
    template_name: str
    template_version_id: str
    version_number: int
    locale: str
    channels: frozenset[str]
    intent_keys: frozenset[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_key": self.template_key,
            "template_name": self.template_name,
            "template_version_id": self.template_version_id,
            "version_number": self.version_number,
            "locale": self.locale,
            "channels": sorted(self.channels),
            "intent_keys": sorted(self.intent_keys),
        }


@dataclass(frozen=True, slots=True)
class TemplateAllowDecision:
    allowed: bool
    reason_code: str | None
    template_key: str | None
    template_version_id: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "template_key": self.template_key,
            "template_version_id": self.template_version_id,
            "message": self.message,
        }


def channels_for_capability(capability: str | None) -> frozenset[str] | None:
    """Return channels covered by a capability key, or None if capability unset."""
    if capability is None or not str(capability).strip():
        return None
    key = str(capability).strip().lower()
    if key in CAPABILITY_CHANNELS:
        return CAPABILITY_CHANNELS[key]
    # Unknown capability key: treat as literal channel name for forward-compat.
    return frozenset({key})


def _entry_from_row(
    template: CommunicationTemplate,
    version: CommunicationTemplateVersion,
) -> TemplateRegistryEntry:
    channels = frozenset(
        str(c.channel).strip().lower()
        for c in (version.channel_bindings or [])
        if c.channel
    )
    intents = frozenset(
        str(i.intent_key).strip()
        for i in (version.intent_bindings or [])
        if i.intent_key
    )
    return TemplateRegistryEntry(
        template_id=str(template.id),
        template_key=str(template.key),
        template_name=str(template.name),
        template_version_id=str(version.id),
        version_number=int(version.version_number or 0),
        locale=str(version.locale or "pl"),
        channels=channels,
        intent_keys=intents,
    )


async def _load_latest_published_by_template(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[tuple[CommunicationTemplate, CommunicationTemplateVersion]]:
    """Latest published version per active template (by version_number)."""
    stmt = (
        select(CommunicationTemplate, CommunicationTemplateVersion)
        .join(
            CommunicationTemplateVersion,
            CommunicationTemplateVersion.template_id == CommunicationTemplate.id,
        )
        .where(
            CommunicationTemplate.tenant_id == tenant_id,
            CommunicationTemplate.status == TEMPLATE_STATUS_ACTIVE,
            CommunicationTemplateVersion.tenant_id == tenant_id,
            CommunicationTemplateVersion.status == VERSION_STATUS_PUBLISHED,
        )
        .options(
            selectinload(CommunicationTemplateVersion.channel_bindings),
            selectinload(CommunicationTemplateVersion.intent_bindings),
        )
        .order_by(
            CommunicationTemplate.key.asc(),
            CommunicationTemplateVersion.version_number.desc(),
        )
    )
    rows = (await db.execute(stmt)).all()
    latest: dict[str, tuple[CommunicationTemplate, CommunicationTemplateVersion]] = {}
    for template, version in rows:
        tid = str(template.id)
        if tid not in latest:
            latest[tid] = (template, version)
    return list(latest.values())


def _intent_seed_allowlist(intent_key: str | None) -> frozenset[str] | None:
    """Non-empty IntentDefinition.allowed_template_keys, else None (no seed gate).

    Unknown intents: no seed gate — durable TemplateIntentBinding is SoT.
    """
    if not intent_key:
        return None
    try:
        definition = get_intent_definition(str(intent_key).strip())
    except UnknownIntentRegistryError:
        return None
    keys = frozenset(definition.allowed_template_keys or ())
    return keys if keys else None


def _matches_filters(
    entry: TemplateRegistryEntry,
    *,
    intent_key: str | None,
    channel: str | None,
    capability: str | None,
    seed_allow: frozenset[str] | None,
) -> bool:
    if intent_key:
        if str(intent_key).strip() not in entry.intent_keys:
            return False
    if channel:
        if str(channel).strip().lower() not in entry.channels:
            return False
    cap_channels = channels_for_capability(capability)
    if cap_channels is not None:
        if entry.channels.isdisjoint(cap_channels):
            return False
    if seed_allow is not None and entry.template_key not in seed_allow:
        return False
    return True


async def list_templates_for_intent(
    db: AsyncSession,
    *,
    tenant_id: str,
    intent_key: str,
    channel: str | None = None,
    capability: str | None = None,
) -> list[TemplateRegistryEntry]:
    seed_allow = _intent_seed_allowlist(intent_key)
    pairs = await _load_latest_published_by_template(db, tenant_id=tenant_id)
    out: list[TemplateRegistryEntry] = []
    for template, version in pairs:
        entry = _entry_from_row(template, version)
        if _matches_filters(
            entry,
            intent_key=intent_key,
            channel=channel,
            capability=capability,
            seed_allow=seed_allow,
        ):
            out.append(entry)
    return out


async def list_templates_for_channel(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    intent_key: str | None = None,
    capability: str | None = None,
) -> list[TemplateRegistryEntry]:
    seed_allow = _intent_seed_allowlist(intent_key) if intent_key else None
    pairs = await _load_latest_published_by_template(db, tenant_id=tenant_id)
    out: list[TemplateRegistryEntry] = []
    for template, version in pairs:
        entry = _entry_from_row(template, version)
        if _matches_filters(
            entry,
            intent_key=intent_key,
            channel=channel,
            capability=capability,
            seed_allow=seed_allow,
        ):
            out.append(entry)
    return out


async def list_templates_for_capability(
    db: AsyncSession,
    *,
    tenant_id: str,
    capability: str,
    intent_key: str | None = None,
    channel: str | None = None,
) -> list[TemplateRegistryEntry]:
    seed_allow = _intent_seed_allowlist(intent_key) if intent_key else None
    pairs = await _load_latest_published_by_template(db, tenant_id=tenant_id)
    out: list[TemplateRegistryEntry] = []
    for template, version in pairs:
        entry = _entry_from_row(template, version)
        if _matches_filters(
            entry,
            intent_key=intent_key,
            channel=channel,
            capability=capability,
            seed_allow=seed_allow,
        ):
            out.append(entry)
    return out


async def get_published_entry_by_key(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_key: str,
) -> TemplateRegistryEntry | None:
    key = str(template_key or "").strip().lower()
    if not key:
        return None
    pairs = await _load_latest_published_by_template(db, tenant_id=tenant_id)
    for template, version in pairs:
        if str(template.key).strip().lower() == key:
            return _entry_from_row(template, version)
    return None


async def is_template_allowed(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_key: str,
    intent_key: str,
    channel: str,
    capability: str | None = None,
) -> TemplateAllowDecision:
    """Single SoT decision: may this Intent use this Template on this Channel (/Capability)?"""
    key = str(template_key or "").strip().lower()
    intent = str(intent_key or "").strip()
    ch = str(channel or "").strip().lower()

    entry = await get_published_entry_by_key(db, tenant_id=tenant_id, template_key=key)
    if entry is None:
        return TemplateAllowDecision(
            allowed=False,
            reason_code="template_not_found_or_unpublished",
            template_key=key or None,
            template_version_id=None,
            message="No active published template for this key",
        )

    if intent not in entry.intent_keys:
        return TemplateAllowDecision(
            allowed=False,
            reason_code="intent_not_bound",
            template_key=entry.template_key,
            template_version_id=entry.template_version_id,
            message=f"Intent {intent!r} is not bound on this template version",
        )

    if ch not in entry.channels:
        return TemplateAllowDecision(
            allowed=False,
            reason_code="channel_not_bound",
            template_key=entry.template_key,
            template_version_id=entry.template_version_id,
            message=f"Channel {ch!r} is not bound on this template version",
        )

    cap_channels = channels_for_capability(capability)
    if cap_channels is not None and entry.channels.isdisjoint(cap_channels):
        return TemplateAllowDecision(
            allowed=False,
            reason_code="capability_mismatch",
            template_key=entry.template_key,
            template_version_id=entry.template_version_id,
            message=f"Capability {capability!r} does not match template channels",
        )

    seed_allow = _intent_seed_allowlist(intent)
    if seed_allow is not None and entry.template_key not in seed_allow:
        return TemplateAllowDecision(
            allowed=False,
            reason_code="intent_seed_deny",
            template_key=entry.template_key,
            template_version_id=entry.template_version_id,
            message="Template key not in IntentDefinition.allowed_template_keys",
        )

    return TemplateAllowDecision(
        allowed=True,
        reason_code=None,
        template_key=entry.template_key,
        template_version_id=entry.template_version_id,
        message="ok",
    )


__all__ = [
    "CAPABILITY_CHANNELS",
    "TemplateRegistryEntry",
    "TemplateAllowDecision",
    "channels_for_capability",
    "list_templates_for_intent",
    "list_templates_for_channel",
    "list_templates_for_capability",
    "get_published_entry_by_key",
    "is_template_allowed",
]
