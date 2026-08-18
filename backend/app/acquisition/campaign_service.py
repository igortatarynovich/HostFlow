"""Campaign foundation service — Stage 3A (ADR-024) + Stage 4 PR-2 hardening."""

from __future__ import annotations

from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import HTTPException

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.acquisition.activity.repository import get_by_source_event_id
from backend.app.acquisition.flights.lifecycle import create_flight
from backend.app.acquisition.target_resolver import assert_promotion_target_accessible
from backend.app.acquisition.validation import (
    CampaignValidationError,
    ValidatedTarget,
    validate_goal_kpi_pair,
    validate_promotion_target,
)
from backend.app.auth.module_gate import enforce_module_gate
from backend.app.auth.deps import UserCtx
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    ACTOR_TYPE_USER,
    AcquisitionActivityEvent,
)
from backend.app.models.campaign import Campaign, CampaignRun, CampaignTarget
from backend.app.models.own_company import OwnCompany

_CAMPAIGN_COMPLETE_FROM = frozenset({"draft", "active", "paused"})
_CAMPAIGN_ARCHIVE_FROM = frozenset({"draft", "active", "paused", "completed"})


def campaign_created_source_event_id(campaign_id: str) -> str:
    return f"acq.campaign.created:{campaign_id}"


def campaign_command_source_event_id(campaign_id: str, command: str) -> str:
    return f"acq.campaign.command:{campaign_id}:{command}"


async def _emit_campaign_event(
    db: AsyncSession,
    *,
    campaign: Campaign,
    event_type: str,
    source_event_id: str,
    actor_type: str,
    actor_id: str | None,
    note: str | None = None,
    flight_id: str | None = None,
) -> AcquisitionActivityEvent:
    contract = get_activity_event_contract(event_type)
    if contract is None:
        raise CampaignServiceError(f"unknown campaign event_type: {event_type!r}", status_code=500)
    payload: dict[str, Any] = {}
    if note is not None and str(note).strip():
        payload["note"] = str(note).strip()
    return await append_activity_event(
        db,
        tenant_id=str(campaign.tenant_id),
        campaign_id=str(campaign.id),
        flight_id=flight_id or (str(campaign.current_flight_id) if campaign.current_flight_id else None),
        event_type=event_type,
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=source_event_id,
        provider=None,
    )


class CampaignServiceError(Exception):
    def __init__(self, detail: str, *, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _from_validation(exc: CampaignValidationError) -> CampaignServiceError:
    return CampaignServiceError(exc.detail, status_code=exc.status_code)


async def _ensure_own_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> None:
    row = await db.execute(
        select(OwnCompany.id).where(
            OwnCompany.id == own_company_id,
            OwnCompany.tenant_id == tenant_id,
            OwnCompany.is_archived.is_(False),
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignServiceError("own_company_id not found for tenant", status_code=404)


async def _gate_destination_modules(
    db: AsyncSession,
    *,
    tenant_id: str,
    ctx: UserCtx,
    modules: Sequence[str],
    action: str = "write",
) -> None:
    seen: set[str] = set()
    for module in modules:
        key = str(module or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            await enforce_module_gate(
                db=db,
                tenant_id=tenant_id,
                ctx=ctx,
                module_key=key,
                action=action,  # type: ignore[arg-type]
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
            raise CampaignServiceError(detail, status_code=exc.status_code) from exc


async def _validate_and_resolve_targets(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    ctx: UserCtx,
    targets: Sequence[dict[str, Any]] | None,
) -> list[ValidatedTarget]:
    validated: list[ValidatedTarget] = []
    for raw in targets or []:
        try:
            vt = validate_promotion_target(
                target_type=str(raw.get("target_type") or ""),
                target_id=str(raw.get("target_id") or ""),
                route_intent=str(raw.get("route_intent") or ""),
                role=str(raw.get("role") or "primary"),
                sort_order=int(raw.get("sort_order") or 0),
                client_target_module=raw.get("target_module"),
            )
            await assert_promotion_target_accessible(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                target_type=vt.target_type,
                target_id=vt.target_id,
            )
        except CampaignValidationError as exc:
            raise _from_validation(exc) from exc
        validated.append(vt)

    if validated:
        await _gate_destination_modules(
            db,
            tenant_id=tenant_id,
            ctx=ctx,
            # Context (e.g. client_account on a hiring campaign) is a reference, not a
            # destination-module write. Sales must not be required to recruit for a client.
            modules=[t.target_module for t in validated if t.role == "primary"],
            action="write",
        )
    return validated


def _campaign_options():
    return (
        selectinload(Campaign.targets),
        selectinload(Campaign.flights).selectinload(CampaignRun.form_links),
        selectinload(Campaign.flights).selectinload(CampaignRun.intake_source_links),
        selectinload(Campaign.flights).selectinload(CampaignRun.ad_links),
    )


async def _reload_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None = None,
) -> Campaign:
    """Re-fetch with populate_existing so collections reflect post-flush writes."""
    stmt = (
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .options(*_campaign_options())
        .execution_options(populate_existing=True)
    )
    if own_company_id:
        stmt = stmt.where(Campaign.own_company_id == own_company_id)
    row = await db.execute(stmt)
    campaign = row.scalar_one_or_none()
    if campaign is None:
        raise CampaignServiceError("Campaign not found", status_code=404)
    return campaign


async def create_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    ctx: UserCtx,
    own_company_id: str,
    name: str,
    goal_type: str,
    primary_kpi: str,
    description: str | None = None,
    targets: Sequence[dict[str, Any]] | None = None,
) -> Campaign:
    name_n = str(name or "").strip()
    if not name_n:
        raise CampaignServiceError("name is required", status_code=422)

    try:
        gt, pk = validate_goal_kpi_pair(goal_type, primary_kpi)
    except CampaignValidationError as exc:
        raise CampaignServiceError(exc.detail, status_code=exc.status_code) from exc

    await _ensure_own_company(db, tenant_id=tenant_id, own_company_id=own_company_id)

    validated = await _validate_and_resolve_targets(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        ctx=ctx,
        targets=targets,
    )

    campaign_id = str(uuid4())
    flight_id = str(uuid4())
    actor_id = str(ctx.sub) if ctx and ctx.sub else None
    actor_type = ACTOR_TYPE_USER if actor_id else ACTOR_TYPE_SYSTEM
    # CampaignGoal (ADR-024) is stored as goal_type + primary_kpi on Campaign in V1.
    campaign = Campaign(
        id=campaign_id,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        name=name_n,
        description=(str(description).strip() if description else None) or None,
        status="draft",
        goal_type=gt,
        primary_kpi=pk,
        current_flight_id=flight_id,
        created_by_user_id=actor_id,
    )
    db.add(campaign)
    # Attach targets before nested activity flush so we never lazy-load
    # ``campaign.targets`` after the instance is expired.
    for idx, t in enumerate(validated):
        db.add(
            CampaignTarget(
                id=str(uuid4()),
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                target_type=t.target_type,
                target_id=t.target_id,
                target_module=t.target_module,
                route_intent=t.route_intent,
                role=t.role,
                sort_order=t.sort_order if t.sort_order else idx,
            )
        )
    # V1 invariant: exactly one reserved Flight; status writes go through lifecycle.
    await create_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        code="flight_1",
        name="Flight 1",
        actor_type=actor_type,
        actor_id=actor_id,
    )
    await _emit_campaign_event(
        db,
        campaign=campaign,
        event_type="CampaignCreated",
        source_event_id=campaign_created_source_event_id(campaign_id),
        actor_type=actor_type,
        actor_id=actor_id,
        flight_id=flight_id,
    )
    await db.flush()
    return await _reload_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)


async def get_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None = None,
) -> Campaign:
    stmt = (
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .options(*_campaign_options())
    )
    if own_company_id:
        stmt = stmt.where(Campaign.own_company_id == own_company_id)
    row = await db.execute(stmt)
    campaign = row.scalar_one_or_none()
    if campaign is None:
        raise CampaignServiceError("Campaign not found", status_code=404)
    return campaign


async def list_campaigns(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Campaign]:
    stmt = (
        select(Campaign)
        .where(Campaign.tenant_id == tenant_id)
        .options(*_campaign_options())
        .order_by(Campaign.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .offset(max(0, offset))
    )
    if own_company_id:
        stmt = stmt.where(Campaign.own_company_id == own_company_id)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def update_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    ctx: UserCtx,
    campaign_id: str,
    own_company_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    goal_type: str | None = None,
    primary_kpi: str | None = None,
) -> Campaign:
    """Metadata-only Campaign update — lifecycle status is command-only (Stage 4 PR-2)."""
    _ = ctx
    campaign = await get_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
    if name is not None:
        name_n = str(name).strip()
        if not name_n:
            raise CampaignServiceError("name cannot be empty", status_code=422)
        campaign.name = name_n
    if description is not None:
        campaign.description = str(description).strip() or None

    next_gt = goal_type if goal_type is not None else campaign.goal_type
    next_pk = primary_kpi if primary_kpi is not None else campaign.primary_kpi
    if goal_type is not None or primary_kpi is not None:
        try:
            gt, pk = validate_goal_kpi_pair(next_gt, next_pk)
        except CampaignValidationError as exc:
            raise CampaignServiceError(exc.detail, status_code=exc.status_code) from exc
        campaign.goal_type = gt
        campaign.primary_kpi = pk

    await db.flush()
    return await _reload_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )


async def _apply_campaign_command(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None,
    command: str,
    target_status: str,
    event_type: str,
    allowed_from: frozenset[str],
    actor_type: str,
    actor_id: str | None,
    reason: str | None = None,
) -> tuple[Campaign, AcquisitionActivityEvent]:
    campaign = await get_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
    source_event_id = campaign_command_source_event_id(str(campaign.id), command)
    current = str(campaign.status or "").strip().lower()
    target = str(target_status).strip().lower()

    if current == target:
        existing = await get_by_source_event_id(
            db, tenant_id=tenant_id, source_event_id=source_event_id
        )
        if existing is None:
            # Status already matches (e.g. legacy free PATCH) — emit idempotent marker.
            existing = await _emit_campaign_event(
                db,
                campaign=campaign,
                event_type=event_type,
                source_event_id=source_event_id,
                actor_type=actor_type,
                actor_id=actor_id,
                note=reason,
            )
        return campaign, existing

    if current not in allowed_from:
        raise CampaignServiceError(
            f"cannot {command} campaign from status {current!r}",
            status_code=422,
        )

    campaign.status = target
    await db.flush()
    event = await _emit_campaign_event(
        db,
        campaign=campaign,
        event_type=event_type,
        source_event_id=source_event_id,
        actor_type=actor_type,
        actor_id=actor_id,
        note=reason,
    )
    reloaded = await _reload_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
    return reloaded, event


async def complete_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    actor_type: str,
    actor_id: str | None = None,
    own_company_id: str | None = None,
    reason: str | None = None,
) -> tuple[Campaign, AcquisitionActivityEvent]:
    """Mark Campaign completed. Does not mutate Flight status."""
    return await _apply_campaign_command(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        command="complete",
        target_status="completed",
        event_type="CampaignCompleted",
        allowed_from=_CAMPAIGN_COMPLETE_FROM,
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
    )


async def archive_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    actor_type: str,
    actor_id: str | None = None,
    own_company_id: str | None = None,
    reason: str | None = None,
) -> tuple[Campaign, AcquisitionActivityEvent]:
    """Mark Campaign archived. Does not mutate Flight status."""
    return await _apply_campaign_command(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        command="archive",
        target_status="archived",
        event_type="CampaignArchived",
        allowed_from=_CAMPAIGN_ARCHIVE_FROM,
        actor_type=actor_type,
        actor_id=actor_id,
        reason=reason,
    )


async def add_campaign_target(
    db: AsyncSession,
    *,
    tenant_id: str,
    ctx: UserCtx,
    campaign_id: str,
    own_company_id: str | None = None,
    target_type: str,
    target_id: str,
    route_intent: str,
    role: str = "primary",
    sort_order: int = 0,
    client_target_module: str | None = None,
) -> Campaign:
    campaign = await get_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
    validated_list = await _validate_and_resolve_targets(
        db,
        tenant_id=tenant_id,
        own_company_id=campaign.own_company_id,
        ctx=ctx,
        targets=[
            {
                "target_type": target_type,
                "target_id": target_id,
                "route_intent": route_intent,
                "role": role,
                "sort_order": sort_order,
                "target_module": client_target_module,
            }
        ],
    )
    validated = validated_list[0]

    campaign.targets.append(
        CampaignTarget(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            target_type=validated.target_type,
            target_id=validated.target_id,
            target_module=validated.target_module,
            route_intent=validated.route_intent,
            role=validated.role,
            sort_order=validated.sort_order,
        )
    )
    await db.flush()
    return await _reload_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )


async def remove_campaign_target(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    target_row_id: str,
    own_company_id: str | None = None,
) -> Campaign:
    await get_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
    row = await db.execute(
        select(CampaignTarget).where(
            CampaignTarget.id == target_row_id,
            CampaignTarget.campaign_id == campaign_id,
            CampaignTarget.tenant_id == tenant_id,
        )
    )
    target = row.scalar_one_or_none()
    if target is None:
        raise CampaignServiceError("Campaign target not found", status_code=404)
    await db.delete(target)
    await db.flush()
    return await _reload_campaign(
        db, tenant_id=tenant_id, campaign_id=campaign_id, own_company_id=own_company_id
    )
