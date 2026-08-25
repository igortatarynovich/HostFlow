"""Questionnaire SSOT repair slice tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import TARGETED_ADVERTISING_PROFILE_CODE
from backend.app.entity_profile.presentation_write import build_tenant_form_presentation_code
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_targeted_advertising_form import ensure_tenant_targeted_advertising_intake_form
from backend.app.intake_platform.constants import FormLifecycleStatus
from backend.app.models.entity_profile import EpIntakePresentation
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.services.questionnaire_sales_resolver import resolve_sales_questionnaire_context
from backend.app.services.questionnaire_ssot_repair import (
    repair_targeted_advertising_form,
    repair_targeted_advertising_questionnaires,
)
from backend.tests.api.test_sales_targeted_advertising_intake import _create_meta_client_lead, _seed_sales_profile


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


@pytest.mark.asyncio
async def test_repair_sets_profile_code_and_tenant_presentation(tenant_id: str) -> None:
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_targeted_advertising_intake_form(session, tenant_id)
        lead_form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug.is_not(None),
            )
        )
        assert lead_form is not None
        lead_form.target_entity_profile_code = None
        await session.commit()

    async with async_session_maker() as session:
        lead_form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug.is_not(None),
            )
        )
        assert lead_form is not None
        first = await repair_targeted_advertising_form(session, tenant_id=tenant_id, lead_form=lead_form)
        await session.commit()
        assert first["repaired"].get("target_entity_profile_code") is True
        presentation_code = first["presentation_code"]
        assert presentation_code.endswith(f".form.{lead_form.public_slug}")

        row = await session.scalar(
            select(EpIntakePresentation).where(
                EpIntakePresentation.tenant_id == tenant_id,
                EpIntakePresentation.presentation_code == presentation_code,
            )
        )
        assert row is not None
        assert row.field_subset

        second = await repair_targeted_advertising_form(session, tenant_id=tenant_id, lead_form=lead_form)
        assert not second.get("repaired")


@pytest.mark.asyncio
async def test_repair_idempotent_for_whole_tenant(tenant_id: str) -> None:
    await _seed_sales_profile(tenant_id)
    async with async_session_maker() as session:
        first = await repair_targeted_advertising_questionnaires(session, tenant_id=tenant_id)
        await session.commit()
        count_after_first = await session.scalar(
            select(func.count())
            .select_from(TenantLeadForm)
            .where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.target_entity_profile_code == TARGETED_ADVERTISING_PROFILE_CODE,
            )
        )
        second = await repair_targeted_advertising_questionnaires(session, tenant_id=tenant_id)
        await session.commit()
        count_after_second = await session.scalar(
            select(func.count())
            .select_from(TenantLeadForm)
            .where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.target_entity_profile_code == TARGETED_ADVERTISING_PROFILE_CODE,
            )
        )
    assert count_after_first == count_after_second
    assert first.status in {"ready", "needs_repair"}


@pytest.mark.asyncio
async def test_sales_questionnaire_context_returns_primary_form(tenant_id: str) -> None:
    await _seed_sales_profile(tenant_id)
    async with async_session_maker() as session:
        context = await resolve_sales_questionnaire_context(session, tenant_id=tenant_id, auto_repair=True)
        await session.commit()
    assert context["readiness"] == "ready"
    assert context["primary_form"] is not None
    assert context["primary_form"]["target_entity_profile_code"] == TARGETED_ADVERTISING_PROFILE_CODE
    assert context["supported_languages"] == ["pl", "en", "ru"]


@pytest.mark.asyncio
async def test_archived_form_hidden_from_sales_list(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    from backend.tests.api.test_intake_forms_settings import _admin_headers

    await _seed_sales_profile(tenant_id)
    admin_headers = await _admin_headers(tenant_id)
    list_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert list_resp.status_code == 200
    form_id = list_resp.json()[0]["id"]

    archive_resp = await client.patch(
        f"/api/v1/settings/intake-forms/{form_id}",
        headers=admin_headers,
        json={"lifecycle_status": "archived"},
    )
    assert archive_resp.status_code == 200, archive_resp.text

    after_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    assert after_resp.status_code == 200
    assert all(row["id"] != form_id for row in after_resp.json())


@pytest.mark.asyncio
async def test_questionnaire_invite_with_locale(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)
    lead = await _create_meta_client_lead(tenant_id)
    forms_resp = await client.get("/api/v1/leads/questionnaire-forms", headers=manager_headers)
    form_id = forms_resp.json()[0]["id"]

    invite_resp = await client.post(
        f"/api/v1/leads/{lead.id}/questionnaire-invite",
        headers=manager_headers,
        json={"mark_sent": True, "lead_form_id": form_id, "form_locale": "en"},
    )
    assert invite_resp.status_code == 200, invite_resp.text
    body = invite_resp.json()
    assert body["form_locale"] == "en"
    assert "lang=en" in body["apply_url"]

    get_resp = await client.get(f"/api/v1/public/apply/{body['token']}")
    assert get_resp.status_code == 200, get_resp.text
    presentation = get_resp.json().get("form_presentation") or {}
    assert presentation.get("contract_version") == "form_presentation_runtime_v1"
    slug = forms_resp.json()[0]["public_slug"]
    expected = build_tenant_form_presentation_code(
        entity_profile_code=TARGETED_ADVERTISING_PROFILE_CODE,
        public_slug=slug,
    )
    assert presentation.get("presentation_code") == expected


@pytest.mark.asyncio
async def test_questionnaire_context_endpoint(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: dict,
) -> None:
    await _seed_sales_profile(tenant_id)
    resp = await client.get("/api/v1/leads/questionnaire-context", headers=manager_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["readiness"] == "ready"
    assert body["primary_form"] is not None
    assert body["config_error"] is None
