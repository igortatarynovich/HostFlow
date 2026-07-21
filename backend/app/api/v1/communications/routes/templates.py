"""C2.1 PR-4 — Template Platform HTTP API (operators/tools).

No Campaign / Automation product endpoints.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.templates.diff import diff_version_payloads
from backend.app.communications.templates.errors import TemplateDomainError
from backend.app.communications.templates.lifecycle import (
    archive_template,
    create_template_with_draft,
    get_draft_version,
    get_latest_published_version,
    get_template,
    get_version,
    list_templates,
    list_versions,
    publish_draft,
    replace_draft_bindings,
    replace_draft_variables,
    update_draft_content,
)
from backend.app.communications.templates.payload import template_version_to_payload
from backend.app.communications.templates.renderer import preview as render_preview
from backend.app.communications.templates.serialize import (
    serialize_template,
    serialize_version,
)
from backend.app.db.deps import get_db_with_tenant

from .._helpers.access import _require_any_comm_feature

router = APIRouter(prefix="/templates", tags=["communications-templates"])


class VariableIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    var_type: str = Field(default="string", max_length=32)
    required: bool = True
    description: str | None = None
    default_value: str | None = None


class TemplateCreateIn(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    locale: str = "pl"
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    channels: list[str] = Field(default_factory=lambda: ["email"])
    intent_keys: list[str] = Field(default_factory=list)
    variables: list[VariableIn] = Field(default_factory=list)


class DraftUpdateIn(BaseModel):
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    locale: str | None = None
    meta: dict[str, Any] | None = None
    channels: list[str] | None = None
    intent_keys: list[str] | None = None
    variables: list[VariableIn] | None = None


class PreviewIn(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)
    channel: str = Field(default="email", min_length=1, max_length=32)
    locale: str | None = None
    version_id: str | None = Field(default=None, max_length=36)


def _http_domain_error(exc: TemplateDomainError) -> HTTPException:
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


async def _template_bundle(db: AsyncSession, tenant_id: str, template_id: str) -> dict[str, Any]:
    template = await get_template(db, tenant_id=tenant_id, template_id=template_id)
    draft = await get_draft_version(db, tenant_id=tenant_id, template_id=template_id)
    published = await get_latest_published_version(
        db, tenant_id=tenant_id, template_id=template_id
    )
    return serialize_template(template, draft=draft, latest_published=published)


@router.get("")
async def api_list_templates(
    include_archived: bool = Query(default=False),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    rows = await list_templates(
        db, tenant_id=tenant_id, include_archived=include_archived
    )
    items = []
    for tpl in rows:
        draft = await get_draft_version(db, tenant_id=tenant_id, template_id=str(tpl.id))
        published = await get_latest_published_version(
            db, tenant_id=tenant_id, template_id=str(tpl.id)
        )
        items.append(serialize_template(tpl, draft=draft, latest_published=published))
    return {"items": items}


@router.post("", status_code=status.HTTP_201_CREATED)
async def api_create_template(
    body: TemplateCreateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        template, _draft = await create_template_with_draft(
            db,
            tenant_id=tenant_id,
            key=body.key,
            name=body.name,
            description=body.description,
            locale=body.locale,
            subject=body.subject,
            body_text=body.body_text,
            body_html=body.body_html,
            channels=body.channels,
            intent_keys=body.intent_keys,
            variables=[v.model_dump() for v in body.variables],
        )
        await db.commit()
        return await _template_bundle(db, tenant_id, str(template.id))
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{template_id}")
async def api_get_template(
    template_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        return await _template_bundle(db, tenant_id, template_id)
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.patch("/{template_id}/draft")
async def api_update_draft(
    template_id: str,
    body: DraftUpdateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        draft = await get_draft_version(db, tenant_id=tenant_id, template_id=template_id)
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=draft,
            subject=body.subject,
            body_text=body.body_text,
            body_html=body.body_html,
            locale=body.locale,
            meta=body.meta,
        )
        if body.channels is not None or body.intent_keys is not None:
            await replace_draft_bindings(
                db,
                tenant_id=tenant_id,
                version=draft,
                channels=body.channels,
                intent_keys=body.intent_keys,
            )
        if body.variables is not None:
            await replace_draft_variables(
                db,
                tenant_id=tenant_id,
                version=draft,
                variables=[v.model_dump() for v in body.variables],
            )
        await db.commit()
        return await _template_bundle(db, tenant_id, template_id)
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{template_id}/publish")
async def api_publish_template(
    template_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, user = ctx
    try:
        published = await publish_draft(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            actor_user_id=str(user.sub),
        )
        await db.commit()
        bundle = await _template_bundle(db, tenant_id, template_id)
        bundle["published_version"] = serialize_version(published)
        return bundle
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{template_id}/archive")
async def api_archive_template(
    template_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await archive_template(db, tenant_id=tenant_id, template_id=template_id)
        await db.commit()
        return await _template_bundle(db, tenant_id, template_id)
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{template_id}/versions")
async def api_list_versions(
    template_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        versions = await list_versions(db, tenant_id=tenant_id, template_id=template_id)
        return {"items": [serialize_version(v) for v in versions]}
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{template_id}/versions/{version_id}")
async def api_get_version(
    template_id: str,
    version_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        version = await get_version(
            db, tenant_id=tenant_id, template_id=template_id, version_id=version_id
        )
        return serialize_version(version)
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{template_id}/diff")
async def api_diff_versions(
    template_id: str,
    from_version_id: str = Query(..., alias="from"),
    to_version_id: str = Query(..., alias="to"),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        left = await get_version(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            version_id=from_version_id,
        )
        right = await get_version(
            db,
            tenant_id=tenant_id,
            template_id=template_id,
            version_id=to_version_id,
        )
        template = await get_template(db, tenant_id=tenant_id, template_id=template_id)
        left_p = template_version_to_payload(left, template=template)
        right_p = template_version_to_payload(right, template=template)
        return diff_version_payloads(left_p, right_p)
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{template_id}/preview")
async def api_preview_template(
    template_id: str,
    body: PreviewIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        template = await get_template(db, tenant_id=tenant_id, template_id=template_id)
        if body.version_id:
            version = await get_version(
                db,
                tenant_id=tenant_id,
                template_id=template_id,
                version_id=body.version_id,
            )
        else:
            version = await get_latest_published_version(
                db, tenant_id=tenant_id, template_id=template_id
            )
            if version is None:
                version = await get_draft_version(
                    db, tenant_id=tenant_id, template_id=template_id
                )
        payload = template_version_to_payload(version, template=template)
        # Operator draft preview: API may soft-mark draft as published for the
        # pure renderer input only (does not mutate durable rows).
        if payload.status == "draft":
            payload = replace(payload, status="published")
        result = render_preview(
            payload,
            variables=body.variables,
            channel=body.channel,
            locale=body.locale,
        )
        return result.to_dict()
    except TemplateDomainError as exc:
        raise _http_domain_error(exc) from exc
