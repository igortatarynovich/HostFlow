"""P7 — Public form runtime wiring after FP-3 (frozen publication → Form Runtime)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.public_intake_presentation_bridge import (
    apply_presentation_values_to_state,
    validate_presentation_required_fields,
)
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT
from backend.app.models.candidate import Candidate
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles
from backend.tests.api.test_public_intake import _headers, _seed_active_lead_form


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


async def _seed_published_form(client: AsyncClient, tenant_id: str) -> str:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"p7-{uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "P7 Driver C+E",
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
    published = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"p7-{form_id}"},
        json={
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ]
        },
    )
    assert published.status_code == 200, published.text
    return slug


@pytest.mark.asyncio
async def test_p7_get_apply_includes_form_runtime(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_published_form(client, tenant_id)
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "p7-runtime@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    assert not create.json().get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body.get("form_presentation") is None
    runtime = body.get("form_runtime")
    assert runtime is not None
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT
    field_ids = {
        str(f.get("qualified_code") or "")
        for f in (runtime.get("fields") or [])
        if isinstance(f, dict)
    }
    assert "recruitment.candidate.first_name" in field_ids
    schema = runtime.get("field_schema") or {}
    assert schema.get("entity_profile_code") == DRIVER_CE_PROFILE_CODE or runtime.get(
        "entity_profile_code"
    ) == DRIVER_CE_PROFILE_CODE


@pytest.mark.asyncio
async def test_p7_unpublished_form_is_not_served_live(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="legacy-no-bind", publish=False)
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "legacy-nobind@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 404, create.text


@pytest.mark.asyncio
async def test_p7_submit_presentation_required_validation(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_published_form(client, tenant_id)
    email = f"p7-val-{uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    token = create.json()["token"]
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
    detail = submit.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "runtime_required_fields"


@pytest.mark.asyncio
async def test_p7_submit_presentation_creates_lead_draft_not_candidate(client: AsyncClient, tenant_id: str) -> None:
    """Create uses lead draft (no direct Candidate); values persist for Form Runtime serve.

    Destination dispatch / application result is leftover submit, not FP-3 public serve.
    """
    slug = await _seed_published_form(client, tenant_id)
    email = f"p7-submit-{uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    body = create.json()
    token = body["token"]
    lead_id = body.get("lead_id")
    assert lead_id
    assert not body.get("candidate_id")

    async with async_session_maker() as session:
        count = await session.scalar(
            select(func.count()).select_from(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.email == email,
                Candidate.deleted_at.is_(None),
            )
        )
        assert int(count or 0) == 0

    put = await client.put(
        f"/api/v1/public/apply/{token}",
        headers=_headers(tenant_id),
        json={
            "data": {
                "contacts": {},
                "personal": {},
                "experience": {},
                "employments": [],
                "agreements": {},
                "presentation_values": {
                    "recruitment.candidate.first_name": "Jan",
                    "recruitment.candidate.last_name": "Kowalski",
                    "recruitment.candidate.contacts.phone": "+48111222333",
                },
            }
        },
    )
    assert put.status_code == 200, put.text
    put_body = put.json()
    pv = (put_body.get("data") or {}).get("presentation_values") or {}
    assert pv.get("recruitment.candidate.first_name") == "Jan"

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    served = get_resp.json()
    assert served.get("form_presentation") is None
    runtime = served.get("form_runtime")
    assert runtime is not None
    assert runtime["contract"] == RUNTIME_MODEL_CONTRACT
    assert served.get("lead_id") == lead_id


def test_p7_bridge_apply_and_validate_required() -> None:
    state: dict = {}
    apply_presentation_values_to_state(
        state,
        {
            "recruitment.candidate.first_name": "Anna",
            "recruitment.candidate.last_name": "Nowak",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
    )
    presentation = {
        "fields": [
            {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
            {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
        ]
    }
    assert validate_presentation_required_fields(presentation, state) == []

    state_incomplete = {"presentation_values_v1": {"recruitment.candidate.first_name": "Anna"}}
    missing = validate_presentation_required_fields(presentation, state_incomplete)
    assert "recruitment.candidate.last_name" in missing
