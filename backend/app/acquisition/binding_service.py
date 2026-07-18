"""CampaignRun ↔ Form / Intake Source bindings — Stage 3B (ADR-024).

CampaignRun *uses* Form and IntakeSourceProfile; it does not own them.
Association rows store only FK + role + is_active (no provider/external_ref snapshots).
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.campaign_service import (
    CampaignServiceError,
    _reload_campaign,
    get_campaign,
)
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.tenant_lead_form import TenantLeadForm


def _normalize_role(role: str | None) -> str:
    role_n = str(role or "primary").strip().lower() or "primary"
    if role_n not in {"primary", "secondary"}:
        raise CampaignServiceError("role must be 'primary' or 'secondary'", status_code=422)
    return role_n


def _is_primary_unique_violation(exc: BaseException) -> bool:
    msg = str(getattr(exc, "orig", None) or exc).lower()
    return (
        "uq_acq_campaign_run_forms_one_active_primary" in msg
        or "uq_acq_campaign_run_intake_sources_one_active_primary" in msg
        or "one_active_primary" in msg
    )


async def _resolve_flight(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None,
    flight_id: str | None,
) -> tuple[Campaign, CampaignRun]:
    campaign = await get_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )
    resolved_id = str(flight_id or "").strip() or str(campaign.current_flight_id or "").strip()
    if not resolved_id:
        raise CampaignServiceError("Campaign has no current Flight", status_code=422)
    flight = next((f for f in (campaign.flights or []) if f.id == resolved_id), None)
    if flight is None:
        raise CampaignServiceError("Flight not found for Campaign", status_code=404)
    return campaign, flight


async def _assert_no_active_primary_form(db: AsyncSession, *, campaign_run_id: str) -> None:
    row = await db.execute(
        select(CampaignRunForm.id).where(
            CampaignRunForm.campaign_run_id == campaign_run_id,
            CampaignRunForm.role == "primary",
            CampaignRunForm.is_active.is_(True),
        )
    )
    if row.scalar_one_or_none() is not None:
        raise CampaignServiceError(
            "Flight already has an active primary Form",
            status_code=422,
        )


async def _assert_no_active_primary_intake_source(
    db: AsyncSession, *, campaign_run_id: str
) -> None:
    row = await db.execute(
        select(CampaignRunIntakeSource.id).where(
            CampaignRunIntakeSource.campaign_run_id == campaign_run_id,
            CampaignRunIntakeSource.role == "primary",
            CampaignRunIntakeSource.is_active.is_(True),
        )
    )
    if row.scalar_one_or_none() is not None:
        raise CampaignServiceError(
            "Flight already has an active primary Intake Source",
            status_code=422,
        )


async def attach_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    form_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
    role: str = "primary",
) -> Campaign:
    _, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    role_n = _normalize_role(role)
    fid = str(form_id or "").strip()
    if not fid:
        raise CampaignServiceError("form_id is required", status_code=422)

    form_row = await db.execute(
        select(TenantLeadForm).where(
            TenantLeadForm.id == fid,
            TenantLeadForm.tenant_id == tenant_id,
        )
    )
    form = form_row.scalar_one_or_none()
    if form is None:
        raise CampaignServiceError("Form not found", status_code=404)
    if not form.is_active or str(form.lifecycle_status or "").lower() == "archived":
        raise CampaignServiceError("Form is inactive", status_code=422)

    existing = await db.execute(
        select(CampaignRunForm.id).where(
            CampaignRunForm.campaign_run_id == flight.id,
            CampaignRunForm.form_id == fid,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise CampaignServiceError("Form already linked to this Flight", status_code=422)

    if role_n == "primary":
        await _assert_no_active_primary_form(db, campaign_run_id=flight.id)

    flight.form_links.append(
        CampaignRunForm(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_run_id=flight.id,
            form_id=fid,
            role=role_n,
            is_active=True,
        )
    )
    try:
        await db.flush()
    except IntegrityError as exc:
        if _is_primary_unique_violation(exc):
            raise CampaignServiceError(
                "Flight already has an active primary Form",
                status_code=422,
            ) from exc
        raise
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )


async def update_form_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    link_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
    is_active: bool | None = None,
    role: str | None = None,
) -> Campaign:
    _, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    row = await db.execute(
        select(CampaignRunForm).where(
            CampaignRunForm.id == link_id,
            CampaignRunForm.campaign_run_id == flight.id,
            CampaignRunForm.tenant_id == tenant_id,
        )
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise CampaignServiceError("Form link not found", status_code=404)

    next_role = _normalize_role(role) if role is not None else link.role
    next_active = link.is_active if is_active is None else bool(is_active)

    becoming_active_primary = next_role == "primary" and next_active
    was_active_primary = link.role == "primary" and link.is_active
    if becoming_active_primary and not was_active_primary:
        await _assert_no_active_primary_form(db, campaign_run_id=flight.id)

    link.role = next_role
    link.is_active = next_active
    try:
        await db.flush()
    except IntegrityError as exc:
        if _is_primary_unique_violation(exc):
            raise CampaignServiceError(
                "Flight already has an active primary Form",
                status_code=422,
            ) from exc
        raise
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )


async def detach_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    link_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
) -> Campaign:
    _, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    row = await db.execute(
        select(CampaignRunForm).where(
            CampaignRunForm.id == link_id,
            CampaignRunForm.campaign_run_id == flight.id,
            CampaignRunForm.tenant_id == tenant_id,
        )
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise CampaignServiceError("Form link not found", status_code=404)
    await db.delete(link)
    await db.flush()
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )


async def attach_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    intake_source_profile_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
    role: str = "primary",
) -> Campaign:
    campaign, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    role_n = _normalize_role(role)
    pid = str(intake_source_profile_id or "").strip()
    if not pid:
        raise CampaignServiceError("intake_source_profile_id is required", status_code=422)

    profile_row = await db.execute(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.id == pid,
            IntakeSourceProfile.tenant_id == tenant_id,
        )
    )
    profile = profile_row.scalar_one_or_none()
    if profile is None:
        raise CampaignServiceError("Intake Source not found", status_code=404)
    if not profile.is_active:
        raise CampaignServiceError("Intake Source is inactive", status_code=422)
    if str(profile.own_company_id) != str(campaign.own_company_id):
        raise CampaignServiceError(
            "Intake Source belongs to another company",
            status_code=404,
        )

    existing = await db.execute(
        select(CampaignRunIntakeSource.id).where(
            CampaignRunIntakeSource.campaign_run_id == flight.id,
            CampaignRunIntakeSource.intake_source_profile_id == pid,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise CampaignServiceError(
            "Intake Source already linked to this Flight",
            status_code=422,
        )

    if role_n == "primary":
        await _assert_no_active_primary_intake_source(db, campaign_run_id=flight.id)

    flight.intake_source_links.append(
        CampaignRunIntakeSource(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_run_id=flight.id,
            intake_source_profile_id=pid,
            role=role_n,
            is_active=True,
        )
    )
    try:
        await db.flush()
    except IntegrityError as exc:
        if _is_primary_unique_violation(exc):
            raise CampaignServiceError(
                "Flight already has an active primary Intake Source",
                status_code=422,
            ) from exc
        raise
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )


async def update_intake_source_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    link_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
    is_active: bool | None = None,
    role: str | None = None,
) -> Campaign:
    _, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    row = await db.execute(
        select(CampaignRunIntakeSource).where(
            CampaignRunIntakeSource.id == link_id,
            CampaignRunIntakeSource.campaign_run_id == flight.id,
            CampaignRunIntakeSource.tenant_id == tenant_id,
        )
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise CampaignServiceError("Intake Source link not found", status_code=404)

    next_role = _normalize_role(role) if role is not None else link.role
    next_active = link.is_active if is_active is None else bool(is_active)

    becoming_active_primary = next_role == "primary" and next_active
    was_active_primary = link.role == "primary" and link.is_active
    if becoming_active_primary and not was_active_primary:
        await _assert_no_active_primary_intake_source(db, campaign_run_id=flight.id)

    link.role = next_role
    link.is_active = next_active
    try:
        await db.flush()
    except IntegrityError as exc:
        if _is_primary_unique_violation(exc):
            raise CampaignServiceError(
                "Flight already has an active primary Intake Source",
                status_code=422,
            ) from exc
        raise
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )


async def detach_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    link_id: str,
    own_company_id: str | None = None,
    flight_id: str | None = None,
) -> Campaign:
    _, flight = await _resolve_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
        flight_id=flight_id,
    )
    row = await db.execute(
        select(CampaignRunIntakeSource).where(
            CampaignRunIntakeSource.id == link_id,
            CampaignRunIntakeSource.campaign_run_id == flight.id,
            CampaignRunIntakeSource.tenant_id == tenant_id,
        )
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise CampaignServiceError("Intake Source link not found", status_code=404)
    await db.delete(link)
    await db.flush()
    return await _reload_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )
