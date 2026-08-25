"""C2.2 PR-4 — Automation Engine HTTP API (operators/tools).

No Campaign / Scheduling product endpoints. No provider send shortcut.
"""

from __future__ import annotations

from typing import Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.automation.errors import AutomationDomainError
from backend.app.communications.automation.evaluator import EventPayload, evaluate
from backend.app.communications.automation.lifecycle import (
    archive_rule,
    create_rule_with_draft,
    get_draft_version,
    get_latest_published_version,
    get_rule,
    get_version,
    list_decisions,
    list_rules,
    list_versions,
    publish_draft,
    replace_draft_triggers,
    set_rule_enabled,
    update_draft_content,
)
from backend.app.communications.automation.payload import rule_version_to_payload
from backend.app.communications.automation.serialize import (
    serialize_decision,
    serialize_rule,
    serialize_version,
)
from backend.app.db.deps import get_db_with_tenant

from .._helpers.access import _require_any_comm_feature

router = APIRouter(prefix="/automation/rules", tags=["communications-automation"])


class TriggerIn(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=128)
    event_filter: dict[str, Any] = Field(default_factory=dict)


class RuleCreateIn(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    enabled: bool = True
    priority: int = 0
    intent_key: str = Field(..., min_length=1, max_length=128)
    preferred_template_key: str | None = None
    channel: str | None = None
    recipient_strategy: str = "origin_primary"
    recipient_config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] = Field(default_factory=dict)
    variables_mapping: dict[str, Any] = Field(default_factory=dict)
    triggers: list[TriggerIn] = Field(default_factory=list)


class DraftUpdateIn(BaseModel):
    intent_key: str | None = None
    preferred_template_key: str | None = None
    channel: str | None = None
    recipient_strategy: str | None = None
    recipient_config: dict[str, Any] | None = None
    conditions: dict[str, Any] | None = None
    variables_mapping: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    triggers: list[TriggerIn] | None = None
    clear_preferred_template_key: bool = False
    clear_channel: bool = False


class EnabledIn(BaseModel):
    enabled: bool


class DryRunIn(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., min_length=1, max_length=128)
    data: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    version_id: str | None = Field(default=None, max_length=36)


def _http_domain_error(exc: AutomationDomainError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if exc.code.endswith("not_found")
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(
        status_code=code,
        detail={"code": exc.code, "message": exc.message, "details": exc.details},
    )


async def _tenant_ctx(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> tuple[AsyncSession, str, UserCtx]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_any_comm_feature(
        db,
        tenant_id=tenant_id,
        current_user=current_user,
        features=["email", "messenger", "sms"],
    )
    return db, tenant_id, current_user


async def _rule_bundle(db: AsyncSession, tenant_id: str, rule_id: str) -> dict[str, Any]:
    rule = await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    draft = await get_draft_version(db, tenant_id=tenant_id, rule_id=rule_id)
    published = await get_latest_published_version(db, tenant_id=tenant_id, rule_id=rule_id)
    return serialize_rule(rule, draft=draft, latest_published=published)


@router.get("")
async def api_list_rules(
    include_archived: bool = Query(default=False),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    rows = await list_rules(db, tenant_id=tenant_id, include_archived=include_archived)
    items = []
    for rule in rows:
        draft = await get_draft_version(db, tenant_id=tenant_id, rule_id=str(rule.id))
        published = await get_latest_published_version(
            db, tenant_id=tenant_id, rule_id=str(rule.id)
        )
        items.append(serialize_rule(rule, draft=draft, latest_published=published))
    return {"items": items}


@router.post("", status_code=status.HTTP_201_CREATED)
async def api_create_rule(
    body: RuleCreateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        filters = {t.event_type: t.event_filter for t in body.triggers}
        rule, _draft = await create_rule_with_draft(
            db,
            tenant_id=tenant_id,
            key=body.key,
            name=body.name,
            description=body.description,
            enabled=body.enabled,
            priority=body.priority,
            intent_key=body.intent_key,
            preferred_template_key=body.preferred_template_key,
            channel=body.channel,
            recipient_strategy=body.recipient_strategy,
            recipient_config=body.recipient_config,
            conditions=body.conditions,
            variables_mapping=body.variables_mapping,
            event_types=[t.event_type for t in body.triggers],
            event_filters=filters,
        )
        await db.commit()
        return await _rule_bundle(db, tenant_id, str(rule.id))
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{rule_id}")
async def api_get_rule(
    rule_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        return await _rule_bundle(db, tenant_id, rule_id)
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.patch("/{rule_id}/draft")
async def api_update_draft(
    rule_id: str,
    body: DraftUpdateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        draft = await get_draft_version(db, tenant_id=tenant_id, rule_id=rule_id)
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=draft,
            intent_key=body.intent_key,
            preferred_template_key=body.preferred_template_key,
            channel=body.channel,
            recipient_strategy=body.recipient_strategy,
            recipient_config=body.recipient_config,
            conditions=body.conditions,
            variables_mapping=body.variables_mapping,
            meta=body.meta,
            clear_preferred_template_key=body.clear_preferred_template_key,
            clear_channel=body.clear_channel,
        )
        if body.triggers is not None:
            filters = {t.event_type: t.event_filter for t in body.triggers}
            await replace_draft_triggers(
                db,
                tenant_id=tenant_id,
                version=draft,
                event_types=[t.event_type for t in body.triggers],
                event_filters=filters,
            )
        await db.commit()
        return await _rule_bundle(db, tenant_id, rule_id)
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{rule_id}/publish")
async def api_publish_rule(
    rule_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, user = ctx
    try:
        published = await publish_draft(
            db,
            tenant_id=tenant_id,
            rule_id=rule_id,
            actor_user_id=str(user.sub),
        )
        await db.commit()
        bundle = await _rule_bundle(db, tenant_id, rule_id)
        bundle["published_version"] = serialize_version(published)
        return bundle
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{rule_id}/enabled")
async def api_set_enabled(
    rule_id: str,
    body: EnabledIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await set_rule_enabled(
            db, tenant_id=tenant_id, rule_id=rule_id, enabled=body.enabled
        )
        await db.commit()
        return await _rule_bundle(db, tenant_id, rule_id)
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{rule_id}/archive")
async def api_archive_rule(
    rule_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await archive_rule(db, tenant_id=tenant_id, rule_id=rule_id)
        await db.commit()
        return await _rule_bundle(db, tenant_id, rule_id)
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{rule_id}/versions")
async def api_list_versions(
    rule_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        versions = await list_versions(db, tenant_id=tenant_id, rule_id=rule_id)
        return {"items": [serialize_version(v) for v in versions]}
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{rule_id}/versions/{version_id}")
async def api_get_version(
    rule_id: str,
    version_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        version = await get_version(
            db, tenant_id=tenant_id, rule_id=rule_id, version_id=version_id
        )
        return serialize_version(version)
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{rule_id}/dry-run")
async def api_dry_run(
    rule_id: str,
    body: DryRunIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    """Operator dry-run via pure evaluator. Does not emit Intent or persist decision."""
    db, tenant_id, _user = ctx
    try:
        rule = await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
        if body.version_id:
            version = await get_version(
                db,
                tenant_id=tenant_id,
                rule_id=rule_id,
                version_id=body.version_id,
            )
        else:
            version = await get_latest_published_version(
                db, tenant_id=tenant_id, rule_id=rule_id
            )
            if version is None:
                version = await get_draft_version(
                    db, tenant_id=tenant_id, rule_id=rule_id
                )
        from dataclasses import replace

        payload = rule_version_to_payload(version, rule=rule)
        # Operator draft dry-run: soft-mark as published for evaluator only.
        if payload.version_status == "draft":
            payload = replace(payload, version_status="published")
        result = evaluate(
            payload,
            EventPayload(
                event_id=body.event_id,
                event_type=body.event_type,
                data=body.data,
                correlation_id=body.correlation_id,
            ),
        )
        return result.to_dict()
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{rule_id}/decisions")
async def api_list_rule_decisions(
    rule_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
        rows = await list_decisions(
            db, tenant_id=tenant_id, rule_id=rule_id, limit=limit
        )
        return {"items": [serialize_decision(d) for d in rows]}
    except AutomationDomainError as exc:
        raise _http_domain_error(exc) from exc
