"""IntakeRouter.resolve() — routing decision only, no derivative entities (PR-3)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from backend.app.models import Candidate, Company, OwnCompany
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing import crud
from backend.app.services.intake_router import IntakeRouter

TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"


async def _ensure_own_company(
    db,
    *,
    tenant_id: str = TENANT_ID,
    business_type: str | None = None,
) -> str:
    extra: dict = {}
    if business_type:
        extra["business_type"] = business_type
    oc = OwnCompany(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name=f"Router OC {uuid.uuid4().hex[:6]}",
        extra=extra,
    )
    db.add(oc)
    await db.flush()
    return oc.id


async def _create_profile_with_binding(
    db,
    *,
    code: str,
    own_company_id: str,
    external_key: str,
    route_intent: str = "sales_inquiry",
    profile_active: bool = True,
    binding_active: bool = True,
    tenant_id: str = TENANT_ID,
    external_key_secondary: str = "",
) -> tuple[str, str]:
    profile = await crud.create_profile(
        db,
        tenant_id=tenant_id,
        code=code,
        name=f"Profile {code}",
        own_company_id=own_company_id,
        provider="meta",
        channel="paid",
        route_intent=route_intent,
        pipeline_preset="service_sales",
        is_active=profile_active,
    )
    binding = await crud.create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=profile.id,
        provider="meta",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
        is_active=binding_active,
    )
    return profile.id, binding.id


async def _set_tenant_default_profile(db, *, profile_id: str, tenant_id: str = TENANT_ID) -> None:
    await db.execute(
        text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'intake_routing_v1',
                    jsonb_build_object('default_profile_id', (:profile_id)::text)
                )
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "profile_id": profile_id},
    )
    await db.flush()


async def _set_tenant_business_type(db, *, business_type: str, tenant_id: str = TENANT_ID) -> None:
    await db.execute(
        text(
            """
            UPDATE tenants
            SET settings = COALESCE(settings::jsonb, '{}'::jsonb)
                || jsonb_build_object('business_type', (:business_type)::text)
            WHERE id = :tenant_id
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    result = await db.execute(
        text(
            """
            UPDATE companies
            SET extra = COALESCE(extra::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'company_role', 'operating',
                    'business_type', (:business_type)::text,
                    'company_type', (:business_type)::text
                )
            WHERE tenant_id = :tenant_id
              AND COALESCE(is_archived, false) = false
              AND LOWER(COALESCE(extra::jsonb->>'company_role', '')) = 'operating'
            """
        ),
        {"tenant_id": tenant_id, "business_type": business_type},
    )
    if result.rowcount == 0:
        company = Company(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=f"Router Operating Co {uuid.uuid4().hex[:6]}",
            extra={
                "company_role": "operating",
                "business_type": business_type,
                "company_type": business_type,
            },
        )
        db.add(company)
    await db.flush()


async def _count_candidates(db, *, tenant_id: str = TENANT_ID) -> int:
    return int(
        (
            await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == tenant_id)
            )
        ).scalar_one()
    )


async def _count_companies(db, *, tenant_id: str = TENANT_ID) -> int:
    return int(
        (
            await db.execute(
                select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id)
            )
        ).scalar_one()
    )


@pytest.mark.asyncio
async def test_exact_binding_matched(db) -> None:
    oc_id = await _ensure_own_company(db)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    profile_id, _ = await _create_profile_with_binding(
        db,
        code=f"matched-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_id,
        external_key=external_key,
        route_intent="sales_inquiry",
    )

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    assert result.matched is True
    assert result.fallback is False
    assert result.failed is False
    assert result.intake_source_profile_id == profile_id
    assert result.own_company_id == oc_id
    assert result.route_intent == RouteIntent.sales_inquiry.value
    assert result.pipeline_preset == "service_sales"


@pytest.mark.asyncio
async def test_inactive_binding_ignored(db) -> None:
    oc_id = await _ensure_own_company(db)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    profile_id, _ = await _create_profile_with_binding(
        db,
        code=f"inactive-bind-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_id,
        external_key=external_key,
        binding_active=False,
    )
    await _set_tenant_default_profile(db, profile_id=profile_id)

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    assert result.matched is True
    assert result.intake_source_profile_id == profile_id
    assert "tenant_default_profile" in result.warnings


@pytest.mark.asyncio
async def test_inactive_profile_ignored(db) -> None:
    oc_id = await _ensure_own_company(db)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    await _create_profile_with_binding(
        db,
        code=f"inactive-prof-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_id,
        external_key=external_key,
        profile_active=False,
    )
    default_profile = await crud.create_profile(
        db,
        tenant_id=TENANT_ID,
        code=f"active-default-{uuid.uuid4().hex[:8]}",
        name="Active default",
        own_company_id=oc_id,
        provider="meta",
        route_intent="sales_inquiry",
    )
    await _set_tenant_default_profile(db, profile_id=default_profile.id)

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    assert result.matched is True
    assert result.intake_source_profile_id == default_profile.id
    assert "tenant_default_profile" in result.warnings


@pytest.mark.asyncio
async def test_missing_binding_uses_tenant_default(db) -> None:
    oc_id = await _ensure_own_company(db)
    default_profile = await crud.create_profile(
        db,
        tenant_id=TENANT_ID,
        code=f"default-{uuid.uuid4().hex[:8]}",
        name="Tenant default",
        own_company_id=oc_id,
        provider="meta",
        route_intent="candidate_application",
    )
    await _set_tenant_default_profile(db, profile_id=default_profile.id)

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=f"form_id:{uuid.uuid4().hex[:12]}",
    )

    assert result.matched is True
    assert result.failed is False
    assert result.intake_source_profile_id == default_profile.id
    assert result.route_intent == RouteIntent.candidate_application.value
    assert "tenant_default_profile" in result.warnings


@pytest.mark.asyncio
async def test_no_default_meta_missing_form_id_failed(db) -> None:
    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key="",
    )

    assert result.matched is False
    assert result.fallback is False
    assert result.failed is True
    assert result.intake_source_profile_id is None
    assert result.route_intent == RouteIntent.unknown.value
    assert "meta_missing_form_id" in result.warnings


@pytest.mark.asyncio
async def test_no_binding_no_default_uses_legacy_fallback(db) -> None:
    await _set_tenant_business_type(db, business_type="services")
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    assert result.matched is False
    assert result.fallback is True
    assert result.failed is False
    assert result.intake_source_profile_id is None
    assert result.route_intent == RouteIntent.sales_inquiry.value
    assert "legacy_business_type_fallback" in result.warnings


@pytest.mark.asyncio
async def test_cross_tenant_binding_not_used(db) -> None:
    oc_other = await _ensure_own_company(db, tenant_id=OTHER_TENANT_ID)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    await _create_profile_with_binding(
        db,
        code=f"other-tenant-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_other,
        external_key=external_key,
        tenant_id=OTHER_TENANT_ID,
    )

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    assert result.intake_source_profile_id is None
    assert result.matched is False


@pytest.mark.asyncio
async def test_resolve_does_not_create_candidate_or_client(db) -> None:
    oc_id = await _ensure_own_company(db)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    candidates_before = await _count_candidates(db)
    companies_before = await _count_companies(db)

    await _create_profile_with_binding(
        db,
        code=f"no-sidefx-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_id,
        external_key=external_key,
        route_intent="candidate_application",
    )

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
    )

    await db.flush()
    candidates_after = await _count_candidates(db)
    companies_after = await _count_companies(db)

    assert result.matched is True
    assert result.route_intent == RouteIntent.candidate_application.value
    assert candidates_after == candidates_before
    assert companies_after == companies_before


@pytest.mark.asyncio
async def test_secondary_relaxed_binding_match(db) -> None:
    oc_id = await _ensure_own_company(db)
    external_key = f"form_id:{uuid.uuid4().hex[:12]}"
    profile_id, _ = await _create_profile_with_binding(
        db,
        code=f"pageless-{uuid.uuid4().hex[:8]}",
        own_company_id=oc_id,
        external_key=external_key,
        external_key_secondary="",
    )

    result = await IntakeRouter.resolve(
        db,
        tenant_id=TENANT_ID,
        provider="meta",
        external_key=external_key,
        external_key_secondary="page_id:999",
    )

    assert result.matched is True
    assert result.intake_source_profile_id == profile_id
    assert "secondary_relaxed_binding" in result.warnings
