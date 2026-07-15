"""P8 — Intake Source CRUD + Presentation Write API."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE, TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.entity_profile.presentation_runtime import FORM_PRESENTATION_RUNTIME_V1
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.candidate import Candidate
from backend.app.models.entity_profile import EpIntakePresentation
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.api.test_intake_forms_settings import _admin_headers


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_lead_source_limit",
        _noop,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.count_tenant_lead_sources",
        _zero,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


def _headers(tenant_id: str) -> dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


async def _seed_entity_profiles(tenant_id: str) -> None:
    async with async_session_maker() as session:
        from backend.tests.api.test_public_intake import _ensure_recruitment_funnels

        await _ensure_recruitment_funnels(session, tenant_id)
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await session.commit()


@pytest.mark.asyncio
async def test_p8_list_entity_profiles(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.get("/api/v1/settings/intake-forms/entity-profiles", headers=headers)
    assert resp.status_code == 200, resp.text
    codes = {row["code"] for row in resp.json()}
    assert DRIVER_CE_PROFILE_CODE in codes


@pytest.mark.asyncio
async def test_p8_create_form_with_presentation(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p8-form-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "P8 Test Form",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "label_override": "Imię",
                    "intake_level": "required",
                    "sort_order": 10,
                },
                {
                    "qualified_code": "recruitment.candidate.last_name",
                    "label_override": "Nazwisko",
                    "intake_level": "required",
                    "sort_order": 20,
                },
                {
                    "qualified_code": "recruitment.candidate.contacts.phone",
                    "label_override": "Telefon",
                    "intake_level": "required",
                    "sort_order": 30,
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["form"]["public_slug"] == slug
    assert body["intake_source_profile"] is not None
    assert body["intake_source_profile"]["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert body["presentation"]["contract_version"] == FORM_PRESENTATION_RUNTIME_V1
    labels = {f["qualified_code"]: f["label"] for f in body["presentation"]["fields"]}
    assert labels["recruitment.candidate.first_name"] == "Imię"

    form_id = body["form"]["id"]
    get_resp = await client.get(f"/api/v1/public/intake", headers=_headers(tenant_id))
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": f"{slug}@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    assert create.json().get("lead_id")
    assert not create.json().get("candidate_id")

    token = create.json()["token"]
    apply = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert apply.status_code == 200, apply.text
    fp = apply.json().get("form_presentation")
    assert fp is not None
    assert fp["contract_version"] == FORM_PRESENTATION_RUNTIME_V1
    assert len(fp.get("fields") or []) == 3

    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form is not None
        pres_code = f"{DRIVER_CE_PROFILE_CODE}.form.{slug}"
        pres = await session.scalar(
            select(EpIntakePresentation).where(
                EpIntakePresentation.tenant_id == tenant_id,
                EpIntakePresentation.presentation_code == pres_code,
            )
        )
        assert pres is not None


@pytest.mark.asyncio
async def test_p8_rejects_field_outside_entity_profile(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p8-bad-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "Bad fields",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.not_a_real_field",
                    "intake_level": "required",
                }
            ],
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "presentation_field_not_in_profile"


@pytest.mark.asyncio
async def test_p8_put_presentation_updates_runtime(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p8-put-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "PUT presentation test",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "label_override": "Initial",
                    "intake_level": "required",
                    "sort_order": 10,
                },
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]

    resp = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "label_override": "First",
                    "intake_level": "required",
                    "sort_order": 10,
                },
                {
                    "qualified_code": "recruitment.candidate.contacts.email",
                    "label_override": "Email",
                    "intake_level": "optional",
                    "sort_order": 20,
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    fields = resp.json()["presentation"]["fields"]
    assert len(fields) == 2
    assert fields[0]["label"] == "First"

    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": f"p8-put-{uuid.uuid4().hex[:6]}@example.com"}, "lead_form_slug": slug},
    )
    token = create.json()["token"]
    apply = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert apply.status_code == 200, apply.text
    fp = apply.json().get("form_presentation")
    assert fp is not None
    labels = {f["qualified_code"]: f["label"] for f in fp["fields"]}
    assert labels.get("recruitment.candidate.first_name") == "First"


@pytest.mark.asyncio
async def test_p8_smoke_test_lead_draft_not_candidate(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p8-smoke-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "Smoke P8",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]
    smoke = await client.post(f"/api/v1/settings/intake-forms/{form_id}/smoke-test", headers=headers)
    assert smoke.status_code == 200, smoke.text
    assert smoke.json().get("lead_id")
    assert not smoke.json().get("candidate_id")

    async with async_session_maker() as session:
        lead = await session.get(Lead, smoke.json()["lead_id"])
        assert lead is not None
        count = await session.scalar(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.email == smoke.json()["contacts"]["email"],
                Candidate.deleted_at.is_(None),
            )
        )
        assert count is None


@pytest.mark.asyncio
async def test_p8_sales_profile_form_uses_sales_inquiry_routing(
    client: AsyncClient,
    tenant_id: str,
) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p8-b2b-{uuid.uuid4().hex[:8]}"
    preset_resp = await client.get(
        f"/api/v1/settings/intake-forms/entity-profiles/{TARGETED_ADVERTISING_PROFILE_CODE}/presentation-preset",
        headers=headers,
    )
    assert preset_resp.status_code == 200, preset_resp.text
    fields = preset_resp.json()["fields"][:5]

    resp = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "B2B Sales Form",
            "public_slug": slug,
            "entity_profile_code": TARGETED_ADVERTISING_PROFILE_CODE,
            "fields": fields,
        },
    )
    assert resp.status_code == 200, resp.text
    intake = resp.json()["intake_source_profile"]
    assert intake is not None
    assert intake["route_intent"] == "sales_inquiry"
    assert intake["entity_profile_code"] == TARGETED_ADVERTISING_PROFILE_CODE
    assert resp.json()["submit_destination"]["route_intent"] == "sales_inquiry"
