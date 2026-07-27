"""Platform Campaigns API — ADR-024 Stage 3A foundation + Stage 3B bindings."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition import binding_service, campaign_service
from backend.app.acquisition.campaign_service import CampaignServiceError
from backend.app.acquisition.campaign_source_cards import (
    enrich_form_card,
    enrich_intake_source_card,
    load_last_submission_by_endpoint,
    load_meta_form_mappings_by_form_id,
    parse_meta_form_id,
)
from backend.app.acquisition.endpoint_activity import form_endpoint_id, intake_source_endpoint_id
from backend.app.acquisition.flights import runtime_commands
from backend.app.acquisition.flights.runtime_commands import FlightRuntimeError
from backend.app.acquisition.kpi_aggregates import (
    KpiAggregateError,
    aggregate_campaign_kpi,
    aggregate_flight_kpi,
)
from backend.app.acquisition.ops.live_intake_monitor import get_live_intake_monitor
from backend.app.acquisition.ops.optimization_signals import get_flight_optimization
from backend.app.acquisition.ops.runtime_read import get_flight_runtime_snapshot
from backend.app.api.v1.platform.acquisition_activity import (
    ActivityCursorOut,
    ActivityEventOut,
)
from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.constants.campaign_registries import load_campaign_registries
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    ACTOR_TYPE_USER,
    AcquisitionActivityEvent,
)
from backend.app.models.campaign import Campaign
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.tenant_lead_form import TenantLeadForm


def _activity_event_out(row: AcquisitionActivityEvent) -> ActivityEventOut:
    return ActivityEventOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        campaign_id=str(row.campaign_id),
        flight_id=str(row.flight_id) if row.flight_id else None,
        endpoint_id=str(row.endpoint_id) if row.endpoint_id else None,
        submission_id=str(row.submission_id) if row.submission_id else None,
        result_id=str(row.result_id) if row.result_id else None,
        outcome_id=str(row.outcome_id) if row.outcome_id else None,
        event_type=str(row.event_type),
        event_version=str(row.event_version),
        occurred_at=row.occurred_at,
        recorded_at=row.recorded_at,
        actor_type=str(row.actor_type),
        actor_id=str(row.actor_id) if row.actor_id else None,
        provider=str(row.provider) if row.provider else None,
        source_event_id=str(row.source_event_id) if row.source_event_id else None,
        correlation_id=str(row.correlation_id) if row.correlation_id else None,
        causation_id=str(row.causation_id) if row.causation_id else None,
        payload=dict(row.payload or {}),
    )

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
    """Metadata-only Campaign update — lifecycle status is command-only (Stage 4 PR-2)."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    goal_type: Optional[str] = None
    primary_kpi: Optional[str] = None


class CampaignCommandIn(BaseModel):
    reason: Optional[str] = None


class FormLinkIn(BaseModel):
    form_id: str
    role: str = "primary"


class IntakeSourceLinkIn(BaseModel):
    intake_source_profile_id: str
    role: str = "primary"


class AdLinkIn(BaseModel):
    """Meta Ad ID → Flight advertising route (Meta-only until more providers map to Lead.source)."""

    provider_ad_id: str
    provider: str = "meta"

    @field_validator("provider")
    @classmethod
    def _provider_must_be_supported(cls, value: str) -> str:
        from backend.app.acquisition.flight_ad_binding import normalize_flight_ad_provider

        try:
            return normalize_flight_ad_provider(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class AdBindingOut(BaseModel):
    id: str
    provider: str
    provider_ad_id: str
    campaign_id: str
    flight_id: str
    is_active: bool
    reprocess: Optional[dict] = None


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
    # Human card (Forms SoT + activity compose; PR2)
    form_is_active: Optional[bool] = None
    publication_status: Optional[str] = None
    is_public: Optional[bool] = None
    last_submission_at: Optional[datetime] = None


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
    # Human card (Meta mapping / bindings / activity compose; PR2)
    profile_is_active: Optional[bool] = None
    display_title: Optional[str] = None
    lead_form_name: Optional[str] = None
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    meta_form_id: Optional[str] = None
    binding_status: Optional[str] = None
    active_binding_count: Optional[int] = None
    last_submission_at: Optional[datetime] = None


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
    # Meta Ad ID → Flight overrides (read shape; write via /ad-bindings)
    ad_bindings: List[AdBindingOut] = Field(default_factory=list)


class FlightUpdateIn(BaseModel):
    """Metadata-only Flight update — lifecycle status is command-only (Stage 4 PR-1)."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class FlightCommandIn(BaseModel):
    reason: Optional[str] = None


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


class FlightCommandOut(BaseModel):
    command: str
    campaign: CampaignOut
    flight_id: str
    flight_status: str
    campaign_status: str
    flight_event_id: str
    flight_event_type: str
    campaign_event_id: Optional[str] = None
    campaign_event_type: Optional[str] = None


class FlightKpiOut(BaseModel):
    tenant_id: str
    campaign_id: str
    flight_id: str
    currency: Optional[str] = None
    spend: str
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[str] = None
    cost_per_qualified: Optional[str] = None
    cost_per_outcome: Optional[str] = None


class CampaignKpiOut(BaseModel):
    tenant_id: str
    campaign_id: str
    currency: Optional[str] = None
    spend: str
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[str] = None
    cost_per_qualified: Optional[str] = None
    cost_per_outcome: Optional[str] = None
    flights: List[FlightKpiOut] = Field(default_factory=list)


class EndpointsSummaryOut(BaseModel):
    forms_total: int
    forms_active: int
    intake_sources_total: int
    intake_sources_active: int


class FlightRuntimeOut(BaseModel):
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    flight_name: str
    flight_code: str
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_current: bool
    endpoints: EndpointsSummaryOut
    kpi: FlightKpiOut
    generated_at: datetime


class LiveIntakeCountersOut(BaseModel):
    submissions: int
    leads_activity: int
    candidates: int
    routing_completed: int
    routing_failed: int
    rejected: int
    kpi_leads: int
    spend: str
    cost_per_lead: Optional[str] = None
    currency: Optional[str] = None


class LiveIntakeApplicantOut(BaseModel):
    lead_id: str
    created_at: Optional[datetime] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_status: str
    disposition: Optional[str] = None
    status_label: str
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    route_intent: Optional[str] = None
    routing_status: Optional[str] = None
    source: Optional[str] = None


class LiveIntakeApplicantsCursorOut(BaseModel):
    created_at: datetime
    id: str


class LiveIntakeMonitorOut(BaseModel):
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    counters: LiveIntakeCountersOut
    applicants: List[LiveIntakeApplicantOut] = Field(default_factory=list)
    applicants_next_cursor: Optional[LiveIntakeApplicantsCursorOut] = None
    items: List[ActivityEventOut] = Field(default_factory=list)
    next_cursor: Optional[ActivityCursorOut] = None
    order: tuple[str, str]
    event_types: List[str] = Field(default_factory=list)


class OptimizationSignalOut(BaseModel):
    code: str
    severity: str
    message: str


class OptimizationWindowCountersOut(BaseModel):
    submissions: int
    routing_completed: int
    routing_failed: int
    delivery_errors: int
    routing_sample: int
    decision_volume: int


class OptimizationThresholdsOut(BaseModel):
    min_decision_volume: int
    routing_fail_rate_threshold: float
    min_routing_sample: int
    delivery_error_threshold: int


class FlightOptimizationOut(BaseModel):
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    assessment: str
    recommended_action: str
    reason_codes: List[str] = Field(default_factory=list)
    signals: List[OptimizationSignalOut] = Field(default_factory=list)
    window_hours: int
    window_start: datetime
    window_end: datetime
    counters: OptimizationWindowCountersOut
    kpi_leads: int
    spend: str
    generated_at: datetime
    thresholds: OptimizationThresholdsOut


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

    meta_form_ids: set[str] = set()
    for live_bindings in bindings_map.values():
        for b in live_bindings:
            fid = parse_meta_form_id(b.external_key)
            if fid:
                meta_form_ids.add(fid)
    for profile in profiles_by_id.values():
        code = str(profile.code or "")
        if code.startswith("meta-form-"):
            fid = code[len("meta-form-") :].strip()
            if fid:
                meta_form_ids.add(fid)

    meta_maps = await load_meta_form_mappings_by_form_id(
        db, tenant_id=campaign.tenant_id, form_ids=meta_form_ids
    )

    endpoint_ids = [form_endpoint_id(fid) for fid in form_ids] + [
        intake_source_endpoint_id(pid) for pid in profile_ids
    ]
    last_by_endpoint = await load_last_submission_by_endpoint(
        db, tenant_id=campaign.tenant_id, endpoint_ids=endpoint_ids
    )

    flights_out: list[CampaignFlightOut] = []
    for f in campaign.flights or []:
        forms_out = []
        for link in f.form_links or []:
            form = forms_by_id.get(link.form_id)
            form_card = enrich_form_card(
                form,
                last_submission_at=last_by_endpoint.get(form_endpoint_id(link.form_id)),
            )
            forms_out.append(
                CampaignFormLinkOut(
                    id=link.id,
                    form_id=link.form_id,
                    role=link.role,
                    is_active=link.is_active,
                    title=form.title if form else None,
                    public_slug=form.public_slug if form else None,
                    form_is_active=form_card.form_is_active,
                    publication_status=form_card.publication_status,
                    is_public=form_card.is_public,
                    last_submission_at=form_card.last_submission_at,
                )
            )
        sources_out = []
        for link in f.intake_source_links or []:
            profile = profiles_by_id.get(link.intake_source_profile_id)
            live_bindings = bindings_map.get(link.intake_source_profile_id) or []
            meta_form_id = None
            for b in live_bindings:
                meta_form_id = parse_meta_form_id(b.external_key)
                if meta_form_id:
                    break
            if not meta_form_id and profile is not None:
                code = str(profile.code or "")
                if code.startswith("meta-form-"):
                    meta_form_id = code[len("meta-form-") :].strip() or None
            meta_map = meta_maps.get(meta_form_id) if meta_form_id else None
            src_card = enrich_intake_source_card(
                profile,
                live_bindings,
                meta_map=meta_map,
                last_submission_at=last_by_endpoint.get(
                    intake_source_endpoint_id(link.intake_source_profile_id)
                ),
            )
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
                    profile_is_active=src_card.profile_is_active,
                    display_title=src_card.display_title,
                    lead_form_name=src_card.lead_form_name,
                    page_id=src_card.page_id,
                    page_name=src_card.page_name,
                    meta_form_id=src_card.meta_form_id,
                    binding_status=src_card.binding_status,
                    active_binding_count=src_card.active_binding_count,
                    last_submission_at=src_card.last_submission_at,
                )
            )
        ad_bindings_out = [
            AdBindingOut(
                id=str(link.id),
                provider=str(link.provider or "meta"),
                provider_ad_id=str(link.provider_ad_id or ""),
                campaign_id=str(campaign.id),
                flight_id=str(link.campaign_run_id),
                is_active=bool(link.is_active),
                reprocess=None,
            )
            for link in (f.ad_links or [])
        ]
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
                ad_bindings=ad_bindings_out,
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


def _raise_runtime(exc: FlightRuntimeError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


async def _flight_command(
    *,
    command: str,
    campaign_id: str,
    flight_id: str,
    payload: FlightCommandIn,
    db_tenant,
    ctx: UserCtx,
    x_own_company_id: Optional[str],
) -> FlightCommandOut:
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        result = await runtime_commands.execute_flight_command(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            command=command,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=payload.reason,
            own_company_id=own_company_id,
        )
        await db.commit()
    except FlightRuntimeError as exc:
        await db.rollback()
        _raise_runtime(exc)
    campaign_out = await _campaign_out(db, result.campaign)
    return FlightCommandOut(
        command=result.command,
        campaign=campaign_out,
        flight_id=str(result.flight.id),
        flight_status=str(result.flight.status),
        campaign_status=str(result.campaign.status),
        flight_event_id=str(result.flight_event.id),
        flight_event_type=str(result.flight_event.event_type),
        campaign_event_id=(
            str(result.campaign_event.id) if result.campaign_event is not None else None
        ),
        campaign_event_type=(
            str(result.campaign_event.event_type) if result.campaign_event is not None else None
        ),
    )


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


class IntakeSourceSampleAdOut(BaseModel):
    ad_id: str
    label: Optional[str] = None


class IntakeSourceOptionOut(BaseModel):
    """Picker option for Marketing Workspace — bindable IntakeSourceProfile rows.

    Enrichment: ``campaign_source_cards`` + optional Meta Graph hydrate
    (``connect_source_picker``). See
    ``docs/specs/tasks/acquisition-ui-cutover-connect-source-picker-enrichment.md``.
    """

    id: str
    name: str
    provider: str
    code: str
    is_active: bool
    display_title: Optional[str] = None
    lead_form_name: Optional[str] = None
    meta_form_id: Optional[str] = None
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    last_submission_at: Optional[datetime] = None
    sample_ad_ids: List[str] = Field(default_factory=list)
    sample_ads: List[IntakeSourceSampleAdOut] = Field(default_factory=list)


@router.get(
    "/intake-source-options",
    response_model=List[IntakeSourceOptionOut],
    dependencies=_READ,
)
async def list_intake_source_options(
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
    provider: Optional[str] = Query(default=None),
):
    """List active intake sources for the current company (Marketing setup picker)."""
    from backend.app.acquisition.connect_source_picker import build_intake_source_options

    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    stmt = select(IntakeSourceProfile).where(
        IntakeSourceProfile.tenant_id == str(tenant_uuid),
        IntakeSourceProfile.own_company_id == own_company_id,
        IntakeSourceProfile.is_active.is_(True),
    )
    if provider and str(provider).strip():
        stmt = stmt.where(IntakeSourceProfile.provider == str(provider).strip().lower())
    stmt = stmt.order_by(IntakeSourceProfile.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    enriched = await build_intake_source_options(
        db,
        tenant_id=str(tenant_uuid),
        profiles=list(rows),
        hydrate_graph=True,
    )
    return [IntakeSourceOptionOut(**row) for row in enriched]

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
    fields = getattr(payload, "model_fields_set", None) or getattr(payload, "__fields_set__", set())
    if "status" in fields:
        raise HTTPException(
            status_code=422,
            detail="Campaign status cannot be changed via PATCH; use launch/pause/resume (Flight) or complete/archive",
        )
    try:
        campaign = await campaign_service.update_campaign(
            db,
            tenant_id=str(tenant_uuid),
            ctx=ctx,
            campaign_id=campaign_id,
            own_company_id=own_company_id,
            name=payload.name,
            description=payload.description,
            goal_type=payload.goal_type,
            primary_kpi=payload.primary_kpi,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.post(
    "/{campaign_id}/complete",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def complete_campaign_endpoint(
    campaign_id: str,
    payload: Optional[CampaignCommandIn] = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    body = payload or CampaignCommandIn()
    try:
        campaign, _event = await campaign_service.complete_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=body.reason,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    return await _campaign_out(db, campaign)


@router.post(
    "/{campaign_id}/archive",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def archive_campaign_endpoint(
    campaign_id: str,
    payload: Optional[CampaignCommandIn] = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    body = payload or CampaignCommandIn()
    try:
        campaign, _event = await campaign_service.archive_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=body.reason,
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


# Stage 4 PR-1 — Flight Runtime: read / metadata / lifecycle commands


@router.get(
    "/{campaign_id}/flights",
    response_model=List[CampaignFlightOut],
    dependencies=_READ,
)
async def list_flights_endpoint(
    campaign_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign, _flights = await runtime_commands.list_flights(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    out = await _campaign_out(db, campaign)
    return out.flights


@router.get(
    "/{campaign_id}/flights/{flight_id}",
    response_model=CampaignFlightOut,
    dependencies=_READ,
)
async def get_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        campaign, flight = await runtime_commands.get_flight(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    out = await _campaign_out(db, campaign)
    for item in out.flights:
        if item.id == str(flight.id):
            return item
    raise HTTPException(status_code=404, detail="Flight not found")


@router.patch(
    "/{campaign_id}/flights/{flight_id}",
    response_model=CampaignFlightOut,
    dependencies=_WRITE,
)
async def update_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    payload: FlightUpdateIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    fields = payload.model_dump(exclude_unset=True)
    if "status" in fields:
        raise HTTPException(
            status_code=422,
            detail="Flight status cannot be changed via PATCH; use launch/pause/resume/complete",
        )
    try:
        campaign, flight = await runtime_commands.update_flight_metadata(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
            name=fields["name"] if "name" in fields else None,
            starts_at=fields.get("starts_at") if "starts_at" in fields else None,
            ends_at=fields.get("ends_at") if "ends_at" in fields else None,
            clear_starts_at="starts_at" in fields and fields.get("starts_at") is None,
            clear_ends_at="ends_at" in fields and fields.get("ends_at") is None,
        )
        await db.commit()
    except FlightRuntimeError as exc:
        await db.rollback()
        _raise_runtime(exc)
    out = await _campaign_out(db, campaign)
    for item in out.flights:
        if item.id == str(flight.id):
            return item
    raise HTTPException(status_code=404, detail="Flight not found")


@router.post(
    "/{campaign_id}/flights/{flight_id}/launch",
    response_model=FlightCommandOut,
    dependencies=_WRITE,
)
async def launch_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    payload: FlightCommandIn | None = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    return await _flight_command(
        command="launch",
        campaign_id=campaign_id,
        flight_id=flight_id,
        payload=payload or FlightCommandIn(),
        db_tenant=db_tenant,
        ctx=ctx,
        x_own_company_id=x_own_company_id,
    )


@router.post(
    "/{campaign_id}/flights/{flight_id}/pause",
    response_model=FlightCommandOut,
    dependencies=_WRITE,
)
async def pause_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    payload: FlightCommandIn | None = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    return await _flight_command(
        command="pause",
        campaign_id=campaign_id,
        flight_id=flight_id,
        payload=payload or FlightCommandIn(),
        db_tenant=db_tenant,
        ctx=ctx,
        x_own_company_id=x_own_company_id,
    )


@router.post(
    "/{campaign_id}/flights/{flight_id}/resume",
    response_model=FlightCommandOut,
    dependencies=_WRITE,
)
async def resume_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    payload: FlightCommandIn | None = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    return await _flight_command(
        command="resume",
        campaign_id=campaign_id,
        flight_id=flight_id,
        payload=payload or FlightCommandIn(),
        db_tenant=db_tenant,
        ctx=ctx,
        x_own_company_id=x_own_company_id,
    )


@router.post(
    "/{campaign_id}/flights/{flight_id}/complete",
    response_model=FlightCommandOut,
    dependencies=_WRITE,
)
async def complete_flight_endpoint(
    campaign_id: str,
    flight_id: str,
    payload: FlightCommandIn | None = None,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    return await _flight_command(
        command="complete",
        campaign_id=campaign_id,
        flight_id=flight_id,
        payload=payload or FlightCommandIn(),
        db_tenant=db_tenant,
        ctx=ctx,
        x_own_company_id=x_own_company_id,
    )


# Explicit Flight binding paths (V1 = one Flight; same handlers with flight_id)


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


@router.patch(
    "/{campaign_id}/flights/{flight_id}/forms/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def patch_form_link_on_flight(
    campaign_id: str,
    flight_id: str,
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
            flight_id=flight_id,
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


@router.patch(
    "/{campaign_id}/flights/{flight_id}/intake-sources/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def patch_intake_source_link_on_flight(
    campaign_id: str,
    flight_id: str,
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
            flight_id=flight_id,
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


# Stage 4 PR-3 — Runtime Read API + Live Intake Monitor


@router.get(
    "/{campaign_id}/kpi",
    response_model=CampaignKpiOut,
    dependencies=_READ,
)
async def get_campaign_kpi_endpoint(
    campaign_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        await campaign_service.get_campaign(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            own_company_id=own_company_id,
        )
        kpi = await aggregate_campaign_kpi(
            db, tenant_id=str(tenant_uuid), campaign_id=campaign_id
        )
    except CampaignServiceError as exc:
        _raise_service(exc)
    except KpiAggregateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CampaignKpiOut.model_validate(kpi.to_dict())


@router.get(
    "/{campaign_id}/flights/{flight_id}/kpi",
    response_model=FlightKpiOut,
    dependencies=_READ,
)
async def get_flight_kpi_endpoint(
    campaign_id: str,
    flight_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        await runtime_commands.get_flight(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
        )
        kpi = await aggregate_flight_kpi(
            db, tenant_id=str(tenant_uuid), flight_id=flight_id
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    except KpiAggregateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FlightKpiOut.model_validate(kpi.to_dict())


@router.get(
    "/{campaign_id}/flights/{flight_id}/runtime",
    response_model=FlightRuntimeOut,
    dependencies=_READ,
)
async def get_flight_runtime_endpoint(
    campaign_id: str,
    flight_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        snap = await get_flight_runtime_snapshot(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    return FlightRuntimeOut(
        tenant_id=snap.tenant_id,
        campaign_id=snap.campaign_id,
        flight_id=snap.flight_id,
        campaign_status=snap.campaign_status,
        flight_status=snap.flight_status,
        flight_name=snap.flight_name,
        flight_code=snap.flight_code,
        starts_at=snap.starts_at,
        ends_at=snap.ends_at,
        is_current=snap.is_current,
        endpoints=EndpointsSummaryOut(**snap.endpoints.to_dict()),
        kpi=FlightKpiOut.model_validate(snap.kpi.to_dict()),
        generated_at=snap.generated_at,
    )


@router.get(
    "/{campaign_id}/flights/{flight_id}/monitor/live-intake",
    response_model=LiveIntakeMonitorOut,
    dependencies=_READ,
)
async def get_live_intake_monitor_endpoint(
    campaign_id: str,
    flight_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
    occurred_after: Optional[datetime] = Query(None),
    after_occurred_at: Optional[datetime] = Query(None),
    after_id: Optional[str] = Query(None),
    applicants_after_created_at: Optional[datetime] = Query(None),
    applicants_after_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[List[str]] = Query(None),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        page = await get_live_intake_monitor(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
            occurred_after=occurred_after,
            after_occurred_at=after_occurred_at,
            after_id=after_id,
            limit=limit,
            event_types=event_type,
            applicants_after_created_at=applicants_after_created_at,
            applicants_after_id=applicants_after_id,
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    next_cursor = None
    if page.next_cursor is not None:
        next_cursor = ActivityCursorOut(
            occurred_at=page.next_cursor[0], id=page.next_cursor[1]
        )
    applicants_next = None
    if page.applicants_next_cursor is not None:
        applicants_next = LiveIntakeApplicantsCursorOut(
            created_at=page.applicants_next_cursor[0],
            id=page.applicants_next_cursor[1],
        )
    return LiveIntakeMonitorOut(
        tenant_id=page.tenant_id,
        campaign_id=page.campaign_id,
        flight_id=page.flight_id,
        campaign_status=page.campaign_status,
        flight_status=page.flight_status,
        counters=LiveIntakeCountersOut(**page.counters.to_dict()),
        applicants=[
            LiveIntakeApplicantOut(**row.to_dict()) for row in page.applicants
        ],
        applicants_next_cursor=applicants_next,
        items=[_activity_event_out(row) for row in page.items],
        next_cursor=next_cursor,
        order=page.order,
        event_types=list(page.event_types),
    )


@router.get(
    "/{campaign_id}/flights/{flight_id}/optimization",
    response_model=FlightOptimizationOut,
    dependencies=_READ,
)
async def get_flight_optimization_endpoint(
    campaign_id: str,
    flight_id: str,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
    window_hours: Optional[int] = Query(
        None,
        ge=1,
        le=168,
        description="Observation window in hours (default 24, clamped 1..168).",
    ),
):
    """Stage 5 PR-1 — read-only optimization signals / pause recommendation.

    Does not mutate Campaign/Flight and does not append Activity events.
    """
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    try:
        snap = await get_flight_optimization(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
            window_hours=window_hours,
        )
    except FlightRuntimeError as exc:
        _raise_runtime(exc)
    return FlightOptimizationOut.model_validate(snap.to_dict())


# --- FlightAdBinding (Ad ID → Flight) ---


async def _reprocess_after_ad_binding_commit(
    *,
    tenant_id: str,
    provider: str,
    provider_ad_id: str,
    enabled: bool = True,
) -> dict:
    """Run auto-reprocess in a separate transaction after binding is committed.

    Failures never roll back the binding — they surface in the response summary.
    """
    empty: dict = {
        "matched": 0,
        "processed": 0,
        "skipped": 0,
        "batches": 0,
        "errors": [],
    }
    if not enabled:
        return empty
    from backend.app.acquisition.flight_ad_binding import reprocess_leads_for_ad_binding

    try:
        return await reprocess_leads_for_ad_binding(
            tenant_id=tenant_id,
            provider=provider,
            provider_ad_id=provider_ad_id,
        )
    except Exception as exc:  # noqa: BLE001 — binding already durable
        return {
            **empty,
            "errors": [{"lead_id": "*", "error": str(exc)[:240]}],
        }


@router.post(
    "/{campaign_id}/ad-bindings",
    response_model=AdBindingOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_ad_current_flight(
    campaign_id: str,
    payload: AdLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_ad(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            provider_ad_id=payload.provider_ad_id,
            provider=payload.provider,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    link = _find_ad_link(campaign, payload.provider, payload.provider_ad_id)
    reprocess = await _reprocess_after_ad_binding_commit(
        tenant_id=str(tenant_uuid),
        provider=str(link.provider) if link else payload.provider,
        provider_ad_id=str(link.provider_ad_id) if link else payload.provider_ad_id,
    )
    return AdBindingOut(
        id=str(link.id) if link else "",
        provider=str(link.provider) if link else payload.provider,
        provider_ad_id=str(link.provider_ad_id) if link else payload.provider_ad_id,
        campaign_id=str(campaign.id),
        flight_id=str(link.campaign_run_id) if link else "",
        is_active=bool(link.is_active) if link else True,
        reprocess=reprocess,
    )


@router.post(
    "/{campaign_id}/flights/{flight_id}/ad-bindings",
    response_model=AdBindingOut,
    status_code=201,
    dependencies=_WRITE,
)
async def attach_ad_on_flight(
    campaign_id: str,
    flight_id: str,
    payload: AdLinkIn,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(None, alias="X-Own-Company-Id"),
):
    db, tenant_uuid = db_tenant
    own_company_id = await _resolve_company(db, tenant_uuid, ctx, x_own_company_id)
    actor_type, actor_id = _activity_actor(ctx)
    try:
        campaign = await binding_service.attach_ad(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            provider_ad_id=payload.provider_ad_id,
            provider=payload.provider,
            own_company_id=own_company_id,
            flight_id=flight_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    link = _find_ad_link(campaign, payload.provider, payload.provider_ad_id)
    reprocess = await _reprocess_after_ad_binding_commit(
        tenant_id=str(tenant_uuid),
        provider=str(link.provider) if link else payload.provider,
        provider_ad_id=str(link.provider_ad_id) if link else payload.provider_ad_id,
    )
    return AdBindingOut(
        id=str(link.id) if link else "",
        provider=str(link.provider) if link else payload.provider,
        provider_ad_id=str(link.provider_ad_id) if link else payload.provider_ad_id,
        campaign_id=str(campaign.id),
        flight_id=str(link.campaign_run_id) if link else flight_id,
        is_active=bool(link.is_active) if link else True,
        reprocess=reprocess,
    )


@router.patch(
    "/{campaign_id}/ad-bindings/{link_id}",
    response_model=AdBindingOut,
    dependencies=_WRITE,
)
async def patch_ad_binding(
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
        campaign = await binding_service.update_ad_link(
            db,
            tenant_id=str(tenant_uuid),
            campaign_id=campaign_id,
            link_id=link_id,
            is_active=payload.is_active,
            own_company_id=own_company_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        await db.commit()
    except CampaignServiceError as exc:
        await db.rollback()
        _raise_service(exc)
    link = _find_ad_link_by_id(campaign, link_id)
    reprocess = await _reprocess_after_ad_binding_commit(
        tenant_id=str(tenant_uuid),
        provider=str(link.provider) if link else "meta",
        provider_ad_id=str(link.provider_ad_id) if link else "",
        enabled=bool(link and link.is_active),
    )
    return AdBindingOut(
        id=str(link.id) if link else link_id,
        provider=str(link.provider) if link else "meta",
        provider_ad_id=str(link.provider_ad_id) if link else "",
        campaign_id=str(campaign.id),
        flight_id=str(link.campaign_run_id) if link else "",
        is_active=bool(link.is_active) if link else False,
        reprocess=reprocess,
    )


@router.delete(
    "/{campaign_id}/ad-bindings/{link_id}",
    response_model=CampaignOut,
    dependencies=_WRITE,
)
async def detach_ad_binding(
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
        campaign = await binding_service.detach_ad(
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


def _find_ad_link(campaign: Campaign, provider: str, provider_ad_id: str):
    prov = str(provider or "meta").strip().lower()
    ad = str(provider_ad_id or "").strip()
    for flight in campaign.flights or []:
        for link in flight.ad_links or []:
            if str(link.provider).lower() == prov and str(link.provider_ad_id) == ad and link.is_active:
                return link
    return None


def _find_ad_link_by_id(campaign: Campaign, link_id: str):
    for flight in campaign.flights or []:
        for link in flight.ad_links or []:
            if str(link.id) == str(link_id):
                return link
    return None
