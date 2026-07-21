"""C2.3 PR-5 — Campaign Orchestrator HTTP API (operators/tools).

No Campaign UI. No provider send shortcut — runs go through orchestrator → emitter → Intent.
"""

from __future__ import annotations

from typing import Any, Literal, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.campaign.audience import (
    EntityCandidate,
    ResolveContext,
    dry_run as audience_dry_run,
)
from backend.app.communications.campaign.errors import CampaignDomainError
from backend.app.communications.campaign.lifecycle import (
    archive_campaign,
    create_campaign_with_draft,
    create_run_from_audience,
    get_campaign,
    get_draft_version,
    get_latest_published_version,
    get_run,
    get_version,
    list_campaigns,
    list_runs,
    list_versions,
    publish_draft,
    update_draft_content,
    upsert_draft_audience_definition,
)
from backend.app.communications.campaign.orchestrator import (
    cancel_campaign_run,
    execute_campaign_run,
)
from backend.app.communications.campaign.payload import version_audience_payload
from backend.app.communications.campaign.serialize import (
    serialize_campaign,
    serialize_run,
    serialize_version,
)
from backend.app.db.deps import get_db_with_tenant

from .._helpers.access import _require_any_comm_feature

router = APIRouter(prefix="/campaigns", tags=["communications-campaigns"])


class AudienceDefinitionIn(BaseModel):
    definition_type: str = Field(default="static_list", min_length=1, max_length=64)
    definition: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class CampaignCreateIn(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    intent_key: str = Field(..., min_length=1, max_length=128)
    preferred_template_key: str | None = None
    channel: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)
    audience: AudienceDefinitionIn = Field(default_factory=AudienceDefinitionIn)


class DraftUpdateIn(BaseModel):
    intent_key: str | None = None
    preferred_template_key: str | None = None
    channel: str | None = None
    plan: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    audience: AudienceDefinitionIn | None = None
    clear_preferred_template_key: bool = False
    clear_channel: bool = False


class EntityCandidateIn(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=64)
    entity_id: str = Field(..., min_length=1, max_length=36)
    address: str | None = None
    label: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class AudienceDryRunIn(BaseModel):
    version_id: str | None = Field(default=None, max_length=36)
    entities: list[EntityCandidateIn] = Field(default_factory=list)
    require_entity_pool: bool = False


class RunCreateIn(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    campaign_version_id: str | None = Field(default=None, max_length=36)
    entities: list[EntityCandidateIn] = Field(default_factory=list)
    require_entity_pool: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class RunExecuteIn(BaseModel):
    mode: Literal["request_only", "render", "execute"] = "request_only"
    skip_transport: bool = True
    mark_ready: bool = True


class RunCancelIn(BaseModel):
    reason: str | None = None


def _http_domain_error(exc: CampaignDomainError) -> HTTPException:
    code = (
        status.HTTP_404_NOT_FOUND
        if exc.code.endswith("not_found")
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(
        status_code=code,
        detail={"code": exc.code, "message": exc.message, "details": exc.details},
    )


def _entities_to_context(
    entities: list[EntityCandidateIn],
    *,
    require_entity_pool: bool = False,
) -> ResolveContext:
    return ResolveContext(
        entities=tuple(
            EntityCandidate(
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                address=e.address,
                label=e.label,
                attributes=dict(e.attributes or {}),
            )
            for e in entities
        ),
        extras={"require_entity_pool": bool(require_entity_pool)},
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


async def _campaign_bundle(
    db: AsyncSession, tenant_id: str, campaign_id: str
) -> dict[str, Any]:
    campaign = await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
    draft = await get_draft_version(db, tenant_id=tenant_id, campaign_id=campaign_id)
    published = await get_latest_published_version(
        db, tenant_id=tenant_id, campaign_id=campaign_id
    )
    return serialize_campaign(campaign, draft=draft, latest_published=published)


@router.get("")
async def api_list_campaigns(
    include_archived: bool = Query(default=False),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    rows = await list_campaigns(
        db, tenant_id=tenant_id, include_archived=include_archived
    )
    items = []
    for campaign in rows:
        draft = await get_draft_version(
            db, tenant_id=tenant_id, campaign_id=str(campaign.id)
        )
        published = await get_latest_published_version(
            db, tenant_id=tenant_id, campaign_id=str(campaign.id)
        )
        items.append(
            serialize_campaign(campaign, draft=draft, latest_published=published)
        )
    return {"items": items}


@router.post("", status_code=status.HTTP_201_CREATED)
async def api_create_campaign(
    body: CampaignCreateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        campaign, _draft = await create_campaign_with_draft(
            db,
            tenant_id=tenant_id,
            key=body.key,
            name=body.name,
            description=body.description,
            intent_key=body.intent_key,
            preferred_template_key=body.preferred_template_key,
            channel=body.channel,
            plan=body.plan,
            audience_definition_type=body.audience.definition_type,
            audience_definition=body.audience.definition,
        )
        await db.commit()
        return await _campaign_bundle(db, tenant_id, str(campaign.id))
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{campaign_id}")
async def api_get_campaign(
    campaign_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        return await _campaign_bundle(db, tenant_id, campaign_id)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.patch("/{campaign_id}/draft")
async def api_update_draft(
    campaign_id: str,
    body: DraftUpdateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        draft = await get_draft_version(db, tenant_id=tenant_id, campaign_id=campaign_id)
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=draft,
            intent_key=body.intent_key,
            preferred_template_key=body.preferred_template_key,
            channel=body.channel,
            plan=body.plan,
            meta=body.meta,
            clear_preferred_template_key=body.clear_preferred_template_key,
            clear_channel=body.clear_channel,
        )
        if body.audience is not None:
            await upsert_draft_audience_definition(
                db,
                tenant_id=tenant_id,
                version=draft,
                definition_type=body.audience.definition_type,
                definition=body.audience.definition,
                meta=body.audience.meta,
            )
        await db.commit()
        return await _campaign_bundle(db, tenant_id, campaign_id)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/publish")
async def api_publish_campaign(
    campaign_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, user = ctx
    try:
        published = await publish_draft(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            actor_user_id=str(user.sub),
        )
        await db.commit()
        bundle = await _campaign_bundle(db, tenant_id, campaign_id)
        bundle["published_version"] = serialize_version(published)
        return bundle
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/archive")
async def api_archive_campaign(
    campaign_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await archive_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
        await db.commit()
        return await _campaign_bundle(db, tenant_id, campaign_id)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{campaign_id}/versions")
async def api_list_versions(
    campaign_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        versions = await list_versions(
            db, tenant_id=tenant_id, campaign_id=campaign_id
        )
        return {"items": [serialize_version(v) for v in versions]}
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{campaign_id}/versions/{version_id}")
async def api_get_version(
    campaign_id: str,
    version_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        version = await get_version(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            version_id=version_id,
        )
        return serialize_version(version)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/audience/dry-run")
async def api_audience_dry_run(
    campaign_id: str,
    body: AudienceDryRunIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    """Resolve audience definition → snapshot candidates. Does not create a Run."""
    db, tenant_id, _user = ctx
    try:
        await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
        if body.version_id:
            version = await get_version(
                db,
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                version_id=body.version_id,
            )
        else:
            version = await get_latest_published_version(
                db, tenant_id=tenant_id, campaign_id=campaign_id
            )
            if version is None:
                version = await get_draft_version(
                    db, tenant_id=tenant_id, campaign_id=campaign_id
                )
        payload = version_audience_payload(version)
        if payload is None:
            raise CampaignDomainError(
                "audience_definition_required",
                "Version has no audience definition",
                details={"version_id": str(version.id)},
            )
        result = audience_dry_run(
            payload,
            _entities_to_context(
                body.entities, require_entity_pool=body.require_entity_pool
            ),
        )
        return {
            "ok": result.ok,
            "definition_type": result.definition_type,
            "recipients": [r.to_run_dict() for r in result.recipients],
            "skipped": [s.to_dict() for s in result.skipped],
            "diagnostics": [d.to_dict() for d in result.diagnostics],
            "fingerprint": dict(result.fingerprint),
            "version_id": str(version.id),
        }
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{campaign_id}/runs")
async def api_list_runs(
    campaign_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        rows = await list_runs(
            db, tenant_id=tenant_id, campaign_id=campaign_id, limit=limit
        )
        return {
            "items": [serialize_run(r, include_items=False) for r in rows],
        }
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/runs", status_code=status.HTTP_201_CREATED)
async def api_create_run(
    campaign_id: str,
    body: RunCreateIn,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    """Freeze audience snapshot into a Run (no Intent emission)."""
    db, tenant_id, _user = ctx
    try:
        if body.campaign_version_id:
            version_id = body.campaign_version_id
        else:
            published = await get_latest_published_version(
                db, tenant_id=tenant_id, campaign_id=campaign_id
            )
            if published is None:
                raise CampaignDomainError(
                    "version_not_published",
                    "No published CampaignVersion to run",
                    details={"campaign_id": campaign_id},
                )
            version_id = str(published.id)

        run = await create_run_from_audience(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            campaign_version_id=version_id,
            idempotency_key=body.idempotency_key,
            resolve_context=_entities_to_context(
                body.entities, require_entity_pool=body.require_entity_pool
            ),
            meta=body.meta,
        )
        await db.commit()
        # Re-load for relationships after commit.
        run = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
        return serialize_run(run)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.get("/{campaign_id}/runs/{run_id}")
async def api_get_run(
    campaign_id: str,
    run_id: str,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    try:
        await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        if str(run.campaign_id) != str(campaign_id):
            raise CampaignDomainError(
                "run_not_found",
                "CampaignRun not found for campaign",
                details={"campaign_id": campaign_id, "run_id": run_id},
            )
        return serialize_run(run)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/runs/{run_id}/execute")
async def api_execute_run(
    campaign_id: str,
    run_id: str,
    body: RunExecuteIn | None = None,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    """Drive run orchestration (default mode=request_only — no transport)."""
    db, tenant_id, _user = ctx
    payload = body or RunExecuteIn()
    try:
        await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        if str(run.campaign_id) != str(campaign_id):
            raise CampaignDomainError(
                "run_not_found",
                "CampaignRun not found for campaign",
                details={"campaign_id": campaign_id, "run_id": run_id},
            )
        result = await execute_campaign_run(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            mode=payload.mode,
            skip_transport=payload.skip_transport,
            mark_ready=payload.mark_ready,
        )
        await db.commit()
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        return {
            "orchestration": result.to_dict(),
            "run": serialize_run(run),
        }
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc


@router.post("/{campaign_id}/runs/{run_id}/cancel")
async def api_cancel_run(
    campaign_id: str,
    run_id: str,
    body: RunCancelIn | None = None,
    ctx: tuple[AsyncSession, str, UserCtx] = Depends(_tenant_ctx),
) -> dict[str, Any]:
    db, tenant_id, _user = ctx
    payload = body or RunCancelIn()
    try:
        await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
        run = await get_run(db, tenant_id=tenant_id, run_id=run_id)
        if str(run.campaign_id) != str(campaign_id):
            raise CampaignDomainError(
                "run_not_found",
                "CampaignRun not found for campaign",
                details={"campaign_id": campaign_id, "run_id": run_id},
            )
        cancelled = await cancel_campaign_run(
            db,
            tenant_id=tenant_id,
            run_id=run_id,
            reason=payload.reason,
        )
        await db.commit()
        return serialize_run(cancelled, include_items=False)
    except CampaignDomainError as exc:
        raise _http_domain_error(exc) from exc
