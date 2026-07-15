"""Provision targeted-advertising questionnaire capability for services tenants."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import (
    TARGETED_ADVERTISING_PRESENTATION_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.entity_profile.manifests.service_sales import service_sales_targeted_advertising_profile
from backend.app.entity_profile.registry import EntityProfileRegistry, UnknownCanonicalFieldError
from backend.app.entity_profile.seed import ensure_tenant_field_registry_defaults
from backend.app.models.entity_profile import EpEntityProfile, EpIntakePresentation
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeChannel, IntakeProvider, RouteIntent
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.models.tenant_lead_form import TenantLeadForm

logger = logging.getLogger(__name__)

TARGETED_ADVERTISING_FORM_SLUG = "targeted-advertising"
TARGETED_ADVERTISING_FORM_TITLE = "Ankieta — reklama targetowana"
INTAKE_PROFILE_CODE = f"public-form-{TARGETED_ADVERTISING_FORM_SLUG}"

CAPABILITY_PENDING = "pending"
CAPABILITY_READY = "ready"
CAPABILITY_FAILED = "failed"
CAPABILITY_NEEDS_REPAIR = "needs_repair"


@dataclass(frozen=True)
class TargetedAdvertisingProvisionResult:
    status: str
    tenant_id: str
    lead_form_id: str | None = None
    error: str | None = None
    created: dict[str, bool] = field(default_factory=dict)
    repaired: dict[str, bool] = field(default_factory=dict)
    skipped: bool = False


def tenant_business_type(tenant: Tenant) -> str:
    settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    return str(settings.get("business_type") or "").strip().lower()


def is_services_tenant(tenant: Tenant) -> bool:
    return tenant_business_type(tenant) == "services"


async def _global_lead_form_public_slug_taken(db: AsyncSession, slug: str, *, tenant_id: str) -> bool:
    row = await db.scalar(
        select(TenantLeadForm.tenant_id)
        .where(
            func.lower(func.trim(TenantLeadForm.public_slug)) == slug.strip().lower(),
            TenantLeadForm.tenant_id != str(tenant_id),
        )
        .limit(1)
    )
    return row is not None


async def _global_intake_public_slug_taken(db: AsyncSession, slug: str, *, tenant_id: str) -> bool:
    row = await db.scalar(
        select(IntakeSourceProfile.tenant_id)
        .where(
            IntakeSourceProfile.public_slug == slug,
            IntakeSourceProfile.tenant_id != str(tenant_id),
        )
        .limit(1)
    )
    return row is not None


async def find_tenant_targeted_advertising_lead_form(
    db: AsyncSession,
    tenant_id: str,
) -> TenantLeadForm | None:
    """Resolve tenant-owned targeted-advertising form (public slug or internal-only instance)."""
    tid = str(tenant_id)
    by_slug = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == tid,
            TenantLeadForm.public_slug == TARGETED_ADVERTISING_FORM_SLUG,
            TenantLeadForm.is_active.is_(True),
        ).limit(1)
    )
    if by_slug is not None:
        return by_slug

    inactive_by_slug = await db.scalar(
        select(TenantLeadForm).where(
            TenantLeadForm.tenant_id == tid,
            TenantLeadForm.public_slug == TARGETED_ADVERTISING_FORM_SLUG,
            TenantLeadForm.is_active.is_(False),
        ).limit(1)
    )
    if inactive_by_slug is not None:
        return inactive_by_slug

    intake_profile = await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == tid,
            IntakeSourceProfile.code == INTAKE_PROFILE_CODE,
            IntakeSourceProfile.is_active.is_(True),
        ).limit(1)
    )
    if intake_profile is None:
        return None

    binding = await db.scalar(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == tid,
            IntakeSourceBinding.intake_source_profile_id == str(intake_profile.id),
            IntakeSourceBinding.provider == IntakeProvider.public_intake.value,
            IntakeSourceBinding.external_key.like("lead_form_id:%"),
        ).limit(1)
    )
    if binding is None:
        return None
    form_id = str(binding.external_key or "").split(":", 1)[-1].strip()
    if not form_id:
        return None
    return await db.get(TenantLeadForm, form_id)


async def _default_own_company_id(db: AsyncSession, tenant_id: str) -> str | None:
    row = await db.scalar(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    return str(row) if row else None


async def _ensure_default_own_company_id(db: AsyncSession, tenant_id: str) -> str:
    existing = await _default_own_company_id(db, str(tenant_id))
    if existing:
        return existing
    row = OwnCompany(
        id=str(uuid4()),
        tenant_id=str(tenant_id),
        name="HostFlow",
        is_archived=False,
    )
    db.add(row)
    await db.flush()
    return str(row.id)


def _tenant_scoped_public_slug(tenant_id: str) -> str:
    suffix = str(tenant_id).replace("-", "")[:10]
    return f"{TARGETED_ADVERTISING_FORM_SLUG}-{suffix}"


async def _ensure_entity_profile_template(db: AsyncSession, tenant_id: str) -> tuple[bool, bool]:
    """Ensure canonical entity profile + presentation exist without overwriting tenant instances."""
    existing_profile = await EntityProfileRegistry.get_entity_profile(
        db,
        tenant_id=str(tenant_id),
        profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
    )
    if existing_profile is None:
        await ensure_tenant_field_registry_defaults(db, tenant_id)
    manifest = service_sales_targeted_advertising_profile()
    profile_result = await EntityProfileRegistry.register_profile_if_absent(
        db,
        manifest,
        tenant_id=str(tenant_id),
    )
    profile_created = bool(profile_result.get("created"))

    entity = await EntityProfileRegistry.get_entity_profile(
        db,
        tenant_id=str(tenant_id),
        profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
    )
    if entity is None:
        raise RuntimeError("targeted_advertising entity profile missing after registration")

    presentation_created = False
    for presentation in manifest.get("intake_presentations") or []:
        if await EntityProfileRegistry.ensure_intake_presentation_if_absent(
            db,
            entity,
            presentation,
            tenant_scope=str(tenant_id),
        ):
            presentation_created = True

    return profile_created, presentation_created


def _repair_intake_profile_system_links(profile: IntakeSourceProfile) -> bool:
    """Fill missing system links only; never replace tenant-customized values."""
    repaired = False
    if not str(profile.entity_profile_code or "").strip():
        profile.entity_profile_code = TARGETED_ADVERTISING_PROFILE_CODE
        repaired = True
    if not str(profile.presentation_code or "").strip():
        profile.presentation_code = TARGETED_ADVERTISING_PRESENTATION_CODE
        repaired = True
    if not str(profile.route_intent or "").strip():
        profile.route_intent = RouteIntent.sales_inquiry.value
        repaired = True
    if not str(profile.lead_type or "").strip():
        profile.lead_type = "client"
        repaired = True
    if not str(profile.lead_target_type or "").strip():
        profile.lead_target_type = "client_lead"
        repaired = True
    if profile.is_active is False and str(profile.public_slug or "") == TARGETED_ADVERTISING_FORM_SLUG:
        profile.is_active = True
        repaired = True
    return repaired


async def _ensure_intake_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_profile_id: str,
    external_key: str,
    priority: int,
) -> bool:
    binding = await db.scalar(
        select(IntakeSourceBinding).where(
            IntakeSourceBinding.tenant_id == str(tenant_id),
            IntakeSourceBinding.provider == IntakeProvider.public_intake.value,
            IntakeSourceBinding.external_key == external_key,
        )
    )
    if binding is not None:
        return False
    db.add(
        IntakeSourceBinding(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            intake_source_profile_id=str(intake_profile_id),
            provider=IntakeProvider.public_intake.value,
            external_key=external_key,
            external_key_secondary=None,
            priority=priority,
            is_active=True,
        )
    )
    await db.flush()
    return True


async def _ensure_intake_form_stack(
    db: AsyncSession,
    tenant_id: str,
    *,
    own_company_id: str,
) -> tuple[TenantLeadForm, dict[str, bool], dict[str, bool]]:
    created: dict[str, bool] = {}
    repaired: dict[str, bool] = {}

    lead_form = await find_tenant_targeted_advertising_lead_form(db, tenant_id)
    if lead_form is None:
        public_slug: str | None = TARGETED_ADVERTISING_FORM_SLUG
        if await _global_lead_form_public_slug_taken(db, TARGETED_ADVERTISING_FORM_SLUG, tenant_id=tenant_id):
            public_slug = _tenant_scoped_public_slug(tenant_id)
            created["public_slug_tenant_scoped"] = True
        lead_form = TenantLeadForm(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            title=TARGETED_ADVERTISING_FORM_TITLE,
            public_slug=public_slug,
            is_active=True,
        )
        db.add(lead_form)
        await db.flush()
        created["lead_form"] = True
    else:
        created["lead_form"] = False
        if not lead_form.is_active:
            lead_form.is_active = True
            repaired["lead_form"] = True
            await db.flush()

    intake_profile = await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == str(tenant_id),
            IntakeSourceProfile.code == INTAKE_PROFILE_CODE,
        )
    )
    if intake_profile is None:
        profile_public_slug: str | None = TARGETED_ADVERTISING_FORM_SLUG
        if await _global_intake_public_slug_taken(db, TARGETED_ADVERTISING_FORM_SLUG, tenant_id=tenant_id):
            profile_public_slug = None
            created["intake_public_slug_internal_only"] = True
        intake_profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            code=INTAKE_PROFILE_CODE,
            name=TARGETED_ADVERTISING_FORM_TITLE,
            provider=IntakeProvider.public_intake.value,
            channel=IntakeChannel.direct.value,
            own_company_id=own_company_id,
            route_intent=RouteIntent.sales_inquiry.value,
            public_slug=profile_public_slug,
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
        created["intake_profile"] = True
    else:
        created["intake_profile"] = False
        if _repair_intake_profile_system_links(intake_profile):
            repaired["intake_profile"] = True
            await db.flush()

    binding_slug = await _ensure_intake_binding(
        db,
        tenant_id=tenant_id,
        intake_profile_id=str(intake_profile.id),
        external_key=f"public_slug:{TARGETED_ADVERTISING_FORM_SLUG}",
        priority=10,
    )
    binding_form = await _ensure_intake_binding(
        db,
        tenant_id=tenant_id,
        intake_profile_id=str(intake_profile.id),
        external_key=f"lead_form_id:{lead_form.id}",
        priority=20,
    )
    created["binding_slug"] = binding_slug
    created["binding_form"] = binding_form

    return lead_form, created, repaired


async def provision_targeted_advertising_capability(
    db: AsyncSession,
    tenant_id: str,
    *,
    tenant: Tenant | None = None,
) -> TargetedAdvertisingProvisionResult:
    """Transactional auto-seed for services tenants; create-only for tenant-owned rows."""
    tid = str(tenant_id)
    tenant_row = tenant
    if tenant_row is None:
        tenant_row = await db.get(Tenant, tid)
    if tenant_row is None:
        return TargetedAdvertisingProvisionResult(
            status=CAPABILITY_FAILED,
            tenant_id=tid,
            error="tenant_not_found",
        )

    if not is_services_tenant(tenant_row):
        return TargetedAdvertisingProvisionResult(
            status=CAPABILITY_READY,
            tenant_id=tid,
            skipped=True,
        )

    own_company_id = await _ensure_default_own_company_id(db, tid)

    created: dict[str, bool] = {}
    repaired: dict[str, bool] = {}
    try:
        profile_created, presentation_created = await _ensure_entity_profile_template(db, tid)
        created["entity_profile"] = profile_created
        created["presentation"] = presentation_created

        lead_form, form_created, form_repaired = await _ensure_intake_form_stack(
            db,
            tid,
            own_company_id=own_company_id,
        )
        created.update(form_created)
        repaired.update(form_repaired)

        form_count = await db.scalar(
            select(func.count())
            .select_from(TenantLeadForm)
            .where(
                TenantLeadForm.tenant_id == tid,
                TenantLeadForm.public_slug == TARGETED_ADVERTISING_FORM_SLUG,
            )
        )
        if form_count and int(form_count) > 1:
            raise RuntimeError("duplicate_targeted_advertising_form_slug")

        status = CAPABILITY_READY
        if repaired and not any(created.values()):
            status = CAPABILITY_NEEDS_REPAIR

        return TargetedAdvertisingProvisionResult(
            status=status,
            tenant_id=tid,
            lead_form_id=str(lead_form.id),
            created=created,
            repaired=repaired,
        )
    except (UnknownCanonicalFieldError, RuntimeError, ValueError) as exc:
        logger.exception(
            "targeted_advertising capability provisioning failed for tenant %s",
            tid,
        )
        return TargetedAdvertisingProvisionResult(
            status=CAPABILITY_FAILED,
            tenant_id=tid,
            error=str(exc),
        )


async def recover_targeted_advertising_capability(
    db: AsyncSession,
    tenant_id: str,
) -> TargetedAdvertisingProvisionResult:
    """Lazy ensure / repair path for legacy services tenants."""
    return await provision_targeted_advertising_capability(db, tenant_id)


async def provision_targeted_advertising_on_tenant_create(
    db: AsyncSession,
    tenant: Tenant,
) -> TargetedAdvertisingProvisionResult:
    """Hook for tenant provisioning; failures should roll back the outer transaction."""
    result = await provision_targeted_advertising_capability(db, str(tenant.id), tenant=tenant)
    if result.status == CAPABILITY_FAILED:
        raise RuntimeError(result.error or "targeted_advertising_provision_failed")
    return result
