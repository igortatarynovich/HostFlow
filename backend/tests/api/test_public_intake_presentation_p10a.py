"""P10A — Presentation Rules on public intake and settings write."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.presentation_rules import apply_presentation_rules_evaluation
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_intake_demo_form import (
    DRIVER_CE_FORM_SLUG,
    ensure_tenant_default_driver_ce_intake_form,
)
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_public_intake import _headers


pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr("backend.app.services.intake_form_write_service.ensure_lead_source_limit", _noop)
    monkeypatch.setattr("backend.app.services.intake_form_write_service.count_tenant_lead_sources", _zero)
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


async def _seed_driver_ce_form_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_default_driver_ce_intake_form(session, tenant_id)
        await session.commit()
        from sqlalchemy import select
        from backend.app.models.tenant_lead_form import TenantLeadForm

        form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug == DRIVER_CE_FORM_SLUG,
            )
        )
        assert form is not None
        return str(form.id)


@pytest.mark.asyncio
async def test_p10a_save_presentation_with_rules(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form_id(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "intake_level": "required",
                    "sort_order": 10,
                },
                {
                    "qualified_code": "recruitment.candidate.contacts.phone",
                    "intake_level": "required",
                    "sort_order": 20,
                },
                {
                    "qualified_code": "recruitment.candidate.contacts.email",
                    "intake_level": "optional",
                    "sort_order": 30,
                    "presentation_rules": {
                        "show_if": {
                            "source_field": "recruitment.candidate.first_name",
                            "operator": "truthy",
                        },
                        "required_if": {
                            "source_field": "recruitment.candidate.first_name",
                            "operator": "truthy",
                        },
                    },
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    fields = resp.json()["presentation"]["fields"]
    email_field = next(f for f in fields if f["qualified_code"] == "recruitment.candidate.contacts.email")
    assert email_field.get("presentation_rules", {}).get("show_if")


@pytest.mark.asyncio
async def test_p10a_rejects_rule_source_outside_subset(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form_id(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "intake_level": "required",
                },
                {
                    "qualified_code": "recruitment.candidate.contacts.email",
                    "intake_level": "optional",
                    "presentation_rules": {
                        "show_if": {
                            "source_field": "platform.identity.citizenship",
                            "operator": "truthy",
                        }
                    },
                },
            ],
        },
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "presentation_rule_source_outside_subset"


@pytest.mark.asyncio
async def test_p10a_public_get_includes_evaluated_state(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form_id(tenant_id)
    admin_headers = await _admin_headers(tenant_id)
    await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=admin_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required", "sort_order": 10},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required", "sort_order": 20},
                {
                    "qualified_code": "recruitment.candidate.contacts.email",
                    "intake_level": "optional",
                    "sort_order": 30,
                    "presentation_rules": {
                        "show_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
                    },
                },
            ],
        },
    )

    email = f"p10a-{uuid.uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": DRIVER_CE_FORM_SLUG},
    )
    token = create.json()["token"]

    get_empty = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    fp = get_empty.json()["form_presentation"]
    email_field = next(f for f in fp["fields"] if f["qualified_code"] == "recruitment.candidate.contacts.email")
    assert email_field["evaluated"]["visible"] is False

    put = await client.put(
        f"/api/v1/public/apply/{token}",
        headers=_headers(tenant_id),
        json={
            "data": {
                "presentation_values": {
                    "recruitment.candidate.first_name": "Anna",
                    "recruitment.candidate.contacts.phone": "+48111222333",
                }
            }
        },
    )
    assert put.status_code == 200, put.text

    get_filled = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    fp2 = get_filled.json()["form_presentation"]
    email_field2 = next(f for f in fp2["fields"] if f["qualified_code"] == "recruitment.candidate.contacts.email")
    assert email_field2["evaluated"]["visible"] is True


@pytest.mark.asyncio
async def test_p10a_submit_validates_required_if(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form_id(tenant_id)
    admin_headers = await _admin_headers(tenant_id)
    await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=admin_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required", "sort_order": 10},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required", "sort_order": 20},
                {
                    "qualified_code": "recruitment.candidate.last_name",
                    "intake_level": "optional",
                    "sort_order": 30,
                    "presentation_rules": {
                        "show_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
                        "required_if": {"source_field": "recruitment.candidate.first_name", "operator": "truthy"},
                    },
                },
            ],
        },
    )

    email = f"p10a-req-{uuid.uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": DRIVER_CE_FORM_SLUG},
    )
    token = create.json()["token"]
    await client.put(
        f"/api/v1/public/apply/{token}",
        headers=_headers(tenant_id),
        json={
            "data": {
                "presentation_values": {
                    "recruitment.candidate.first_name": "Anna",
                    "recruitment.candidate.contacts.phone": "+48111222333",
                }
            }
        },
    )

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 422, submit.text
    detail = submit.json()["detail"]
    assert detail["code"] == "presentation_required_fields"
    assert "recruitment.candidate.last_name" in detail["missing"]


def test_p10a_runtime_evaluator_unit_smoke() -> None:
    presentation = {
        "fields": [
            {
                "qualified_code": "recruitment.candidate.contacts.email",
                "intake_level": "optional",
                "presentation_rules": {
                    "show_if": {"source_field": "recruitment.candidate.first_name", "operator": "eq", "value": "Anna"}
                },
            }
        ]
    }
    out = apply_presentation_rules_evaluation(
        presentation,
        {"recruitment.candidate.first_name": "Anna"},
    )
    assert out["fields"][0]["evaluated"]["visible"] is True
