"""Platform Campaigns API — ADR-024 Stage 3A foundation + Stage 3B bindings."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition import binding_service, campaign_service
from backend.app.acquisition.campaign_service import CampaignServiceError
from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.constants.campaign_registries import load_campaign_registries
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM, ACTOR_TYPE_USER
from backend.app.models.campaign import Campaign
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.tenant_lead_form import TenantLeadForm

router = APIRouter(
    prefix="/platform/campaigns",
    tags=["campaigns"],
    redirect_slashes=False,
)

_WRITE = [Depends(require_roles(Role.administrator, Role.supervisor, Role.recruiter, Role.client_manager, Role.superadmin))]

def _activity_actor(ctx: UserCtx) -> tuple[str, str | None]:
    actor_id = str(ctx.sub).strip() if ctx and getattr(ctx, "sub", None) else None
    if actor_id:
        return ACTOR_TYPE_USER, actor_id
    return ACTOR_TYPE_SYSTEM, None

_READ = [
    Depends(
        require_roles(
            Role.administrator,
            Role.supervisor,
            Role.recruiter,
            Role.client_manager,
            Role.viewer,
            Role.hr_officer,
            Role.superadmin,
        )
    )
]


class CampaignTargetIn(BaseModel):
    target_type: str
    target_id: str
    route_intent: str
    role: str = "primary"
    sort_order: int = 0
    # Optional — if sent, must match canonical registry module (never trusted as SoT).
    target_module: Optional[str] = None


class CampaignCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    goal_type: str
    primary_kpi: str
    description: Optional[str] = None
    own_company_id: Optional[str] = None
    targets: List[CampaignTargetIn] = Field(default_factory=list)


class CampaignUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    goal_type: Optional[str] = None
    primary_kpi: Optional[str] = None


class FormLinkIn(BaseModel):
    form_id: str
    role: str = "primary"


class IntakeSourceLinkIn(BaseModel):
    intake_source_profile_id: str
    role: str = "primary"


class LinkPatchIn(BaseModel):
    """Update association flags only — does not mutate Form / Intake Source SoT."""

    is_active: Optional[bool] = None
    role: Optional[str] = None


class CampaignTargetOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    target_module: str
    route_intent: str
    role: str
    sort_order: int


class CampaignFormLinkOut(BaseModel):
    id: str
    form_id: str
    role: str
    is_active: bool
    title: Optional[str] = None
    public_slug: Optional[str] = None


class IntakeSourceBindingOut(BaseModel):
    """Live resolve from IntakeSourceBinding SoT (not stored on association)."""

    id: str
    provider: str
    external_key: str
    external_key_secondary: str = ""
    label: Optional[str] = None
    priority: int = 0


class CampaignIntakeSourceLinkOut(BaseModel):
    id: str
    intake_source_profile_id: str
    role: str
    is_active: bool
    # From IntakeSourceProfile JOIN
    provider: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    # Live from IntakeSourceBinding SoT
    bindings: List[IntakeSourceBindingOut] = Field(default_factory=list)


class CampaignFlightOut(BaseModel):
    id: str
    code: str
    name: str
    status: str
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_current: bool = False
    forms: List[CampaignFormLinkOut] = Field(default_factory=list)
    intake_sources: List[CampaignIntakeSourceLinkOut] = Field(default_factory=list)


class CampaignGoalOut(BaseModel):
    """Logical CampaignGoal (ADR-024) — Goal Type + Primary KPI."""

    goal_type: str
    primary_kpi: str


class CampaignOut(BaseModel):
    id: str
    tenant_id: str
    own_company_id: str
    name: str
    description: Optional[str] = None
    status: str
    goal_type: str
    primary_kpi: str
    goal: CampaignGoalOut
    current_flight_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    targets: List[CampaignTargetOut] = Field(default_factory=list)
    flights: List[CampaignFlightOut] = Field(default_factory=list)


async def _form_display_map(
    db: AsyncSession, *, tenant_id: str, form_ids: set[str]
) -> dict[str, TenantLeadForm]:
    if not form_ids:
        return {}
    rows = await db.execute(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == tenant_id,
            TenantLeadForm.id.in_(list(form_ids)),
        )
    )
    return {row.id: row for row in rows.scalars().all()}


async def _profile_display_map(
    db: AsyncSession, *, tenant_id: str, profile_ids: set[str]
) -> dict[str, IntakeSourceProfile]:
    if not profile_ids:
        return {}
    rows = await db.execute(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == tenant_id,
            IntakeSourceProfile.id.in_(list(profile_ids)),
        )
    )
    return {row.id: row for row in rows.scalars().all()}


async def _bindings_by_profile(
    db: AsyncSession, *, tenant_id: str, profile_ids: set[str]
) -> dict[str, list[IntakeSourceBinding]]:
    if not profile_ids:
        return {}
    rows = await db.execute(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == tenant_id,
            IntakeSourceBinding.intake_source_profile_id.in_(list(profile_ids)),
            IntakeSourceBinding.is_active.is_(True),
        )
    )
    out: dict[str, list[IntakeSourceBinding]] = {}
    for row in rows.scalars().all():
        out.setdefault(row.intake_source_profile_id, []).append(row)
    for items in out.values():
        items.sort(key=lambda b: int(b.priority or 0), reverse=True)
    return out


async def _campaign_out(db: AsyncSession, campaign: Campaign) -> CampaignOut:
    current = campaign.current_flight_id
    goal = CampaignGoalOut(goal_type=campaign.goal_type, primary_kpi=campaign.primary_kpi)

    form_ids: set[str] = set()
    profile_ids: set[str] = set()
    for flight in campaign.flights or []:
        for link in flight.form_links or []:
            form_ids.add(link.form_id)
        for link in flight.intake_source_links or []:
            profile_ids.add(link.intake_source_profile_id)

    forms_by_id = await _form_display_map(db, tenant_id=campaign.tenant_id, form_ids=form_ids)
    profiles_by_id = await _profile_display_map(
        db, tenant_id=campaign.tenant_id, profile_ids=profile_ids
    )
    bindings_map = await _bindings_by_profile(
        db, tenant_id=campaign.tenant_id, profile_ids=profile_ids
    )

    flights_out: list[CampaignFlightOut] = []
    for f in campaign.flights or []:
        forms_out = []
        for link in f.form_links or []:
            form = forms_by_id.get(link.form_id)
            forms_out.append(
                CampaignFormLinkOut(
                    id=link.id,
                    form_id=link.form_id,
                    role=link.role,
                    is_active=link.is_active,
                    title=form.title if form else None,
                    public_slug=form.public_slug if form else None,
                )
            )
        sources_out = []
        for link in f.intake_source_links or []:
            profile = profiles_by_id.get(link.intake_source_profile_id)
            live_bindings = bindings_map.get(link.intake_source_profile_id) or []
            sources_out.append(
                CampaignIntakeSourceLinkOut(
                    id=link.id,
                    intake_source_profile_id=link.intake_source_profile_id,
                    role=link.role,
                    is_active=link.is_active,
                    provider=str(profile.provider) if profile else None,
                    code=profile.code if profile else None,
                    name=profile.name if profile else None,
                    bindings=[
                        IntakeSourceBindingOut(
                            id=b.id,
                            provider=b.provider,
                            external_key=b.external_key,
                            external_key_secondary=b.external_key_secondary or "",
                            label=b.label,
                            priority=int(b.priority or 0),
                        )
                        for b in live_bindings
                    ],
                )
            )
        flights_out.append(
            CampaignFlightOut(
                id=f.id,
                code=f.code,
                name=f.name,
                status=f.status,
                starts_at=f.starts_at,
                ends_at=f.ends_at,
                is_current=bool(current and f.id == current),
                forms=forms_out,
                intake_sources=sources_out,
            )
        )

    return CampaignOut(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        own_company_id=campaign.own_company_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        goal_type=campaign.goal_type,
        primary_kpi=campaign.primary_kpi,
        goal=goal,
        current_flight_id=campaign.current_flight_id,
        created_by_user_id=campaign.created_by_user_id,
        created_at=getattr(campaign, "created_at", None),
        updated_at=getattr(campaign, "updated_at", None),
        targets=[
            CampaignTargetOut(
                id=t.id,
                target_type=t.target_type,
                target_id=t.target_id,
                target_module=t.target_module,
                route_intent=t.route_intent,
                role=t.role,
                sort_order=t.sort_order,
            )
            for t in (campaign.targets or [])
        ],
        flights=flights_out,
    )


def _raise_service(exc: CampaignServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


async def _resolve_company(
    db: AsyncSession,
    tenant_id: UUID,
    ctx: UserCtx,
    x_own_company_id: Optional[str],
    explicit: Optional[str] = None,
) -> str:
    if explicit and str(explicit).strip():
        return await resolve_own_company_id_for_session(
            db, str(tenant_id), ctx, str(explicit).strip()
        )
    return await resolve_own_company_id_for_session(db, str(tenant_id), ctx, x_own_company_id)


@router.get("/registries", dependencies=_READ)
async def get_campaign_registries(
    _: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    """SSOT registries for Goal Type / Primary KPI / Promotion Targets."""
    return load_campaign_registries()


@router.get("", response_model=List[CampaignOut], dependencies=_READ)
async def list_campaigns_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    rows = await campaign_service.list_campaigns(
        db,
        tenant_id=str(tenant_uuid),
        own_company_id=own_company_id,
        limit=limit,
        offset=offset,
    )
    return [await _campaign_out(db, r) for r in rows]


@router.post("", response_model=CampaignOut, status_code=201, dependencies=_WRITE)
async def create_campaign_endpoint(
    payload: CampaignCreateIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(
        db, tenant_uuid, ctx, x_own_company_id, payload.own_company_id
    )
    try:
        campaign = await campaign_service.create_campaign(
            db,
            tenant_id=str(tenant_uuid),
            ctx=ctx,
            own_company_id=own_company_id,
            name=payload.name,
            goal_type=payload.goal_type,
            primary_kpi=payload.primary_kpi,
            description=payload.description,
            targets=[t.model_dump() for t in payload.targets],
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.get("/{campaign_id}", response_model=CampaignOut, dependencies=_READ)
async def get_campaign_endpoint(
    campaign_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.get_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
        )
    except CampaignServiceError as exc:
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.patch("/{campaign_id}", response_model=CampaignOut, dependencies=_WRITE)
async def update_campaign_endpoint(
    campaign_id: str,
    payload: CampaignUpdateIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.update_campaign(
            db,
            tenant_id=str(tenant_uuid),
            ctx=ctx,
            campaign_id=campaign_id,
            own_company_id=own_company_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            goal_type=payload.goal_type,
            primary_kpi=payload.primary_kpi,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.post("/{campaign_id}/targets", response_model=CampaignOut, status_code=201, dependencies=_WRITE)
async def add_target_endpoint(
    campaign_id: str,
    payload: CampaignTargetIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.add_campaign_target(
            db,
            tenant_id=str(tenant_uuid),
            ctx=ctx,
            campaign_id=campaign_id,
            own_company_id=own_company_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            route_intent=payload.route_intent,
            role=payload.role,
            sort_order=payload.sort_order,
            client_target_module=payload.target_module,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.delete("/{campaign_id}/targets/{target_id}", response_model=CampaignOut, dependencies=_WRITE)
async def remove_target_endpoint(
    campaign_id: str,
    target_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.remove_campaign_target(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            target_row_id=target_id,
            own_company_id=own_company_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


# --- Stage 3B: Form / Intake Source bindings (current Flight shorthand) ---


@router.get("/{campaign_id}/forms", response_model=List[CampaignFormLinkOut], dependencies=_READ)
async def list_current_flight_forms(
    campaign_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.get_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
        )
    except CampaignServiceError as exc:
        _raise_service(exc)
    out = await _campaign_out(db, campaign)
    current = next((f for f in out.flights if f.is_current), None)
    return current.forms if current else []


@router.post(
    "/{campaign_id}/forms",
    response_model=CampaignOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_form_current_flight(
    campaign_id: str,
    payload: FormLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_form(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            form_id=payload.form_id,
            own_company_id=own_company_id,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.delete(
    "/{campaign_id}/forms/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def detach_form_current_flight(
    campaign_id: str,
    link_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.detach_form(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.patch(
    "/{campaign_id}/forms/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def patch_form_link_current_flight(
    campaign_id: str,
    link_id: str,
    payload: LinkPatchIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.update_form_link(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            is_active=payload.is_active,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.get(
    "/{campaign_id}/intake-sources",
    response_model=List[CampaignIntakeSourceLinkOut],
    dependencies=_READ,
)
async def list_current_flight_intake_sources(
    campaign_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign = await campaign_service.get_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
        )
    except CampaignServiceError as exc:
        _raise_service(exc)
    out = await _campaign_out(db, campaign)
    current = next((f for f in out.flights if f.is_current), None)
    return current.intake_sources if current else []


@router.post(
    "/{campaign_id}/intake-sources",
    response_model=CampaignOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_intake_source_current_flight(
    campaign_id: str,
    payload: IntakeSourceLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_intake_source(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            intake_source_profile_id=payload.intake_source_profile_id,
            own_company_id=own_company_id,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.delete(
    "/{campaign_id}/intake-sources/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def detach_intake_source_current_flight(
    campaign_id: str,
    link_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.detach_intake_source(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.patch(
    "/{campaign_id}/intake-sources/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def patch_intake_source_link_current_flight(
    campaign_id: str,
    link_id: str,
    payload: LinkPatchIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.update_intake_source_link(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            is_active=payload.is_active,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


# Explicit Flight paths (V1 = one Flight; same handlers with flight_id)


@router.post(
    "/{campaign_id}/flights/{flight_id}/forms",
    response_model=CampaignOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_form_on_flight(
    campaign_id: str,
    flight_id: str,
    payload: FormLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_form(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            form_id=payload.form_id,
            own_company_id=own_company_id,
            flight_id=flight_id,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.delete(
    "/{campaign_id}/flights/{flight_id}/forms/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def detach_form_on_flight(
    campaign_id: str,
    flight_id: str,
    link_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.detach_form(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            flight_id=flight_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.post(
    "/{campaign_id}/flights/{flight_id}/intake-sources",
    response_model=CampaignOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_intake_source_on_flight(
    campaign_id: str,
    flight_id: str,
    payload: IntakeSourceLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_intake_source(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            intake_source_profile_id=payload.intake_source_profile_id,
            own_company_id=own_company_id,
            flight_id=flight_id,
            role=payload.role,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.delete(
    "/{campaign_id}/flights/{flight_id}/intake-sources/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def detach_intake_source_on_flight(
    campaign_id: str,
    flight_id: str,
    link_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.detach_intake_source(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            own_company_id=own_company_id,
            flight_id=flight_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)
