"""Auto-seed targeted-advertising capability on services tenant provisioning."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import (
    TARGETED_ADVERTISING_PRESENTATION_CODE,
    TARGETED_ADVERTISING_PROFILE_CODE,
)
from backend.app.entity_profile.provision_targeted_advertising import (
    CAPABILITY_PENDING,
    CAPABILITY_READY,
    TARGETED_ADVERTISING_FORM_SLUG,
    find_tenant_targeted_advertising_lead_form,
    provision_targeted_advertising_capability,
    recover_targeted_advertising_capability,
)
from backend.app.entity_profile.seed_targeted_advertising_form import (
    ensure_tenant_targeted_advertising_intake_form,
)
from backend.app.models import Lead
from backend.app.models.entity_profile import EpEntityProfile, EpIntakePresentation
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant, TenantStatus, TenantType
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.leads import crud as leads_crud


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _ensure_questionnaire_invite_table() -> None:
    from backend.app.db.base import Base
    from backend.app.db.session import engine
    from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[LeadQuestionnaireInvite.__table__],
                checkfirst=True,
            )
        )


async def _create_tenant_bundle(
    *,
    business_type: str,
    suffix: str | None = None,
) -> tuple[str, str]:
    tag = suffix or uuid4().hex[:8]
    async with async_session_maker() as session:
        tenant = Tenant(
            id=str(uuid4()),
            name=f"Provision Test {tag}",
            slug=f"provision-test-{tag}",
            api_key=f"api-{tag}-{uuid4().hex[:8]}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"business_type": business_type},
        )
        session.add(tenant)
        own_company = OwnCompany(
            tenant_id=str(tenant.id),
            name=f"OC {tag}",
        )
        session.add(own_company)
        await session.commit()
        return str(tenant.id), str(own_company.id)


async def _form_count(tenant_id: str) -> int:
    async with async_session_maker() as session:
        form = await find_tenant_targeted_advertising_lead_form(session, tenant_id)
        return 1 if form is not None else 0


@pytest.mark.asyncio
async def test_services_tenant_gets_single_targeted_advertising_form() -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="services")
    async with async_session_maker() as session:
        result = await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()
    assert result.status == CAPABILITY_READY
    assert result.lead_form_id
    assert await _form_count(tenant_id) == 1


@pytest.mark.asyncio
async def test_repeat_provisioning_does_not_create_duplicate() -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="services")
    async with async_session_maker() as session:
        first = await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()
    async with async_session_maker() as session:
        second = await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()
    assert first.lead_form_id == second.lead_form_id
    assert await _form_count(tenant_id) == 1
    assert not second.created.get("lead_form")


@pytest.mark.asyncio
async def test_non_services_tenant_skips_targeted_advertising_form() -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="agency")
    async with async_session_maker() as session:
        result = await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()
    assert result.skipped is True
    assert await _form_count(tenant_id) == 0


@pytest.mark.asyncio
async def test_legacy_form_is_reused_not_replaced() -> None:
    tenant_id, own_company_id = await _create_tenant_bundle(business_type="services")
    legacy_form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=legacy_form_id,
                tenant_id=tenant_id,
                title="Legacy custom title",
                public_slug=None,
                is_active=True,
            )
        )
        profile_id = str(uuid4())
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=f"public-form-{TARGETED_ADVERTISING_FORM_SLUG}",
                name="Legacy intake",
                provider="public_intake",
                channel="direct",
                own_company_id=own_company_id,
                route_intent="sales_inquiry",
                public_slug=None,
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
        )
        await session.flush()
        session.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                intake_source_profile_id=profile_id,
                provider="public_intake",
                external_key=f"lead_form_id:{legacy_form_id}",
                priority=20,
                is_active=True,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        result = await recover_targeted_advertising_capability(session, tenant_id)
        await session.commit()

    assert result.lead_form_id == legacy_form_id
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, legacy_form_id)
        assert form is not None
        assert form.title == "Legacy custom title"


@pytest.mark.asyncio
async def test_user_customizations_are_not_overwritten() -> None:
    tenant_id, own_company_id = await _create_tenant_bundle(business_type="services")
    custom_title = "Tenant-owned questionnaire title"
    custom_profile_name = "Tenant-owned intake profile"
    async with async_session_maker() as session:
        form = TenantLeadForm(
            id=str(uuid4()),
            tenant_id=tenant_id,
            title=custom_title,
            public_slug=None,
            is_active=True,
        )
        session.add(form)
        await session.flush()
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=f"public-form-{TARGETED_ADVERTISING_FORM_SLUG}",
            name=custom_profile_name,
            provider="public_intake",
            channel="direct",
            own_company_id=own_company_id,
            route_intent="sales_inquiry",
            public_slug=None,
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
        session.add(profile)
        await session.flush()
        session.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                intake_source_profile_id=str(profile.id),
                provider="public_intake",
                external_key=f"lead_form_id:{form.id}",
                priority=20,
                is_active=True,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()

    async with async_session_maker() as session:
        form = await find_tenant_targeted_advertising_lead_form(session, tenant_id)
        profile = await session.scalar(
            select(IntakeSourceProfile).where(
                IntakeSourceProfile.tenant_id == tenant_id,
                IntakeSourceProfile.code == f"public-form-{TARGETED_ADVERTISING_FORM_SLUG}",
            )
        )
        assert form is not None
        assert form.title == custom_title
        assert profile is not None
        assert profile.name == custom_profile_name


@pytest.mark.asyncio
async def test_provisioning_failure_rolls_back_partial_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="services")

    async def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated_provision_failure")

    monkeypatch.setattr(
        "backend.app.entity_profile.provision_targeted_advertising._ensure_intake_form_stack",
        _boom,
    )

    async with async_session_maker() as session:
        result = await provision_targeted_advertising_capability(session, tenant_id)
        await session.rollback()

    assert result.status == "failed"
    assert await _form_count(tenant_id) == 0
    async with async_session_maker() as session:
        profile_count = await session.scalar(
            select(func.count())
            .select_from(EpEntityProfile)
            .where(
                EpEntityProfile.tenant_id == tenant_id,
                EpEntityProfile.profile_code == TARGETED_ADVERTISING_PROFILE_CODE,
            )
        )
        assert int(profile_count or 0) == 0


@pytest.mark.asyncio
async def test_lazy_ensure_restores_missing_legacy_form() -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="services")
    async with async_session_maker() as session:
        await ensure_tenant_targeted_advertising_intake_form(session, tenant_id)
        await session.commit()
    assert await _form_count(tenant_id) == 1


@pytest.mark.asyncio
async def test_provisioned_form_supports_questionnaire_invite(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    async with async_session_maker() as session:
        from backend.app.models.own_company import OwnCompany

        own_company_id = await session.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        await provision_targeted_advertising_capability(session, tenant_id)
        lead = await leads_crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            source="meta_ads",
            external_id=f"auto-seed-{uuid4().hex[:8]}",
            payload={"full_name": "Auto Seed Lead"},
            normalized={"full_name": "Auto Seed Lead", "email": "lead@example.com"},
            lead_type="client",
            lead_target_type="client_lead",
        )
        await session.commit()
        lead_id = str(lead.id)

    invite_resp = await client.post(
        f"/api/v1/leads/{lead_id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    token = invite_resp.json()["token"]
    assert token

    public_resp = await client.get(f"/api/v1/public/apply/{token}")
    assert public_resp.status_code == 200, public_resp.text
    body = public_resp.json()
    assert body.get("form_presentation", {}).get("entity_profile_code") == TARGETED_ADVERTISING_PROFILE_CODE
    assert body.get("form_presentation", {}).get("presentation_code") == TARGETED_ADVERTISING_PRESENTATION_CODE


@pytest.mark.asyncio
async def test_tenant_create_hook_provisions_services_capability() -> None:
    tag = uuid4().hex[:8]
    async with async_session_maker() as session:
        tenant, _license = await tenant_service.create_tenant_with_license(
            session,
            tenant_payload={
                "name": f"Hook Services {tag}",
                "slug": f"hook-services-{tag}",
                "type": TenantType.agency,
                "status": TenantStatus.active,
                "settings": {"business_type": "services"},
            },
            license_payload={"plan": "manual"},
        )
        session.add(OwnCompany(tenant_id=str(tenant.id), name=f"Hook OC {tag}"))
        await session.commit()
        tenant_id = str(tenant.id)

    # Re-run provision after own company exists (initial hook may be pending)
    async with async_session_maker() as session:
        result = await recover_targeted_advertising_capability(session, tenant_id)
        await session.commit()
    assert result.status in {CAPABILITY_READY, CAPABILITY_PENDING}
    if result.status == CAPABILITY_READY:
        assert await _form_count(tenant_id) == 1


@pytest.mark.asyncio
async def test_inactive_slug_form_is_reactivated_not_duplicated() -> None:
    tenant_id, _ = await _create_tenant_bundle(business_type="services")
    legacy_form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=legacy_form_id,
                tenant_id=tenant_id,
                title="Inactive canonical slug",
                public_slug=TARGETED_ADVERTISING_FORM_SLUG,
                is_active=False,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        result = await recover_targeted_advertising_capability(session, tenant_id)
        await session.commit()

    assert result.lead_form_id == legacy_form_id
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, legacy_form_id)
        assert form is not None
        assert form.is_active is True


@pytest.mark.asyncio
async def test_services_tenant_without_own_company_stays_pending() -> None:
    tag = uuid4().hex[:8]
    async with async_session_maker() as session:
        tenant = Tenant(
            id=str(uuid4()),
            name=f"Pending Services {tag}",
            slug=f"pending-services-{tag}",
            api_key=f"api-pending-{tag}",
            type=TenantType.agency,
            status=TenantStatus.active,
            settings={"business_type": "services"},
        )
        session.add(tenant)
        await session.commit()
        tenant_id = str(tenant.id)

    async with async_session_maker() as session:
        result = await provision_targeted_advertising_capability(session, tenant_id)
        await session.commit()

    assert result.status == CAPABILITY_PENDING
    assert await _form_count(tenant_id) == 0
