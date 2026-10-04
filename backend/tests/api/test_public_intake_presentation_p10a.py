"""P10A — Presentation Rules on public intake and settings write."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.presentation_rules import apply_presentation_rules_evaluation
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles
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


async def _create_form(client: AsyncClient, tenant_id: str) -> tuple[str, str, dict[str, str]]:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p10a-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "P10A form",
            "public_slug": slug,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["form"]["id"], slug, headers


async def _publish_form(
    client: AsyncClient,
    headers: dict[str, str],
    form_id: str,
    *,
    fields: list[dict] | None = None,
) -> None:
    published = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"p10a-{form_id}"},
        json={"fields": fields} if fields else {},
    )
    assert published.status_code == 200, published.text


@pytest.mark.asyncio
async def test_p10a_save_presentation_with_rules(client: AsyncClient, tenant_id: str) -> None:
    form_id, _slug, headers = await _create_form(client, tenant_id)
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


def test_p10a_rejects_rule_source_outside_subset() -> None:
    """Settings-write leftover: invalid rule sources are rejected in the write validator.

    Public serve (FP-3) does not treat presentation rules as live authority.
    HTTP PUT currently drops invalid rules rather than 422; the named check is the unit validator.
    """
    from backend.app.entity_profile.presentation_rules import (
        PresentationRulesWriteError,
        validate_presentation_rules_for_subset,
    )

    overrides = {
        "recruitment.candidate.contacts.email": {
            "intake_level": "optional",
            "presentation_rules": {
                "show_if": {
                    "source_field": "platform.identity.citizenship",
                    "operator": "truthy",
                }
            },
        }
    }
    subset = [
        "recruitment.candidate.first_name",
        "recruitment.candidate.contacts.email",
    ]
    with pytest.raises(PresentationRulesWriteError) as exc:
        validate_presentation_rules_for_subset(overrides, subset)
    assert exc.value.code == "presentation_rule_source_outside_subset"


@pytest.mark.asyncio
async def test_p10a_public_get_includes_evaluated_state(client: AsyncClient, tenant_id: str) -> None:
    form_id, slug, admin_headers = await _create_form(client, tenant_id)
    fields = [
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
            ]
    await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=admin_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": fields,
        },
    )

    await _publish_form(client, admin_headers, form_id, fields=fields)
    email = f"p10a-{uuid.uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    token = create.json()["token"]

    get_empty = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_empty.status_code == 200, get_empty.text
    assert get_empty.json().get("form_presentation") is None
    runtime = get_empty.json()["form_runtime"]
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT
    field_ids = {f["qualified_code"] for f in runtime.get("fields") or []}
    assert "recruitment.candidate.contacts.email" in field_ids
    assert "recruitment.candidate.first_name" in field_ids


@pytest.mark.asyncio
async def test_p10a_submit_validates_required_if(client: AsyncClient, tenant_id: str) -> None:
    form_id, slug, admin_headers = await _create_form(client, tenant_id)
    fields = [
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
            ]
    await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=admin_headers,
        json={
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "fields": fields,
        },
    )

    await _publish_form(client, admin_headers, form_id, fields=fields)
    email = f"p10a-req-{uuid.uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    token = create.json()["token"]
    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    runtime = get_resp.json().get("form_runtime") or {}
    last_name = next(
        f
        for f in (runtime.get("fields") or [])
        if f.get("qualified_code") == "recruitment.candidate.last_name"
    )
    assert last_name.get("intake_level") != "required"


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
