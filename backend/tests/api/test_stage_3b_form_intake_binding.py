"""ADR-024 Stage 3B — Form + Intake Source bindings on CampaignRun."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.db.session import async_session_maker
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
    CampaignTarget,
)
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.own_company import OwnCompany
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


async def _seed_own_company(tenant_id: str, *, name: str = "Other OC") -> str:
    oc_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(OwnCompany(id=oc_id, tenant_id=tenant_id, name=name, is_archived=False))
        await session.commit()
    return oc_id


async def _seed_form(
    *,
    tenant_id: str,
    title: str = "Drivers CE form",
    is_active: bool = True,
    lifecycle_status: str = "active",
    public_slug: str | None = None,
) -> str:
    form_id = str(uuid4())
    slug = public_slug or f"form-{form_id[:8]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title=title,
                public_slug=slug,
                is_active=is_active,
                lifecycle_status=lifecycle_status,
                purpose="inquiry",
            )
        )
        await session.commit()
    return form_id


async def _seed_intake_source(
    *,
    tenant_id: str,
    own_company_id: str,
    provider: str = "public_intake",
    code: str | None = None,
    name: str = "Website intake",
    is_active: bool = True,
    with_binding: bool = False,
    external_key: str | None = None,
) -> str:
    profile_id = str(uuid4())
    code_n = code or f"src-{profile_id[:8]}"
    key = external_key or f"form_id:{profile_id[:12]}"
    async with async_session_maker() as session:
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=code_n,
                name=name,
                provider=provider,
                channel="organic",
                own_company_id=own_company_id,
                route_intent="candidate_application",
                is_active=is_active,
            )
        )
        await session.flush()
        if with_binding:
            session.add(
                IntakeSourceBinding(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    intake_source_profile_id=profile_id,
                    provider=provider,
                    external_key=key,
                    external_key_secondary=f"page_id:{profile_id[:8]}",
                    label="Meta form",
                    is_active=True,
                    priority=10,
                )
            )
        await session.commit()
    return profile_id


async def _create_campaign(client: AsyncClient, headers: dict, **extra) -> dict:
    own_company_id = extra.get("own_company_id")
    payload = {
        "name": extra.pop("name", "Stage 3B campaign"),
        "goal_type": extra.pop("goal_type", "hiring"),
        "primary_kpi": extra.pop("primary_kpi", "applications"),
        **extra,
    }
    hdrs = dict(headers)
    if own_company_id:
        hdrs["X-Own-Company-Id"] = own_company_id
    resp = await client.post("/api/v1/platform/campaigns", headers=hdrs, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _company_headers(auth_headers: dict, own_company_id: str) -> dict:
    return {**auth_headers, "X-Own-Company-Id": own_company_id}

def test_binding_models_do_not_own_operations_domain():
    forbidden_tables = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
    }
    for model in (Campaign, CampaignRun, CampaignTarget, CampaignRunForm, CampaignRunIntakeSource):
        mapper = inspect(model)
        fk_tables = {
            fk.column.table.name for col in mapper.columns for fk in col.foreign_keys
        }
        assert not (fk_tables & forbidden_tables), f"{model.__name__}: {fk_tables & forbidden_tables}"

    form_fks = {
        fk.column.table.name
        for col in inspect(CampaignRunForm).columns
        for fk in col.foreign_keys
    }
    assert "acq_campaign_runs" in form_fks
    assert "tenant_lead_forms" in form_fks

    src_fks = {
        fk.column.table.name
        for col in inspect(CampaignRunIntakeSource).columns
        for fk in col.foreign_keys
    }
    assert "acq_campaign_runs" in src_fks
    assert "intake_source_profiles" in src_fks


@pytest.mark.asyncio
async def test_attach_form_and_intake_source_to_current_flight(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        provider="public_intake",
    )

    campaign = await _create_campaign(
        client, auth_headers, own_company_id=own_company_id, name="Bind both"
    )
    cid = campaign["id"]
    hdrs = _company_headers(auth_headers, own_company_id)
    assert len(campaign["flights"]) == 1
    assert campaign["flights"][0]["forms"] == []
    assert campaign["flights"][0]["intake_sources"] == []

    form_resp = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_id, "role": "primary"},
    )
    assert form_resp.status_code == 201, form_resp.text
    body = form_resp.json()
    assert len(body["flights"][0]["forms"]) == 1
    assert body["flights"][0]["forms"][0]["form_id"] == form_id
    assert body["flights"][0]["forms"][0]["title"] == "Drivers CE form"

    src_resp = await client.post(
        f"/api/v1/platform/campaigns/{cid}/intake-sources",
        headers=hdrs,
        json={"intake_source_profile_id": profile_id},
    )
    assert src_resp.status_code == 201, src_resp.text
    body = src_resp.json()
    assert len(body["flights"][0]["intake_sources"]) == 1
    assert body["flights"][0]["intake_sources"][0]["intake_source_profile_id"] == profile_id
    assert body["flights"][0]["intake_sources"][0]["provider"] == "public_intake"

    got = await client.get(f"/api/v1/platform/campaigns/{cid}", headers=hdrs)
    assert got.status_code == 200
    assert len(got.json()["flights"][0]["forms"]) == 1
    assert len(got.json()["flights"][0]["intake_sources"]) == 1

@pytest.mark.asyncio
async def test_same_form_reusable_across_two_campaigns(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id, title="Shared form")

    c1 = await _create_campaign(client, auth_headers, own_company_id=own_company_id, name="C1")
    c2 = await _create_campaign(client, auth_headers, own_company_id=own_company_id, name="C2")
    hdrs = _company_headers(auth_headers, own_company_id)

    r1 = await client.post(
        f"/api/v1/platform/campaigns/{c1['id']}/forms",
        headers=hdrs,
        json={"form_id": form_id},
    )
    r2 = await client.post(
        f"/api/v1/platform/campaigns/{c2['id']}/forms",
        headers=hdrs,
        json={"form_id": form_id},
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text

    async with async_session_maker() as session:
        forms = await session.execute(select(TenantLeadForm).where(TenantLeadForm.id == form_id))
        assert forms.scalar_one_or_none() is not None
        links = await session.execute(
            select(CampaignRunForm).where(CampaignRunForm.form_id == form_id)
        )
        assert len(list(links.scalars().all())) == 2


@pytest.mark.asyncio
async def test_rejects_inactive_form(client: AsyncClient, auth_headers: dict):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id, is_active=False)
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign['id']}/forms",
        headers=_company_headers(auth_headers, own_company_id),
        json={"form_id": form_id},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rejects_intake_source_other_company(client: AsyncClient, auth_headers: dict):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_a = await _default_own_company_id(tenant_id)
    own_b = await _seed_own_company(tenant_id, name="Foreign OC 3B")
    foreign_profile = await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=own_b,
        provider="website",
    )
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_a)
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign['id']}/intake-sources",
        headers=_company_headers(auth_headers, own_a),
        json={"intake_source_profile_id": foreign_profile},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detach_removes_association_not_sot(client: AsyncClient, auth_headers: dict):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_intake_source(
        tenant_id=tenant_id, own_company_id=own_company_id
    )
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    cid = campaign["id"]
    hdrs = _company_headers(auth_headers, own_company_id)

    attached = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_id},
    )
    assert attached.status_code == 201, attached.text
    link_id = attached.json()["flights"][0]["forms"][0]["id"]

    src = await client.post(
        f"/api/v1/platform/campaigns/{cid}/intake-sources",
        headers=hdrs,
        json={"intake_source_profile_id": profile_id},
    )
    assert src.status_code == 201, src.text
    src_link_id = src.json()["flights"][0]["intake_sources"][0]["id"]

    d1 = await client.delete(
        f"/api/v1/platform/campaigns/{cid}/forms/{link_id}",
        headers=hdrs,
    )
    assert d1.status_code == 200, d1.text
    assert d1.json()["flights"][0]["forms"] == []

    d2 = await client.delete(
        f"/api/v1/platform/campaigns/{cid}/intake-sources/{src_link_id}",
        headers=hdrs,
    )
    assert d2.status_code == 200, d2.text
    assert d2.json()["flights"][0]["intake_sources"] == []

    async with async_session_maker() as session:
        assert (
            await session.execute(select(TenantLeadForm).where(TenantLeadForm.id == form_id))
        ).scalar_one_or_none() is not None
        assert (
            await session.execute(
                select(IntakeSourceProfile).where(IntakeSourceProfile.id == profile_id)
            )
        ).scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_meta_intake_source_bind_does_not_create_application(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    profile_id = await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        provider="meta",
        name="Meta CE leads",
        with_binding=True,
    )
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    async with async_session_maker() as session:
        before_apps = len(
            list(
                (
                    await session.execute(
                        select(RecruitmentApplication).where(
                            RecruitmentApplication.tenant_id == tenant_id
                        )
                    )
                ).scalars().all()
            )
        )

    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign['id']}/intake-sources",
        headers=_company_headers(auth_headers, own_company_id),
        json={"intake_source_profile_id": profile_id},
    )
    assert resp.status_code == 201, resp.text
    link = resp.json()["flights"][0]["intake_sources"][0]
    assert link["provider"] == "meta"
    assert link["bindings"]
    assert link["bindings"][0]["external_key"].startswith("form_id:")
    assert link["bindings"][0]["id"]

    async with async_session_maker() as session:
        after_apps = list(
            (
                await session.execute(
                    select(RecruitmentApplication).where(
                        RecruitmentApplication.tenant_id == tenant_id
                    )
                )
            ).scalars().all()
        )
        assert len(after_apps) == before_apps
        # Form SoT count unchanged by Meta bind (no Form invented for Meta).
        form_links = list(
            (
                await session.execute(
                    select(CampaignRunForm).where(
                        CampaignRunForm.campaign_run_id == campaign["flights"][0]["id"]
                    )
                )
            ).scalars().all()
        )
        assert form_links == []


@pytest.mark.asyncio
async def test_cookie_and_bearer_form_bind_parity(client: AsyncClient, auth_headers: dict):
    from backend.app.auth.session_cookies import CSRF_HEADER, session_cookie_names

    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_a = await _seed_form(tenant_id=tenant_id, title="Bearer form")
    form_b = await _seed_form(tenant_id=tenant_id, title="Cookie form")
    hdrs = _company_headers(auth_headers, own_company_id)

    c_bearer = await _create_campaign(
        client, auth_headers, own_company_id=own_company_id, name="Bearer bind"
    )
    c_cookie = await _create_campaign(
        client, auth_headers, own_company_id=own_company_id, name="Cookie bind"
    )
    bearer = await client.post(
        f"/api/v1/platform/campaigns/{c_bearer['id']}/forms",
        headers=hdrs,
        json={"form_id": form_a},
    )
    assert bearer.status_code == 201, bearer.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    names = session_cookie_names()
    csrf = login.cookies.get(names["csrf"])
    assert csrf

    cookie = await client.post(
        f"/api/v1/platform/campaigns/{c_cookie['id']}/forms",
        headers={
            "X-Tenant-Id": auth_headers["X-Tenant-Id"],
            "X-Own-Company-Id": own_company_id,
            CSRF_HEADER: csrf,
        },
        cookies={
            names["access"]: login.cookies.get(names["access"]),
            names["csrf"]: csrf,
        },
        json={"form_id": form_b},
    )
    assert cookie.status_code == 201, cookie.text
    assert cookie.json()["flights"][0]["forms"][0]["form_id"] == form_b


@pytest.mark.asyncio
async def test_explicit_flight_path_attach_form(client: AsyncClient, auth_headers: dict):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    flight_id = campaign["flights"][0]["id"]
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign['id']}/flights/{flight_id}/forms",
        headers=_company_headers(auth_headers, own_company_id),
        json={"form_id": form_id},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["flights"][0]["forms"][0]["form_id"] == form_id


@pytest.mark.asyncio
async def test_same_entity_cannot_bind_twice_to_one_flight(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    hdrs = _company_headers(auth_headers, own_company_id)
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    cid = campaign["id"]

    ok = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_id},
    )
    assert ok.status_code == 201, ok.text
    dup = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_id, "role": "secondary"},
    )
    assert dup.status_code == 422


@pytest.mark.asyncio
async def test_second_active_primary_form_rejected_then_reassign_after_inactive(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    form_a = await _seed_form(tenant_id=tenant_id, title="Primary A")
    form_b = await _seed_form(tenant_id=tenant_id, title="Primary B")
    hdrs = _company_headers(auth_headers, own_company_id)
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    cid = campaign["id"]

    first = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_a, "role": "primary"},
    )
    assert first.status_code == 201, first.text
    link_a = first.json()["flights"][0]["forms"][0]["id"]

    second = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_b, "role": "primary"},
    )
    assert second.status_code == 422

    secondary = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_b, "role": "secondary"},
    )
    assert secondary.status_code == 201, secondary.text

    deactivated = await client.patch(
        f"/api/v1/platform/campaigns/{cid}/forms/{link_a}",
        headers=hdrs,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200, deactivated.text
    assert any(
        f["id"] == link_a and f["is_active"] is False
        for f in deactivated.json()["flights"][0]["forms"]
    )

    form_c = await _seed_form(tenant_id=tenant_id, title="Primary C")
    reassigned = await client.post(
        f"/api/v1/platform/campaigns/{cid}/forms",
        headers=hdrs,
        json={"form_id": form_c, "role": "primary"},
    )
    assert reassigned.status_code == 201, reassigned.text
    actives = [
        f
        for f in reassigned.json()["flights"][0]["forms"]
        if f["role"] == "primary" and f["is_active"]
    ]
    assert len(actives) == 1
    assert actives[0]["form_id"] == form_c


@pytest.mark.asyncio
async def test_second_active_primary_intake_source_rejected(
    client: AsyncClient,
    auth_headers: dict,
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    src_a = await _seed_intake_source(
        tenant_id=tenant_id, own_company_id=own_company_id, name="Src A"
    )
    src_b = await _seed_intake_source(
        tenant_id=tenant_id, own_company_id=own_company_id, name="Src B"
    )
    hdrs = _company_headers(auth_headers, own_company_id)
    campaign = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    cid = campaign["id"]

    ok = await client.post(
        f"/api/v1/platform/campaigns/{cid}/intake-sources",
        headers=hdrs,
        json={"intake_source_profile_id": src_a, "role": "primary"},
    )
    assert ok.status_code == 201, ok.text
    bad = await client.post(
        f"/api/v1/platform/campaigns/{cid}/intake-sources",
        headers=hdrs,
        json={"intake_source_profile_id": src_b, "role": "primary"},
    )
    assert bad.status_code == 422


def test_association_models_have_no_provider_or_external_ref_columns():
    form_cols = {c.key for c in inspect(CampaignRunForm).columns}
    src_cols = {c.key for c in inspect(CampaignRunIntakeSource).columns}
    assert "provider" not in src_cols
    assert "external_ref" not in src_cols
    assert {"campaign_run_id", "form_id", "role", "is_active"} <= form_cols
    assert {"campaign_run_id", "intake_source_profile_id", "role", "is_active"} <= src_cols


@pytest.mark.asyncio
async def test_intake_source_options_for_marketing_picker(
    client: AsyncClient,
    auth_headers: dict,
):
    """Marketing setup needs named Meta sources — no raw profile JSON for operators."""
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    meta_id = await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        provider="meta",
        name="Meta leads PL",
    )
    await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        provider="public_intake",
        name="Website",
    )
    other_oc = await _seed_own_company(tenant_id, name="Other marketing OC")
    await _seed_intake_source(
        tenant_id=tenant_id,
        own_company_id=other_oc,
        provider="meta",
        name="Other company Meta",
    )

    hdrs = _company_headers(auth_headers, own_company_id)
    all_resp = await client.get("/api/v1/platform/campaigns/intake-source-options", headers=hdrs)
    assert all_resp.status_code == 200, all_resp.text
    all_rows = all_resp.json()
    assert any(row["id"] == meta_id and row["name"] == "Meta leads PL" for row in all_rows)
    assert all(row["id"] != "" for row in all_rows)
    assert not any(row["name"] == "Other company Meta" for row in all_rows)

    meta_resp = await client.get(
        "/api/v1/platform/campaigns/intake-source-options",
        headers=hdrs,
        params={"provider": "meta"},
    )
    assert meta_resp.status_code == 200
    meta_rows = meta_resp.json()
    assert meta_rows
    assert all(row["provider"] == "meta" for row in meta_rows)
    assert any(row["id"] == meta_id for row in meta_rows)
