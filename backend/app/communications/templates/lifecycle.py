"""C2.1 PR-1 — Template draft/publish lifecycle (no HTTP, no render, no Campaign)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.communications.templates.errors import TemplateDomainError
from backend.app.models.communication_template import (
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_ARCHIVED,
    VARIABLE_TYPES,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationTemplate,
    CommunicationTemplateChannelBinding,
    CommunicationTemplateIntentBinding,
    CommunicationTemplateVariable,
    CommunicationTemplateVersion,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_key(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key or len(key) > 128:
        raise TemplateDomainError("invalid_template_key", "template key is required (≤128)")
    return key


def _norm_channel(raw: str) -> str:
    ch = str(raw or "").strip().lower()
    if not ch:
        raise TemplateDomainError("invalid_channel", "channel is required")
    return ch


def _norm_intent(raw: str) -> str:
    intent = str(raw or "").strip()
    if not intent:
        raise TemplateDomainError("invalid_intent_key", "intent_key is required")
    return intent


def _norm_var_type(raw: str) -> str:
    t = str(raw or "string").strip().lower() or "string"
    if t not in VARIABLE_TYPES:
        raise TemplateDomainError(
            "invalid_variable_type",
            f"Unknown variable type: {raw}",
            details={"allowed": sorted(VARIABLE_TYPES)},
        )
    return t


def _assert_draft(version: CommunicationTemplateVersion) -> None:
    if not version.is_draft:
        raise TemplateDomainError(
            "version_not_draft",
            "Only draft TemplateVersion is editable",
            details={"version_id": str(version.id), "status": version.status},
        )


def _assert_not_published_mutation(version: CommunicationTemplateVersion) -> None:
    if version.is_published:
        raise TemplateDomainError(
            "published_immutable",
            "Published TemplateVersion is immutable",
            details={"version_id": str(version.id)},
        )


async def create_template_with_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    key: str,
    name: str,
    description: str | None = None,
    locale: str = "pl",
    subject: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    channels: Sequence[str] = ("email",),
    intent_keys: Sequence[str] = (),
    variables: Sequence[dict[str, Any]] = (),
) -> tuple[CommunicationTemplate, CommunicationTemplateVersion]:
    """Create Template + initial draft version (version_number=0)."""
    tid = str(tenant_id or "").strip()
    if not tid:
        raise TemplateDomainError("tenant_required", "tenant_id is required")
    tpl_key = _norm_key(key)
    tpl_name = str(name or "").strip() or tpl_key

    exists = (
        await db.execute(
            select(CommunicationTemplate.id).where(
                CommunicationTemplate.tenant_id == tid,
                CommunicationTemplate.key == tpl_key,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise TemplateDomainError(
            "template_key_exists",
            f"Template key already exists: {tpl_key}",
            details={"key": tpl_key},
        )

    template = CommunicationTemplate(
        id=str(uuid4()),
        tenant_id=tid,
        key=tpl_key,
        name=tpl_name,
        description=(str(description).strip() if description else None),
        status=TEMPLATE_STATUS_ACTIVE,
    )
    draft = CommunicationTemplateVersion(
        id=str(uuid4()),
        tenant_id=tid,
        template_id=template.id,
        version_number=0,
        status=VERSION_STATUS_DRAFT,
        locale=str(locale or "pl").strip().lower()[:16] or "pl",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        meta={},
    )
    db.add(template)
    db.add(draft)
    await db.flush()

    await replace_draft_bindings(
        db,
        tenant_id=tid,
        version=draft,
        channels=channels,
        intent_keys=intent_keys,
    )
    if variables:
        await replace_draft_variables(db, tenant_id=tid, version=draft, variables=variables)

    await db.flush()
    await db.refresh(draft)
    return template, draft


async def get_draft_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_id: str,
) -> CommunicationTemplateVersion:
    row = (
        await db.execute(
            select(CommunicationTemplateVersion)
            .options(
                selectinload(CommunicationTemplateVersion.variables),
                selectinload(CommunicationTemplateVersion.channel_bindings),
                selectinload(CommunicationTemplateVersion.intent_bindings),
            )
            .where(
                CommunicationTemplateVersion.tenant_id == tenant_id,
                CommunicationTemplateVersion.template_id == template_id,
                CommunicationTemplateVersion.status == VERSION_STATUS_DRAFT,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise TemplateDomainError(
            "draft_not_found",
            "Draft TemplateVersion not found",
            details={"template_id": template_id},
        )
    return row


async def update_draft_content(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationTemplateVersion,
    subject: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    locale: str | None = None,
    meta: dict[str, Any] | None = None,
) -> CommunicationTemplateVersion:
    if str(version.tenant_id) != str(tenant_id):
        raise TemplateDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    if subject is not None:
        version.subject = subject
    if body_text is not None:
        version.body_text = body_text
    if body_html is not None:
        version.body_html = body_html
    if locale is not None:
        version.locale = str(locale).strip().lower()[:16] or version.locale
    if meta is not None:
        version.meta = dict(meta)
    await db.flush()
    return version


async def replace_draft_variables(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationTemplateVersion,
    variables: Sequence[dict[str, Any]],
) -> list[CommunicationTemplateVariable]:
    if str(version.tenant_id) != str(tenant_id):
        raise TemplateDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    await db.execute(
        delete(CommunicationTemplateVariable).where(
            CommunicationTemplateVariable.version_id == str(version.id)
        )
    )
    await db.flush()

    created: list[CommunicationTemplateVariable] = []
    seen: set[str] = set()
    for raw in variables:
        name = str((raw or {}).get("name") or "").strip()
        if not name:
            raise TemplateDomainError("invalid_variable", "variable name is required")
        if name in seen:
            raise TemplateDomainError(
                "duplicate_variable",
                f"Duplicate variable: {name}",
                details={"name": name},
            )
        seen.add(name)
        row = CommunicationTemplateVariable(
            id=str(uuid4()),
            version_id=str(version.id),
            name=name,
            var_type=_norm_var_type(str((raw or {}).get("var_type") or "string")),
            required=bool((raw or {}).get("required", True)),
            description=(
                str((raw or {}).get("description")).strip()
                if (raw or {}).get("description") is not None
                else None
            ),
            default_value=(
                None
                if (raw or {}).get("default_value") is None
                else str((raw or {}).get("default_value"))
            ),
        )
        db.add(row)
        created.append(row)
    await db.flush()
    return created


async def replace_draft_bindings(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationTemplateVersion,
    channels: Sequence[str] | None = None,
    intent_keys: Sequence[str] | None = None,
) -> None:
    if str(version.tenant_id) != str(tenant_id):
        raise TemplateDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    if channels is not None:
        await db.execute(
            delete(CommunicationTemplateChannelBinding).where(
                CommunicationTemplateChannelBinding.version_id == str(version.id)
            )
        )
        await db.flush()
        seen_ch: set[str] = set()
        for ch in channels:
            norm = _norm_channel(ch)
            if norm in seen_ch:
                continue
            seen_ch.add(norm)
            db.add(
                CommunicationTemplateChannelBinding(
                    id=str(uuid4()),
                    version_id=str(version.id),
                    channel=norm,
                )
            )

    if intent_keys is not None:
        await db.execute(
            delete(CommunicationTemplateIntentBinding).where(
                CommunicationTemplateIntentBinding.version_id == str(version.id)
            )
        )
        await db.flush()
        seen_i: set[str] = set()
        for intent in intent_keys:
            norm = _norm_intent(intent)
            if norm in seen_i:
                continue
            seen_i.add(norm)
            db.add(
                CommunicationTemplateIntentBinding(
                    id=str(uuid4()),
                    version_id=str(version.id),
                    intent_key=norm,
                )
            )
    await db.flush()


def _clone_children_to_version(
    *,
    source: CommunicationTemplateVersion,
    target_id: str,
) -> tuple[
    list[CommunicationTemplateVariable],
    list[CommunicationTemplateChannelBinding],
    list[CommunicationTemplateIntentBinding],
]:
    vars_ = [
        CommunicationTemplateVariable(
            id=str(uuid4()),
            version_id=target_id,
            name=v.name,
            var_type=v.var_type,
            required=bool(v.required),
            description=v.description,
            default_value=v.default_value,
        )
        for v in (source.variables or [])
    ]
    channels = [
        CommunicationTemplateChannelBinding(
            id=str(uuid4()),
            version_id=target_id,
            channel=c.channel,
        )
        for c in (source.channel_bindings or [])
    ]
    intents = [
        CommunicationTemplateIntentBinding(
            id=str(uuid4()),
            version_id=target_id,
            intent_key=i.intent_key,
        )
        for i in (source.intent_bindings or [])
    ]
    return vars_, channels, intents


async def publish_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_id: str,
    actor_user_id: str | None = None,
) -> CommunicationTemplateVersion:
    """Publish creates a new immutable TemplateVersion from the current draft.

    Draft remains editable. Published versions are never mutated in place.
    Returns the new published version (``template_version_id`` for Command/Snapshot).
    """
    draft = await get_draft_version(db, tenant_id=tenant_id, template_id=template_id)
    _assert_draft(draft)

    max_published = (
        await db.execute(
            select(func.coalesce(func.max(CommunicationTemplateVersion.version_number), 0)).where(
                CommunicationTemplateVersion.tenant_id == tenant_id,
                CommunicationTemplateVersion.template_id == template_id,
                CommunicationTemplateVersion.status == VERSION_STATUS_PUBLISHED,
            )
        )
    ).scalar_one()
    next_number = int(max_published or 0) + 1

    published_id = str(uuid4())
    published = CommunicationTemplateVersion(
        id=published_id,
        tenant_id=tenant_id,
        template_id=template_id,
        version_number=next_number,
        status=VERSION_STATUS_PUBLISHED,
        locale=draft.locale,
        subject=draft.subject,
        body_text=draft.body_text,
        body_html=draft.body_html,
        meta=dict(draft.meta or {}),
        published_at=_now(),
        published_by=(str(actor_user_id).strip() if actor_user_id else None),
    )
    db.add(published)
    vars_, channels, intents = _clone_children_to_version(source=draft, target_id=published_id)
    for row in (*vars_, *channels, *intents):
        db.add(row)
    await db.flush()
    await db.refresh(published)
    return published


async def archive_template(
    db: AsyncSession,
    *,
    tenant_id: str,
    template_id: str,
) -> CommunicationTemplate:
    tpl = (
        await db.execute(
            select(CommunicationTemplate).where(
                CommunicationTemplate.tenant_id == tenant_id,
                CommunicationTemplate.id == template_id,
            )
        )
    ).scalar_one_or_none()
    if tpl is None:
        raise TemplateDomainError(
            "template_not_found",
            "Template not found",
            details={"template_id": template_id},
        )
    tpl.status = TEMPLATE_STATUS_ARCHIVED
    await db.flush()
    return tpl


def assert_version_immutable_for_write(version: CommunicationTemplateVersion) -> None:
    """Public guard for future writers (renderer must not mutate published rows)."""
    _assert_not_published_mutation(version)


__all__ = [
    "create_template_with_draft",
    "get_draft_version",
    "update_draft_content",
    "replace_draft_variables",
    "replace_draft_bindings",
    "publish_draft",
    "archive_template",
    "assert_version_immutable_for_write",
]
