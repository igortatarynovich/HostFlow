"""Onboarding and activation status for self-serve CRM flow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import Company, Lead, OwnCompany, Reminder, ServiceOrder, Tenant, Vacancy
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.constants.spa_paths import LEADS
from backend.app.services.onboarding_demo_seed import (
    clear_onboarding_demo_data,
    onboarding_demo_still_active,
    seed_onboarding_demo_if_needed,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# IA v2 / Phase 2 — onboarding wizard progress (5-step «first lead in 5 min»)
# ---------------------------------------------------------------------------

WIZARD_STEP_KEYS = (
    "type",  # business type / company creation
    "channel",  # connect first lead intake channel
    "client",  # create first client company (or skip for employer)
    "vacancy",  # create first vacancy (or skip for services)
    "first_lead",  # final: see demo lead with NBA
)
WizardStepKey = Literal["type", "channel", "client", "vacancy", "first_lead"]
LEAD_INTAKE_CHANNEL_KEYS = ("meta", "public_intake", "webhook", "manual", "skipped")


class OnboardingClearDemoOut(BaseModel):
    reminders: int
    leads: int
    candidates: int
    companies: int


class OnboardingStatusOut(BaseModel):
    business_type: str
    onboarding_required: bool
    activation_required: bool
    demo_seeded: bool = False
    companies_count: int
    leads_count: int
    vacancies_count: int
    service_orders_count: int
    reminders_count: int
    clients_count: int
    counterparties_count: int
    steps: dict[str, bool]


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


@router.get("/status", response_model=OnboardingStatusOut)
async def get_onboarding_status(
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    own_company_id: str | None = Depends(resolve_active_own_company_id_optional),
):
    """Onboarding/activation state for path `signup -> company -> first value`."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant_row = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).limit(1)
    )
    tenant = tenant_row.scalar_one_or_none()

    own_company_count_row = await db.execute(
        select(func.count())
        .select_from(OwnCompany)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
    )
    # Keep legacy client/counterparty classification from Company.extra for now.
    company_extra_rows = await db.execute(
        select(Company.extra).where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
    )
    lead_count_row = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id)
    )
    vacancy_count_row = await db.execute(
        select(func.count()).select_from(Vacancy).where(Vacancy.tenant_id == tenant_id)
    )
    service_order_count_row = await db.execute(
        select(func.count()).select_from(ServiceOrder).where(ServiceOrder.tenant_id == tenant_id)
    )
    reminder_count_row = await db.execute(
        select(func.count()).select_from(Reminder).where(Reminder.tenant_id == tenant_id)
    )

    total_companies_count = int(own_company_count_row.scalar_one() or 0)
    operating_companies_count = total_companies_count
    clients_count = 0
    counterparties_count = 0
    for extra in company_extra_rows.scalars().all():
        kind = _normalize_company_role(extra)
        if kind == "client":
            clients_count += 1
        elif kind == "counterparty":
            counterparties_count += 1

    # Backward compatibility: if tenant has legacy operating companies but no OwnCompany yet.
    if operating_companies_count == 0:
        legacy_company_count_row = await db.execute(
            select(func.count())
            .select_from(Company)
            .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
        )
        legacy_total = int(legacy_company_count_row.scalar_one() or 0)
        if legacy_total > 0:
            operating_companies_count = 1
            total_companies_count = 1

    leads_count = int(lead_count_row.scalar_one() or 0)
    vacancies_count = int(vacancy_count_row.scalar_one() or 0)
    service_orders_count = int(service_order_count_row.scalar_one() or 0)
    reminders_count = int(reminder_count_row.scalar_one() or 0)

    # Prefer operating profile type from Company.extra (operating company).
    # OwnCompany.extra may be empty/stale (only affects billing/legal brand),
    # while Leads behavior is controlled by the operating profile's company_type.
    raw_business_type = None
    try:
        rows = await db.execute(
            select(Company.extra)
            .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
            .order_by(Company.created_at.asc())
            .limit(50)
        )
        for (extra,) in rows.all():
            if not isinstance(extra, dict):
                continue
            role = str(extra.get("company_role") or "").strip().lower()
            if role != "operating":
                continue
            ct = extra.get("company_type") or extra.get("business_type") or extra.get("company_kind") or extra.get("kind")
            if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                raw_business_type = ct.strip().lower()
                break
    except Exception:
        raw_business_type = None

    if raw_business_type is None:
        raw_business_type = (
            (tenant.settings or {}).get("business_type")
            if tenant is not None and isinstance(getattr(tenant, "settings", None), dict)
            else None
        )

    business_type = str(raw_business_type or "").strip().lower()
    if business_type not in ("agency", "employer", "services"):
        tenant_type_value = str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", ""))).strip().lower()
        if tenant_type_value == "company":
            business_type = "employer"
        else:
            business_type = "agency"

    onboarding_required = operating_companies_count == 0
    steps = {
        "company_created": operating_companies_count > 0,
        "first_lead_created": leads_count > 0,
        "first_vacancy_created": vacancies_count > 0,
        "first_service_order_created": service_orders_count > 0,
        "first_client_created": clients_count > 0,
        "next_action_created": reminders_count > 0,
    }
    if business_type == "employer":
        type_specific_ready = steps["first_vacancy_created"]
    elif business_type == "services":
        # Services tenants can get first value either by creating first client manually
        # or by receiving first ad lead (potential client) into Leads inbox.
        type_specific_ready = steps["first_client_created"] or steps["first_lead_created"]
    else:
        type_specific_ready = steps["first_lead_created"]
    activation_required = steps["company_created"] and not (
        type_specific_ready and steps["next_action_created"]
    )

    demo_seeded = bool(onboarding_demo_still_active(tenant))

    return OnboardingStatusOut(
        business_type=business_type,
        onboarding_required=onboarding_required,
        activation_required=activation_required,
        demo_seeded=demo_seeded,
        companies_count=operating_companies_count,
        leads_count=leads_count,
        vacancies_count=vacancies_count,
        service_orders_count=service_orders_count,
        reminders_count=reminders_count,
        clients_count=clients_count,
        counterparties_count=counterparties_count,
        steps=steps,
    )


@router.post(
    "/clear-demo-data",
    response_model=OnboardingClearDemoOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def post_clear_demo_data(
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """Remove onboarding sample leads/candidates/company and related reminders (§2.2)."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        summary = await clear_onboarding_demo_data(db, tenant_id=tenant_id)
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear demo data",
        ) from exc
    return OnboardingClearDemoOut(**summary)


class OnboardingDemoSeedOut(BaseModel):
    seeded: bool
    already_active: bool
    summary: dict[str, Any] = Field(default_factory=dict)
    business_type: str
    own_company_id: str | None = None


@router.post(
    "/demo/seed",
    response_model=OnboardingDemoSeedOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def post_seed_onboarding_demo(
    current_user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
    own_company_id: str | None = Depends(resolve_active_own_company_id_optional),
):
    """Phase 2 #4 — explicit «load demo data» CTA.

    Seeds the same sample leads/candidates pack as company creation
    (`seed_onboarding_demo_if_needed`). Idempotent at the seeder level —
    re-calling for an already-seeded tenant returns ``already_active=True``
    without inserting duplicates. Use ``POST /onboarding/clear-demo-data``
    first to wipe the pack before reseeding.
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    raw_business_type: str | None = None
    rows = await db.execute(
        select(Company.extra)
        .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
        .order_by(Company.created_at.asc())
        .limit(50)
    )
    for (extra,) in rows.all():
        if not isinstance(extra, dict):
            continue
        role = str(extra.get("company_role") or "").strip().lower()
        if role != "operating":
            continue
        ct = (
            extra.get("company_type")
            or extra.get("business_type")
            or extra.get("company_kind")
            or extra.get("kind")
        )
        if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
            raw_business_type = ct.strip().lower()
            break
    if raw_business_type is None and isinstance(getattr(tenant, "settings", None), dict):
        candidate = (tenant.settings or {}).get("business_type")
        if isinstance(candidate, str) and candidate.strip().lower() in {"agency", "employer", "services"}:
            raw_business_type = candidate.strip().lower()
    business_type = (raw_business_type or "agency").strip().lower()

    resolved_own_company = (own_company_id or "").strip()
    if not resolved_own_company:
        own_row = await db.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        first = own_row.scalar_one_or_none()
        if first is not None:
            resolved_own_company = str(first)

    if not resolved_own_company:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "no_own_company",
                "message": "Create your operating company before seeding the demo pack.",
            },
        )

    actor_id = str(current_user.sub).strip() if getattr(current_user, "sub", None) else None
    already = bool(onboarding_demo_still_active(tenant))
    summary: dict[str, Any] = {}
    try:
        summary = await seed_onboarding_demo_if_needed(
            db,
            tenant_id=tenant_id,
            own_company_id=resolved_own_company,
            business_type=business_type,
            assignee_user_id=actor_id,
        )
        await db.commit()
    except HTTPException:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to seed demo data",
        ) from exc

    return OnboardingDemoSeedOut(
        seeded=bool(summary),
        already_active=already and not summary,
        summary=summary or {},
        business_type=business_type,
        own_company_id=resolved_own_company,
    )


# ---------------------------------------------------------------------------
# Wizard progress — Phase 2 «first value in 5 minutes»
# ---------------------------------------------------------------------------


class WizardStateOut(BaseModel):
    current_step: str
    completed_steps: list[str]
    channel: str | None = None
    skipped_steps: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    step_data: dict[str, Any] = Field(default_factory=dict)
    finished: bool = False


class WizardStepIn(BaseModel):
    step: WizardStepKey
    completed: bool = True
    skipped: bool = False
    next_step: WizardStepKey | None = None
    channel: str | None = None
    data: dict[str, Any] | None = None
    finished: bool = False


def _wizard_blob(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None or not isinstance(tenant.settings, dict):
        return {}
    ob = tenant.settings.get("onboarding")
    if not isinstance(ob, dict):
        return {}
    blob = ob.get("wizard")
    return dict(blob) if isinstance(blob, dict) else {}


def _serialize_wizard(blob: dict[str, Any]) -> WizardStateOut:
    completed = [str(s) for s in (blob.get("completed_steps") or []) if str(s) in WIZARD_STEP_KEYS]
    skipped = [str(s) for s in (blob.get("skipped_steps") or []) if str(s) in WIZARD_STEP_KEYS]
    raw_step = str(blob.get("current_step") or "type").lower()
    if raw_step not in WIZARD_STEP_KEYS:
        raw_step = "type"
    raw_channel = str(blob.get("channel") or "").lower() or None
    if raw_channel and raw_channel not in LEAD_INTAKE_CHANNEL_KEYS:
        raw_channel = None
    step_data = blob.get("step_data") if isinstance(blob.get("step_data"), dict) else {}
    return WizardStateOut(
        current_step=raw_step,
        completed_steps=completed,
        channel=raw_channel,
        skipped_steps=skipped,
        started_at=str(blob.get("started_at") or "") or None,
        completed_at=str(blob.get("completed_at") or "") or None,
        step_data=dict(step_data),
        finished=bool(blob.get("finished")),
    )


async def _persist_wizard(db: AsyncSession, tenant_id: str, blob: dict[str, Any]) -> dict[str, Any]:
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    settings: dict[str, Any] = (
        dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    )
    onboarding = (
        dict(settings.get("onboarding")) if isinstance(settings.get("onboarding"), dict) else {}
    )
    onboarding["wizard"] = blob
    settings["onboarding"] = onboarding
    tenant.settings = settings
    db.add(tenant)
    await db.flush()
    await db.commit()
    return blob


@router.get("/wizard", response_model=WizardStateOut)
async def get_onboarding_wizard(
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """Read current state of the onboarding wizard (5-step Phase 2 flow)."""
    db, tenant_uuid = db_tenant
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == str(tenant_uuid)).limit(1))
    ).scalar_one_or_none()
    blob = _wizard_blob(tenant)
    return _serialize_wizard(blob)


@router.post("/wizard/step", response_model=WizardStateOut)
async def post_onboarding_wizard_step(
    payload: WizardStepIn,
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """Persist progress for one wizard step.

    The frontend calls this after the user takes the action for a step
    (creates a company, picks a channel, creates a vacancy, etc) — server
    writes into ``tenant.settings.onboarding.wizard`` so the user can resume
    later from the same point.
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    blob = dict(_wizard_blob(tenant))
    if not blob.get("started_at"):
        blob["started_at"] = datetime.now(timezone.utc).isoformat()

    completed = [str(s) for s in (blob.get("completed_steps") or [])]
    skipped = [str(s) for s in (blob.get("skipped_steps") or [])]

    step_key = payload.step
    if payload.completed and step_key not in completed:
        completed.append(step_key)
    if payload.skipped and step_key not in skipped:
        skipped.append(step_key)
        # Skipped steps still count as «handled» so the user can move forward.
        if step_key not in completed:
            completed.append(step_key)
    blob["completed_steps"] = completed
    blob["skipped_steps"] = skipped

    if payload.channel:
        ch = payload.channel.strip().lower()
        if ch in LEAD_INTAKE_CHANNEL_KEYS:
            blob["channel"] = ch

    if payload.data is not None:
        sd = blob.get("step_data") if isinstance(blob.get("step_data"), dict) else {}
        sd[step_key] = payload.data
        blob["step_data"] = sd

    if payload.next_step:
        blob["current_step"] = payload.next_step
    elif step_key in WIZARD_STEP_KEYS:
        idx = WIZARD_STEP_KEYS.index(step_key)
        nxt = WIZARD_STEP_KEYS[idx + 1] if idx + 1 < len(WIZARD_STEP_KEYS) else step_key
        blob["current_step"] = nxt

    if payload.finished:
        blob["finished"] = True
        blob["completed_at"] = datetime.now(timezone.utc).isoformat()

    await _persist_wizard(db, tenant_id, blob)
    return _serialize_wizard(blob)


# ---------------------------------------------------------------------------
# First lead snapshot — what step 5 of the wizard renders
# ---------------------------------------------------------------------------


class WizardFirstLeadOut(BaseModel):
    has_lead: bool
    lead_id: str | None = None
    title: str | None = None
    source: str | None = None
    stage: str | None = None
    created_at: str | None = None
    is_demo: bool = False
    nba_title: str | None = None
    nba_due_at: str | None = None
    nba_id: str | None = None
    leads_url: str = Field(default=f"{LEADS}/")
    demo_seeded: bool = False


@router.get("/wizard/first-lead", response_model=WizardFirstLeadOut)
async def get_onboarding_wizard_first_lead(
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """Return the most recent lead + its next-best-action for the wizard final step.

    Used by ``OnboardingWizardPage.tsx`` step 5 to render «here is your first
    lead with the NBA the system suggests». Falls back gracefully when the
    tenant has no leads yet (the frontend then renders the demo-seed CTA).
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    ).scalar_one_or_none()
    demo_active = bool(onboarding_demo_still_active(tenant))

    lead_row = await db.execute(
        select(Lead)
        .where(Lead.tenant_id == tenant_id)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    lead = lead_row.scalar_one_or_none()
    if lead is None:
        return WizardFirstLeadOut(has_lead=False, demo_seeded=demo_active)

    title: str | None = None
    payload = lead.payload if isinstance(getattr(lead, "payload", None), dict) else {}
    normalized = lead.normalized if isinstance(getattr(lead, "normalized", None), dict) else {}
    for cand in (
        normalized.get("full_name"),
        normalized.get("name"),
        normalized.get("company"),
        payload.get("full_name"),
        payload.get("name"),
        payload.get("company_name"),
        payload.get("company"),
    ):
        if isinstance(cand, str) and cand.strip():
            title = cand.strip()
            break
    if not title:
        title = f"Lead {str(lead.id)[:8]}"

    is_demo = (str(getattr(lead, "source", "") or "").strip() == "onboarding_demo") or bool(
        (payload or {}).get("demo")
    )

    nba_title: str | None = None
    nba_due: str | None = None
    nba_id: str | None = None
    reminder_row = await db.execute(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "lead",
            Reminder.entity_id == str(lead.id),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    reminder = reminder_row.scalar_one_or_none()
    if reminder is not None:
        nba_id = str(reminder.id)
        nba_title = (
            getattr(reminder, "title", None)
            or getattr(reminder, "type", None)
            or "Follow up"
        )
        if reminder.due_at is not None:
            try:
                nba_due = reminder.due_at.isoformat()
            except Exception:
                nba_due = None

    return WizardFirstLeadOut(
        has_lead=True,
        lead_id=str(lead.id),
        title=title,
        source=str(getattr(lead, "source", "") or "") or None,
        stage=str(getattr(lead, "stage", "") or "") or None,
        created_at=lead.created_at.isoformat() if getattr(lead, "created_at", None) else None,
        is_demo=is_demo,
        nba_title=nba_title,
        nba_due_at=nba_due,
        nba_id=nba_id,
        leads_url=f"{LEADS}/?focus={lead.id}",
        demo_seeded=demo_active,
    )
