"""Recruitment setup readiness snapshot — canonical gates G0–G8 (Flow 1).

Scope: ``recruitment.setup.intake`` per canonical-setup-flow.md §4–§5.
Computed from tenant data; wizard progress is not source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Company,
    Funnel,
    FunnelStage,
    IntakeSourceBinding,
    IntakeSourceProfile,
    MetaAdsMap,
    MetaFormRoute,
    MetaLeadCredential,
    OwnCompany,
    Tenant,
    User,
    Vacancy,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.entity_profile import PLATFORM_TENANT_SCOPE, EpEntityProfile
from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.models.user import Role
from backend.app.models.vacancy import VacancyStatus
from backend.app.modules.intake_routing.meta_bridge import meta_external_key, meta_external_key_secondary
from backend.app.modules.intake_routing.reference import normalize_route_intent
from backend.app.modules.leads.service._helpers import _load_tenant_business_type
from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.constants.spa_paths import (
    CLIENTS as SPA_CLIENTS,
    MY_COMPANY as SPA_MY_COMPANY,
    ONBOARDING_COMPANY as SPA_ONBOARDING_COMPANY,
    SETTINGS_CANDIDATE_PROFILES as SPA_SETTINGS_CANDIDATE_PROFILES,
    SETTINGS_FUNNELS as SPA_SETTINGS_FUNNELS,
    SETTINGS_INTEGRATIONS as SPA_SETTINGS_INTEGRATIONS,
    SETTINGS_LEAD_FORMS as SPA_SETTINGS_LEAD_FORMS,
    SETTINGS_LEADS as SPA_SETTINGS_LEADS,
    SETTINGS_USERS as SPA_SETTINGS_USERS,
    SETUP_CLIENT as SPA_SETUP_CLIENT,
    SETUP_INTAKE as SPA_SETUP_INTAKE,
    SETUP_PROCESS as SPA_SETUP_PROCESS,
    SETUP_VACANCY as SPA_SETUP_VACANCY,
    VACANCY_NEW as SPA_VACANCY_NEW,
)
from backend.app.platform.next_action.contracts import NextActionCandidate, ReachabilityContext
from backend.app.platform.next_action.publisher import publish_first_reachable_next_action

SETUP_READINESS_SCOPE = "recruitment.setup.intake"

GateId = Literal["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
GateStatus = Literal["pass", "fail", "not_applicable"]
BusinessType = Literal["agency", "employer", "services"]

GATE_ORDER: tuple[GateId, ...] = ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")


@dataclass(frozen=True)
class SetupNextAction:
    gate_id: GateId
    label_key: str
    handler_ref: str


@dataclass(frozen=True)
class SetupGateResult:
    id: GateId
    status: GateStatus
    applicable: bool
    blocker_text: str | None = None


@dataclass
class SetupReadinessSnapshot:
    scope: str
    ready: bool
    business_type: BusinessType
    gates: list[SetupGateResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_action: SetupNextAction | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "ready": self.ready,
            "business_type": self.business_type,
            "gates": [
                {
                    "id": gate.id,
                    "status": gate.status,
                    "applicable": gate.applicable,
                    "blocker_text": gate.blocker_text,
                }
                for gate in self.gates
            ],
            "blockers": list(self.blockers),
            "next_action": (
                {
                    "gate_id": self.next_action.gate_id,
                    "label_key": self.next_action.label_key,
                    "handler_ref": self.next_action.handler_ref,
                }
                if self.next_action
                else None
            ),
        }


@dataclass
class _ActiveVacancyRow:
    id: str
    funnel_id: str | None
    funnel_stage_count: int
    entity_profile_code: str | None
    entity_profile_active: bool


@dataclass
class _IntakeSourceRow:
    profile_id: str
    provider: str
    route_intent: str
    default_assignee_id: str | None
    entity_profile_code: str | None
    entity_profile_active: bool
    pipeline_preset: str | None
    is_active: bool


@dataclass
class SetupReadinessContext:
    tenant_active: bool
    admin_user_count: int
    operating_company_count: int
    business_type: BusinessType
    clients_count: int
    manual_intake_declared: bool
    active_vacancies: list[_ActiveVacancyRow]
    intake_sources: list[_IntakeSourceRow]
    meta_credentials_active: int
    published_lead_forms: int
    dual_routing_conflicts: list[str]
    legacy_meta_routes_without_binding: int
    meta_ads_map_count: int
    tenant_status: str | None = None


def _normalize_company_role(extra: object) -> str | None:
    if not isinstance(extra, dict):
        return None
    raw = (
        extra.get("company_role")
        or extra.get("company_kind")
        or extra.get("kind")
        or extra.get("entity_type")
    )
    normalized = str(raw or "").strip().lower()
    if normalized in {"operating", "client", "counterparty"}:
        return normalized
    return None


def _normalize_tenant_status(raw: object) -> str | None:
    if raw is None:
        return None
    if hasattr(raw, "value"):
        value = str(getattr(raw, "value")).strip().lower()
        return value or None
    text = str(raw).strip()
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    text = text.lower()
    return text or None


def _manual_intake_declared(settings: dict[str, Any] | None) -> bool:
    if not isinstance(settings, dict):
        return False
    onboarding = settings.get("onboarding")
    setup = settings.get("setup")
    ob = onboarding if isinstance(onboarding, dict) else {}
    st = setup if isinstance(setup, dict) else {}
    return bool(
        ob.get("manual_intake_policy")
        or ob.get("manual_intake_declared")
        or st.get("manual_intake_declared")
    )


def recruitment_activation_lock_applies(settings: dict[str, Any] | None) -> bool:
    """True only for tenants enrolled in post-M1 setup activation lock (new self-service signups)."""
    if not isinstance(settings, dict):
        return False
    setup = settings.get("setup")
    if not isinstance(setup, dict):
        return False
    return setup.get("recruitment_activation_lock") is True


def _gate_applicable(gate_id: GateId, business_type: BusinessType) -> bool:
    if gate_id in ("G0", "G1", "G6", "G7", "G8"):
        return True
    if gate_id == "G2":
        return business_type == "agency"
    if gate_id in ("G3", "G4", "G5"):
        return business_type in ("agency", "employer")
    return True


def _vacancy_has_funnel(v: _ActiveVacancyRow) -> bool:
    return bool(v.funnel_id) and v.funnel_stage_count >= 1


def _vacancy_has_profile(v: _ActiveVacancyRow) -> bool:
    return bool(v.entity_profile_code) and v.entity_profile_active


def _has_hiring_context(ctx: SetupReadinessContext) -> bool:
    return any(_vacancy_has_funnel(v) for v in ctx.active_vacancies)


def _has_requirement_profile(ctx: SetupReadinessContext) -> bool:
    return any(_vacancy_has_profile(v) for v in ctx.active_vacancies)


def _source_connected(ctx: SetupReadinessContext) -> bool:
    if ctx.manual_intake_declared:
        return True
    active_profiles = [s for s in ctx.intake_sources if s.is_active]
    if active_profiles:
        return True
    if ctx.meta_credentials_active > 0:
        return True
    if ctx.published_lead_forms > 0:
        return True
    return False


def _profile_route_complete(source: _IntakeSourceRow, ctx: SetupReadinessContext) -> bool:
    if not source.default_assignee_id:
        return False
    if not source.entity_profile_code or not source.entity_profile_active:
        return False
    intent = normalize_route_intent(source.route_intent)
    if intent == RouteIntent.candidate_application.value:
        return _has_hiring_context(ctx)
    return bool(source.pipeline_preset or intent in {
        RouteIntent.sales_inquiry.value,
        RouteIntent.service_request.value,
        RouteIntent.partner_inquiry.value,
    })


def _routes_complete(ctx: SetupReadinessContext) -> bool:
    if ctx.manual_intake_declared and not ctx.intake_sources:
        return _has_hiring_context(ctx) if ctx.business_type in ("agency", "employer") else True
    active_sources = [s for s in ctx.intake_sources if s.is_active and s.provider != IntakeProvider.manual.value]
    if not active_sources:
        if ctx.manual_intake_declared:
            return _has_hiring_context(ctx) if ctx.business_type in ("agency", "employer") else True
        if ctx.meta_credentials_active > 0 or ctx.published_lead_forms > 0:
            return False
        return True
    return all(_profile_route_complete(s, ctx) for s in active_sources)


def _no_dual_routing(ctx: SetupReadinessContext) -> bool:
    if ctx.dual_routing_conflicts:
        return False
    if ctx.legacy_meta_routes_without_binding > 0:
        return False
    if ctx.meta_ads_map_count > 0 and ctx.intake_sources and ctx.legacy_meta_routes_without_binding == 0:
        meta_bindings = [s for s in ctx.intake_sources if s.provider == IntakeProvider.meta.value and s.is_active]
        if not meta_bindings and ctx.meta_ads_map_count > 0:
            return False
    return True


def _evaluate_gate(gate_id: GateId, ctx: SetupReadinessContext) -> SetupGateResult:
    applicable = _gate_applicable(gate_id, ctx.business_type)
    if not applicable:
        return SetupGateResult(id=gate_id, status="not_applicable", applicable=False)

    if gate_id == "G0":
        if ctx.tenant_active and ctx.admin_user_count >= 1:
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Tenant inactive or no administrator user"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G1":
        if ctx.operating_company_count >= 1 and ctx.business_type in ("agency", "employer", "services"):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Operating company or business type missing"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G2":
        if ctx.clients_count >= 1:
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "No client company configured"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G3":
        if ctx.active_vacancies:
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "No active vacancy"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G4":
        if _has_hiring_context(ctx):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Vacancy not linked to funnel with stages"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G5":
        if _has_requirement_profile(ctx):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Requirement profile (entity profile) not resolved"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G6":
        if _source_connected(ctx):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "No working candidate intake channel configured"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G7":
        if _routes_complete(ctx):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Intake route incomplete (assignee, profile, hiring context)"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    if gate_id == "G8":
        if _no_dual_routing(ctx):
            return SetupGateResult(id=gate_id, status="pass", applicable=True)
        blocker = "Conflicting legacy and intake routing detected"
        return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text=blocker)

    return SetupGateResult(id=gate_id, status="fail", applicable=True, blocker_text="Unknown gate")


NEXT_ACTIONS: dict[GateId, SetupNextAction] = {
    "G0": SetupNextAction("G0", "setup.gate.g0.admin_user", SPA_SETTINGS_USERS),
    "G1": SetupNextAction("G1", "setup.gate.g1.company", SPA_ONBOARDING_COMPANY),
    "G2": SetupNextAction("G2", "setup.gate.g2.client", SPA_SETUP_CLIENT),
    "G3": SetupNextAction("G3", "setup.gate.g3.vacancy", SPA_SETUP_VACANCY),
    "G4": SetupNextAction("G4", "setup.gate.g4.funnel", SPA_SETUP_PROCESS),
    "G5": SetupNextAction("G5", "setup.gate.g5.profile", SPA_SETUP_PROCESS),
    "G6": SetupNextAction("G6", "setup.gate.g6.intake", SPA_SETUP_INTAKE),
    "G7": SetupNextAction("G7", "setup.gate.g7.intake", SPA_SETUP_INTAKE),
    "G8": SetupNextAction("G8", "setup.gate.g8.intake", SPA_SETUP_INTAKE),
}


def evaluate_setup_readiness_from_context(ctx: SetupReadinessContext) -> SetupReadinessSnapshot:
    """Pure gate evaluation — used by API and unit tests."""
    gates = [_evaluate_gate(gate_id, ctx) for gate_id in GATE_ORDER]
    blockers = [g.blocker_text for g in gates if g.status == "fail" and g.blocker_text]
    ready = all(g.status in ("pass", "not_applicable") for g in gates)
    gates_by_id = {g.id: g for g in gates}
    gate_actions: dict[GateId, NextActionCandidate] = {
        gate_id: NextActionCandidate(
            gate_id=action.gate_id,
            label_key=action.label_key,
            handler_ref=action.handler_ref,
        )
        for gate_id, action in NEXT_ACTIONS.items()
    }
    reachability_ctx = ReachabilityContext(
        setup_ready=ready,
        tenant_status=ctx.tenant_status,
    )
    published = publish_first_reachable_next_action(
        gate_order=GATE_ORDER,
        gates_by_id=gates_by_id,
        gate_actions=gate_actions,
        reachability_ctx=reachability_ctx,
    )
    next_action: SetupNextAction | None = None
    if published is not None:
        next_action = SetupNextAction(
            published.gate_id,  # type: ignore[arg-type]
            published.label_key,
            published.handler_ref,
        )
    return SetupReadinessSnapshot(
        scope=SETUP_READINESS_SCOPE,
        ready=ready,
        business_type=ctx.business_type,
        gates=gates,
        blockers=blockers,
        next_action=next_action,
    )


async def _entity_profile_is_active(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str | None,
    cache: dict[str, bool],
) -> bool:
    code = str(profile_code or "").strip()
    if not code:
        return False
    if code in cache:
        return cache[code]
    row = await db.execute(
        select(EpEntityProfile.status)
        .where(
            EpEntityProfile.profile_code == code,
            EpEntityProfile.status == "active",
            or_(
                EpEntityProfile.tenant_id == str(tenant_id),
                EpEntityProfile.tenant_id == PLATFORM_TENANT_SCOPE,
            ),
        )
        .limit(1)
    )
    active = row.scalar_one_or_none() == "active"
    cache[code] = active
    return active


async def _load_active_vacancies(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    profile_cache: dict[str, bool],
) -> list[_ActiveVacancyRow]:
    stmt = select(Vacancy).where(
        Vacancy.tenant_id == tenant_id,
        Vacancy.is_archived.is_(False),
        Vacancy.is_active.is_(True),
        Vacancy.status.in_((VacancyStatus.open.value, VacancyStatus.on_hold.value)),
    )
    if own_company_id:
        stmt = stmt.where(Vacancy.own_company_id == own_company_id)
    vacancies = list((await db.execute(stmt)).scalars().all())
    rows: list[_ActiveVacancyRow] = []
    for vacancy in vacancies:
        stage_count = 0
        if vacancy.funnel_id:
            funnel = await db.get(Funnel, vacancy.funnel_id)
            if funnel is not None and str(funnel.tenant_id) == tenant_id:
                stage_count = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(FunnelStage)
                            .where(FunnelStage.funnel_id == funnel.id)
                        )
                    ).scalar_one()
                    or 0
                )
        entity_code, _, _ = await resolve_entity_profile_hints_from_vacancy(
            db,
            tenant_id=tenant_id,
            vacancy_id=str(vacancy.id),
        )
        entity_active = await _entity_profile_is_active(
            db,
            tenant_id=tenant_id,
            profile_code=entity_code,
            cache=profile_cache,
        )
        rows.append(
            _ActiveVacancyRow(
                id=str(vacancy.id),
                funnel_id=str(vacancy.funnel_id) if vacancy.funnel_id else None,
                funnel_stage_count=stage_count,
                entity_profile_code=entity_code,
                entity_profile_active=entity_active,
            )
        )
    return rows


async def _load_intake_sources(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    profile_cache: dict[str, bool],
) -> list[_IntakeSourceRow]:
    stmt = select(IntakeSourceProfile).where(IntakeSourceProfile.tenant_id == tenant_id)
    if own_company_id:
        stmt = stmt.where(IntakeSourceProfile.own_company_id == own_company_id)
    profiles = list((await db.execute(stmt)).scalars().all())
    rows: list[_IntakeSourceRow] = []
    for profile in profiles:
        entity_code = str(getattr(profile, "entity_profile_code", None) or "").strip() or None
        entity_active = await _entity_profile_is_active(
            db,
            tenant_id=tenant_id,
            profile_code=entity_code,
            cache=profile_cache,
        )
        rows.append(
            _IntakeSourceRow(
                profile_id=str(profile.id),
                provider=str(profile.provider or "").strip().lower(),
                route_intent=str(profile.route_intent or RouteIntent.unknown.value),
                default_assignee_id=str(profile.default_assignee_id or "").strip() or None,
                entity_profile_code=entity_code,
                entity_profile_active=entity_active,
                pipeline_preset=str(profile.pipeline_preset or "").strip() or None,
                is_active=bool(profile.is_active),
            )
        )
    return rows


async def _count_admin_users(db: AsyncSession, tenant_id: str) -> int:
    row = await db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.role == Role.administrator,
        )
    )
    return int(row.scalar_one() or 0)


async def _detect_dual_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> tuple[list[str], int]:
    conflicts: list[str] = []
    legacy_without_binding = 0
    meta_routes = list(
        (
            await db.execute(
                select(MetaFormRoute).where(
                    MetaFormRoute.tenant_id == tenant_id,
                    MetaFormRoute.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    for route in meta_routes:
        binding = (
            await db.execute(
                select(IntakeSourceBinding.id)
                .where(
                    IntakeSourceBinding.tenant_id == tenant_id,
                    IntakeSourceBinding.provider == IntakeProvider.meta.value,
                    IntakeSourceBinding.external_key == meta_external_key(route.form_id),
                    IntakeSourceBinding.external_key_secondary == meta_external_key_secondary(route.page_id),
                    IntakeSourceBinding.is_active.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if binding is None:
            legacy_without_binding += 1
            conflicts.append(f"meta_form:{route.form_id}:missing_intake_binding")
    return conflicts, legacy_without_binding


async def build_setup_readiness_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
) -> SetupReadinessContext:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    tenant_active = bool(tenant and getattr(tenant, "is_active", True))
    tenant_status = _normalize_tenant_status(getattr(tenant, "status", None) if tenant else None)
    settings = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else {}

    own_company_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(OwnCompany)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            )
        ).scalar_one()
        or 0
    )
    if own_company_count == 0:
        legacy_company_count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Company)
                    .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
                )
            ).scalar_one()
            or 0
        )
        if legacy_company_count > 0:
            own_company_count = 1

    company_extra_rows = await db.execute(
        select(Company.extra).where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
    )
    clients_count = 0
    for extra in company_extra_rows.scalars().all():
        if _normalize_company_role(extra) == "client":
            clients_count += 1

    business_type_raw = await _load_tenant_business_type(db, tenant_id, own_company_id)
    business_type: BusinessType = (
        business_type_raw if business_type_raw in ("agency", "employer", "services") else "agency"
    )

    profile_cache: dict[str, bool] = {}
    active_vacancies = await _load_active_vacancies(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        profile_cache=profile_cache,
    )
    intake_sources = await _load_intake_sources(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        profile_cache=profile_cache,
    )

    meta_credentials_active = int(
        (
            await db.execute(
                select(func.count())
                .select_from(MetaLeadCredential)
                .where(
                    MetaLeadCredential.tenant_id == tenant_id,
                    MetaLeadCredential.status == "active",
                )
            )
        ).scalar_one()
        or 0
    )
    published_lead_forms = int(
        (
            await db.execute(
                select(func.count())
                .select_from(TenantLeadForm)
                .where(
                    TenantLeadForm.tenant_id == tenant_id,
                    TenantLeadForm.is_active.is_(True),
                    TenantLeadForm.public_slug.isnot(None),
                    TenantLeadForm.public_slug != "",
                )
            )
        ).scalar_one()
        or 0
    )
    meta_ads_map_count = int(
        (
            await db.execute(
                select(func.count()).select_from(MetaAdsMap).where(MetaAdsMap.tenant_id == tenant_id)
            )
        ).scalar_one()
        or 0
    )
    dual_conflicts, legacy_without_binding = await _detect_dual_routing(db, tenant_id=tenant_id)

    return SetupReadinessContext(
        tenant_active=tenant_active,
        tenant_status=tenant_status,
        admin_user_count=await _count_admin_users(db, tenant_id),
        operating_company_count=own_company_count,
        business_type=business_type,
        clients_count=clients_count,
        manual_intake_declared=_manual_intake_declared(settings),
        active_vacancies=active_vacancies,
        intake_sources=intake_sources,
        meta_credentials_active=meta_credentials_active,
        published_lead_forms=published_lead_forms,
        dual_routing_conflicts=dual_conflicts,
        legacy_meta_routes_without_binding=legacy_without_binding,
        meta_ads_map_count=meta_ads_map_count,
    )


async def evaluate_recruitment_setup_readiness(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
) -> SetupReadinessSnapshot:
    ctx = await build_setup_readiness_context(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
    )
    return evaluate_setup_readiness_from_context(ctx)


__all__ = [
    "SETUP_READINESS_SCOPE",
    "SetupGateResult",
    "SetupNextAction",
    "SetupReadinessContext",
    "SetupReadinessSnapshot",
    "build_setup_readiness_context",
    "evaluate_recruitment_setup_readiness",
    "evaluate_setup_readiness_from_context",
    "recruitment_activation_lock_applies",
]
