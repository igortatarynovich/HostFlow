"""ADR-024 Stage 3A — Campaign registry integrity + foundation API."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.validation import (
    CampaignValidationError,
    validate_goal_kpi_pair,
    validate_promotion_target,
)
from backend.app.constants.campaign_registries import (
    canonical_target_module,
    goal_kpi_pairs,
    goal_type_codes,
    load_campaign_registries,
    primary_kpi_codes,
    promotion_targets_by_type,
)
from backend.app.db.session import async_session_maker
from backend.app.models.additional_service import Service
from backend.app.models.campaign import Campaign, CampaignRun, CampaignTarget
from backend.app.models.client_account import ClientAccount
from backend.app.models.own_company import OwnCompany
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data


def test_campaign_registries_ssot_shape():
    reg = load_campaign_registries()
    assert reg["version"] == "campaign_registries_v1"
    assert "hiring" in goal_type_codes()
    assert "cost_per_hire" in primary_kpi_codes()
    assert ("hiring", "cost_per_hire") in goal_kpi_pairs()
    assert ("hiring", "revenue") not in goal_kpi_pairs()
    assert canonical_target_module("vacancy") == "recruitment"
    assert canonical_target_module("service") == "sales"
    assert "candidate_application" in promotion_targets_by_type()["vacancy"]["allowed_route_intents"]


def test_goal_kpi_pair_validation():
    assert validate_goal_kpi_pair("Hiring", "Cost_per_Hire") == ("hiring", "cost_per_hire")
    with pytest.raises(CampaignValidationError):
        validate_goal_kpi_pair("hiring", "revenue")
    with pytest.raises(CampaignValidationError):
        validate_goal_kpi_pair("unknown", "hires")


def test_promotion_target_module_is_canonical_not_client_trust():
    v = validate_promotion_target(
        target_type="vacancy",
        target_id="vac-1",
        route_intent="candidate_application",
        client_target_module="recruitment",
    )
    assert v.target_module == "recruitment"

    with pytest.raises(CampaignValidationError, match="canonical"):
        validate_promotion_target(
            target_type="vacancy",
            target_id="vac-1",
            route_intent="candidate_application",
            client_target_module="sales",
        )

    with pytest.raises(CampaignValidationError, match="route_intent"):
        validate_promotion_target(
            target_type="vacancy",
            target_id="vac-1",
            route_intent="sales_inquiry",
        )

    with pytest.raises(CampaignValidationError, match="Unknown"):
        validate_promotion_target(
            target_type="not_a_target",
            target_id="x",
            route_intent="candidate_application",
        )


def test_campaign_models_do_not_own_operations_domain():
    """Campaign must not FK/own Candidate, Application, Inquiry, or Client."""
    forbidden_tables = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
    }
    forbidden_cols = {"candidate_id", "application_id", "inquiry_id", "client_account_id"}
    for model in (Campaign, CampaignRun, CampaignTarget):
        mapper = inspect(model)
        cols = {c.key for c in mapper.columns}
        fk_tables = {
            fk.column.table.name
            for col in mapper.columns
            for fk in col.foreign_keys
        }
        assert not (fk_tables & forbidden_tables), f"{model.__name__} owns {fk_tables & forbidden_tables}"
        assert not (cols & forbidden_cols), f"{model.__name__} has {cols & forbidden_cols}"
        # Universal target reference only — no typed domain FK.
        if model is CampaignTarget:
            assert "target_id" in cols
            assert "target_type" in cols


async def _allow_gate(*args, **kwargs):  # noqa: ANN002, ANN003
    return None


async def _deny_gate(*args, **kwargs):  # noqa: ANN002, ANN003
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail="Module disabled for tenant")


async def _seed_own_company(tenant_id: str, *, name: str = "Other OC") -> str:
    oc_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            OwnCompany(
                id=oc_id,
                tenant_id=tenant_id,
                name=name,
                is_archived=False,
            )
        )
        await session.commit()
    return oc_id


async def _seed_vacancy(
    *,
    tenant_id: str,
    own_company_id: str | None,
    company_id: str,
    title: str = "CE Drivers",
) -> str:
    vac_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Vacancy(
                id=vac_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                company_id=company_id,
                title=title,
                status="open",
                is_active=True,
                is_archived=False,
            )
        )
        await session.commit()
    return vac_id


async def _seed_client_account(
    *,
    tenant_id: str,
    display_name: str = "Rock Cargo",
    own_company_id: str | None = None,
) -> str:
    account_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            ClientAccount(
                id=account_id,
                tenant_id=tenant_id,
                display_name=display_name,
                status="prospect",
                own_company_id=own_company_id,
            )
        )
        await session.commit()
    return account_id


async def _seed_service(*, tenant_id: str, code: str | None = None) -> str:
    svc_id = str(uuid4())
    code_n = code or f"svc-{svc_id[:8]}"
    async with async_session_maker() as session:
        session.add(
            Service(
                id=svc_id,
                tenant_id=tenant_id,
                code=code_n,
                name="Recruitment package",
                is_active=True,
            )
        )
        await session.commit()
    return svc_id


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id).where(
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
            ).limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc, "bootstrap must seed own_companies"
        return str(oc)


@pytest.mark.asyncio
async def test_create_campaign_auto_creates_one_flight(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _allow_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=data["company_id"],
    )

    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Recruit Drivers Germany",
            "goal_type": "hiring",
            "primary_kpi": "cost_per_hire",
            "own_company_id": own_company_id,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "target_module": "recruitment",
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Recruit Drivers Germany"
    assert body["goal_type"] == "hiring"
    assert body["primary_kpi"] == "cost_per_hire"
    assert body["goal"] == {"goal_type": "hiring", "primary_kpi": "cost_per_hire"}
    assert body["own_company_id"] == own_company_id
    assert len(body["flights"]) == 1
    assert body["flights"][0]["code"] == "flight_1"
    assert body["flights"][0]["is_current"] is True
    assert body["current_flight_id"] == body["flights"][0]["id"]
    assert len(body["targets"]) == 1
    assert body["targets"][0]["target_module"] == "recruitment"
    assert body["targets"][0]["route_intent"] == "candidate_application"

    listed = await client.get(
        "/api/v1/platform/campaigns",
        headers={**auth_headers, "X-Own-Company-Id": own_company_id},
    )
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


@pytest.mark.asyncio
async def test_create_campaign_rejects_invalid_goal_kpi_pair(
    client: AsyncClient,
    auth_headers: dict,
):
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Bad KPI",
            "goal_type": "hiring",
            "primary_kpi": "revenue",
        },
    )
    assert resp.status_code == 422
    assert "pair" in resp.json()["detail"].lower() or "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_campaign_rejects_client_module_spoof(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _allow_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=data["company_id"],
    )
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Spoof module",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "own_company_id": own_company_id,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "target_module": "sales",
                }
            ],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_target_rejects_disallowed_route_intent(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _allow_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    svc_id = await _seed_service(tenant_id=tenant_id)

    created = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "No bad routes",
            "goal_type": "sales",
            "primary_kpi": "revenue",
        },
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]
    assert len(created.json()["flights"]) == 1

    bad = await client.post(
        f"/api/v1/platform/campaigns/{cid}/targets",
        headers=auth_headers,
        json={
            "target_type": "service",
            "target_id": svc_id,
            "route_intent": "candidate_application",
        },
    )
    assert bad.status_code == 422

    ok = await client.post(
        f"/api/v1/platform/campaigns/{cid}/targets",
        headers=auth_headers,
        json={
            "target_type": "service",
            "target_id": svc_id,
            "route_intent": "sales_inquiry",
        },
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["targets"][0]["target_module"] == "sales"


@pytest.mark.asyncio
async def test_rejects_target_of_another_company(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _allow_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_a = await _default_own_company_id(tenant_id)
    own_b = await _seed_own_company(tenant_id, name="Foreign OC")
    foreign_vac = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=own_b,
        company_id=data["company_id"],
        title="Other company vacancy",
    )

    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Cross-company leak",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "own_company_id": own_a,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": foreign_vac,
                    "route_intent": "candidate_application",
                }
            ],
        },
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_accepts_unscoped_vacancy_and_client_account(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _allow_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=None,
        company_id=data["company_id"],
        title="Kierowca CE",
    )
    account_id = await _seed_client_account(tenant_id=tenant_id, own_company_id=None)

    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Rock Cargo drivers",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "own_company_id": own_company_id,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "role": "primary",
                },
                {
                    "target_type": "client_account",
                    "target_id": account_id,
                    "route_intent": "sales_inquiry",
                    "role": "context",
                    "sort_order": 1,
                },
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    types = {row["target_type"] for row in body["targets"]}
    assert types == {"vacancy", "client_account"}


async def _deny_sales_allow_rest(*args, **kwargs):  # noqa: ANN002, ANN003
    from fastapi import HTTPException

    if str(kwargs.get("module_key") or "").strip().lower() == "sales":
        raise HTTPException(status_code=403, detail="Sales module is disabled for this workspace")
    return None


@pytest.mark.asyncio
async def test_hiring_campaign_does_not_require_sales_for_client_context(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _deny_sales_allow_rest,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=data["company_id"],
    )
    account_id = await _seed_client_account(tenant_id=tenant_id)

    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Hiring without Sales module",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "own_company_id": own_company_id,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "role": "primary",
                },
                {
                    "target_type": "client_account",
                    "target_id": account_id,
                    "route_intent": "sales_inquiry",
                    "role": "context",
                    "sort_order": 1,
                },
            ],
        },
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_rejects_disabled_destination_module(
    client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        "backend.app.acquisition.campaign_service.enforce_module_gate",
        _deny_gate,
    )
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        company_id=data["company_id"],
    )
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Module off",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "own_company_id": own_company_id,
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                }
            ],
        },
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_campaign_always_has_exactly_one_flight(
    client: AsyncClient,
    auth_headers: dict,
):
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Flight invariant",
            "goal_type": "awareness",
            "primary_kpi": "reach",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["flights"]) == 1
    assert body["current_flight_id"] == body["flights"][0]["id"]

    async with async_session_maker() as session:
        rows = await session.execute(
            select(CampaignRun).where(CampaignRun.campaign_id == body["id"])
        )
        flights = list(rows.scalars().all())
    assert len(flights) == 1
    assert flights[0].code == "flight_1"


@pytest.mark.asyncio
async def test_cookie_and_bearer_create_campaign_parity(
    client: AsyncClient,
    auth_headers: dict,
):
    from backend.app.auth.session_cookies import CSRF_HEADER, session_cookie_names

    # Bearer path first — before login cookies land on the shared AsyncClient jar.
    bearer = await client.post(
        "/api/v1/platform/campaigns",
        headers=auth_headers,
        json={
            "name": "Bearer campaign",
            "goal_type": "sales",
            "primary_kpi": "cac",
        },
    )
    assert bearer.status_code == 201, bearer.text
    assert len(bearer.json()["flights"]) == 1

    data = await _init_data()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    names = session_cookie_names()
    csrf = login.cookies.get(names["csrf"])
    assert csrf

    cookie = await client.post(
        "/api/v1/platform/campaigns",
        headers={
            "X-Tenant-Id": auth_headers["X-Tenant-Id"],
            CSRF_HEADER: csrf,
        },
        cookies={
            names["access"]: login.cookies.get(names["access"]),
            names["csrf"]: csrf,
        },
        json={
            "name": "Cookie campaign",
            "goal_type": "sales",
            "primary_kpi": "roi",
        },
    )
    assert cookie.status_code == 201, cookie.text
    assert len(cookie.json()["flights"]) == 1
    assert cookie.json()["goal"]["primary_kpi"] == "roi"


@pytest.mark.asyncio
async def test_registries_endpoint(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/platform/campaigns/registries", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "goal_types" in body
    assert "goal_kpi_pairs" in body
    assert "promotion_targets" in body
