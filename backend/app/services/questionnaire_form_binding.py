"""Shared helpers for B2B questionnaire form ↔ intake source binding."""

from __future__ import annotations

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.tenant_lead_form import TenantLeadForm


def is_repaired_b2b_questionnaire_form(lead_form: TenantLeadForm) -> bool:
    profile_code = str(getattr(lead_form, "target_entity_profile_code", None) or "").strip()
    slug = str(getattr(lead_form, "public_slug", None) or "").strip()
    return profile_code == TARGETED_ADVERTISING_PROFILE_CODE and bool(slug)


async def intake_profile_for_lead_form(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_form: TenantLeadForm,
) -> IntakeSourceProfile | None:
    # lead_form may be expired after a concurrent IntegrityError rollback / flush.
    state = sa_inspect(lead_form)
    if state.expired or not state.identity:
        await db.refresh(lead_form)
        state = sa_inspect(lead_form)
    form_id = str(state.identity[0]) if state.identity else str(lead_form.id)
    public_slug = str(lead_form.public_slug or "").strip()

    bindings = (
        await db.execute(
            select(IntakeSourceBinding).where(
                IntakeSourceBinding.tenant_id == str(tenant_id),
                IntakeSourceBinding.external_key == f"lead_form_id:{form_id}",
                IntakeSourceBinding.is_active.is_(True),
            )
        )
    ).scalars().all()
    for binding in bindings:
        profile = await db.get(IntakeSourceProfile, str(binding.intake_source_profile_id))
        if (
            profile is not None
            and profile.is_active
            and str(profile.route_intent or "") == RouteIntent.sales_inquiry.value
        ):
            return profile

    if not public_slug:
        return None
    return await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.public_slug == public_slug,
            IntakeSourceProfile.route_intent == RouteIntent.sales_inquiry.value,
            IntakeSourceProfile.is_active.is_(True),
        )
    )
