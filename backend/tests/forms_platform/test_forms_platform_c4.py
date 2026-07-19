"""C4 — ADR-007 Forms platform publication bridge."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE
from backend.app.forms_platform.constants import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DISPATCHER_SALES_INQUIRY,
    FORMS_PLATFORM_CONTRACT_VERSION,
    STORAGE_BACKEND_TENANT_LEAD_FORM,
)
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.forms_platform.handlers import list_registered_handlers, resolve_submission_handler
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles


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


def test_c4_handler_registry_lists_recruitment_lead_draft() -> None:
    handlers = list_registered_handlers()
    ids = {row["handler_id"] for row in handlers}
    assert DISPATCHER_CANDIDATE_APPLICATION in ids
    assert DISPATCHER_SALES_INQUIRY in ids
    lead = resolve_submission_handler(route_intent="candidate_application")
    assert lead["creates_on_create"]["application"] is True
    assert lead["creates_on_create"]["lead_draft"] is False
    assert lead["creates_on_create"]["candidate"] is False
    assert lead["destination"] == "recruitment"

    with pytest.raises(FormsRoutingUnresolvedError):
        resolve_submission_handler(route_intent=None)


@pytest.mark.asyncio
async def test_c4_handlers_api(client: AsyncClient, tenant_id: str) -> None:
    headers = await _admin_headers(tenant_id)
    resp = await client.get("/api/v1/platform/forms/handlers", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["handler_id"] for row in resp.json()["handlers"]}
    assert DISPATCHER_CANDIDATE_APPLICATION in ids


@pytest.mark.asyncio
async def test_c4_publication_resolve_api(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"c4-form-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "C4 Forms Platform",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]

    by_id = await client.get(
        "/api/v1/platform/forms/publications/resolve",
        headers=headers,
        params={"form_id": form_id},
    )
    assert by_id.status_code == 200, by_id.text
    body = by_id.json()
    assert body["contract_version"] == FORMS_PLATFORM_CONTRACT_VERSION
    assert body["storage_backend"] == STORAGE_BACKEND_TENANT_LEAD_FORM
    assert body["public_slug"] == slug
    assert body["entity_profile_code"] == WAREHOUSE_WORKER_PROFILE_CODE
    assert body["submission_handler"]["handler_id"] == DISPATCHER_CANDIDATE_APPLICATION

    by_slug = await client.get(
        "/api/v1/platform/forms/publications/resolve",
        headers=headers,
        params={"public_slug": slug},
    )
    assert by_slug.status_code == 200
    assert by_slug.json()["publication_id"] == form_id


@pytest.mark.asyncio
async def test_c4_intake_form_detail_includes_forms_platform(client: AsyncClient, tenant_id: str) -> None:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"c4-detail-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "C4 Detail",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]
    detail = await client.get(f"/api/v1/settings/intake-forms/{form_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    fp = detail.json().get("forms_platform") or {}
    assert fp.get("contract_version") == FORMS_PLATFORM_CONTRACT_VERSION
    assert fp.get("submission_handler", {}).get("handler_id") == DISPATCHER_CANDIDATE_APPLICATION
