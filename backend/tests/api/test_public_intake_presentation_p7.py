"""P7 — Public form runtime wiring (form_presentation_runtime_v1)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.presentation_runtime import FORM_PRESENTATION_RUNTIME_V1
from backend.app.entity_profile.public_intake_presentation_bridge import (
    apply_presentation_values_to_state,
    validate_presentation_required_fields,
)
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_intake_demo_form import (
    DRIVER_CE_FORM_SLUG,
    ensure_tenant_default_driver_ce_intake_form,
)
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.api.test_public_intake import _headers, _seed_active_lead_form


pytestmark = pytest.mark.anyio


async def _seed_driver_ce(tenant_id: str) -> str:
    async with async_session_maker() as session:
        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_tenant_default_driver_ce_intake_form(session, tenant_id)
        await session.commit()
        form = await session.scalar(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug == DRIVER_CE_FORM_SLUG,
            )
        )
        assert form is not None
        return str(form.public_slug)


@pytest.mark.asyncio
async def test_p7_get_apply_includes_presentation_runtime(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_driver_ce(tenant_id)
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
    fp = body.get("form_presentation")
    assert fp is not None
    assert fp["contract_version"] == FORM_PRESENTATION_RUNTIME_V1
    assert fp["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert len(fp.get("fields") or []) == 3
    labels = {f["qualified_code"]: f["label"] for f in fp["fields"]}
    assert labels["recruitment.candidate.first_name"] == "Imię"


@pytest.mark.asyncio
async def test_p7_legacy_form_without_binding_has_no_presentation(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="legacy-no-bind")
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "legacy-nobind@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json().get("form_presentation") is None


@pytest.mark.asyncio
async def test_p7_submit_presentation_required_validation(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_driver_ce(tenant_id)
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "p7-val@example.com"}, "lead_form_slug": slug},
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
    assert detail.get("code") == "presentation_required_fields"


@pytest.mark.asyncio
async def test_p7_submit_presentation_creates_lead_draft_not_candidate(client: AsyncClient, tenant_id: str) -> None:
    """Create uses lead draft (no direct Candidate); submit persists presentation values."""
    slug = await _seed_driver_ce(tenant_id)
    from uuid import uuid4

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

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text
    submitted = submit.json()
    assert submitted.get("status") == "submitted"
    assert submitted.get("lead_id") == lead_id

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead.stage == "questionnaire_submitted"
        from backend.app.entity_profile.public_intake_draft_session import get_public_intake_draft_block

        block = get_public_intake_draft_block(lead)
        state = block.get("intake_state") or {}
        assert state.get("presentation_values_v1", {}).get("recruitment.candidate.first_name") == "Jan"


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
