"""Seed targeted advertising public intake form + intake source bindings (Stage Sales Intake 1)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    TARGETED_ADVERTISING_PRESENTATION_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeChannel, IntakeProvider, RouteIntent
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm


TARGETED_ADVERTISING_FORM_SLUG = "targeted-advertising"
TARGETED_ADVERTISING_FORM_TITLE = "Ankieta — reklama targetowana"


async def _default_own_company_id(db: AsyncSession, tenant_id: str) -> str | None:
    row = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    return str(row) if row else None


async def ensure_tenant_targeted_advertising_intake_form(db: AsyncSession, tenant_id: str) -> None:
    """Idempotent: TenantLeadForm + IntakeSourceProfile for service_sales.targeted_advertising."""
    own_company_id = await _default_own_company_id(db, str(tenant_id))
    if not own_company_id:
        return

    lead_form = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == str(tenant_id),
            TenantLeadForm.public_slug == TARGETED_ADVERTISING_FORM_SLUG,
        )
    )
    if lead_form is None:
        lead_form = TenantLeadForm(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            title=TARGETED_ADVERTISING_FORM_TITLE,
            public_slug=TARGETED_ADVERTISING_FORM_SLUG,
            is_active=True,
        )
        db.add(lead_form)
        await db.flush()

    profile_code = f"public-form-{TARGETED_ADVERTISING_FORM_SLUG}"
    intake_profile = await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.code == profile_code,
        )
    )
    if intake_profile is None:
        intake_profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            code=profile_code,
            name=TARGETED_ADVERTISING_FORM_TITLE,
            provider=IntakeProvider.public_intake.value,
            channel=IntakeChannel.direct.value,
            own_company_id=own_company_id,
            route_intent=RouteIntent.sales_inquiry.value,
            public_slug=TARGETED_ADVERTISING_FORM_SLUG,
            form_type="sales_questionnaire",
            lead_type="client",
            lead_target_type="client_lead",
            entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
            presentation_code=TARGETED_ADVERTISING_PRESENTATION_CODE,
            source="meta_ads",
            default_language="pl",
            supported_languages="pl,en",
            is_active=True,
        )
        db.add(intake_profile)
        await db.flush()
    else:
        intake_profile.entity_profile_code = TARGETED_ADVERTISING_PROFILE_CODE
        intake_profile.presentation_code = TARGETED_ADVERTISING_PRESENTATION_CODE
        intake_profile.lead_type = "client"
        intake_profile.lead_target_type = "client_lead"
        intake_profile.route_intent = RouteIntent.sales_inquiry.value
        intake_profile.is_active = True
        await db.flush()

    binding_key = f"public_slug:{TARGETED_ADVERTISING_FORM_SLUG}"
    binding = await db.scalar(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == str(tenant_id),
            IntakeSourceBinding.provider == IntakeProvider.public_intake.value,
            IntakeSourceBinding.external_key == binding_key,
        )
    )
    if binding is None:
        db.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                intake_source_profile_id=str(intake_profile.id),
                provider=IntakeProvider.public_intake.value,
                external_key=binding_key,
                external_key_secondary=None,
                priority=10,
                is_active=True,
            )
        )
        await db.flush()

    lead_form_id_key = f"lead_form_id:{lead_form.id}"
    binding_by_id = await db.scalar(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == str(tenant_id),
            IntakeSourceBinding.provider == IntakeProvider.public_intake.value,
            IntakeSourceBinding.external_key == lead_form_id_key,
        )
    )
    if binding_by_id is None:
        db.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                intake_source_profile_id=str(intake_profile.id),
                provider=IntakeProvider.public_intake.value,
                external_key=lead_form_id_key,
                external_key_secondary=None,
                priority=20,
                is_active=True,
            )
        )
