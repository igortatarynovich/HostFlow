"""P6 — Intake Form admin read API + smoke test."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.session import async_session_maker
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_intake_demo_form import (
    DRIVER_CE_FORM_SLUG,
    ensure_tenant_default_driver_ce_intake_form,
)
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


pytestmark = pytest.mark.anyio


def _make_token(user_id: str, email: str, tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": "administrator",
        "tenant_id": tenant_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    return encode_jwt(payload)


async def _admin_headers(tenant_id: str) -> Dict[str, str]:
    data = await _init_data()
    token = _make_token(data["admin_id"], data["admin_email"], tenant_id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Tenant-Id": tenant_id,
    }


async def _seed_driver_ce_form(tenant_id: str) -> str:
    async with async_session_maker() as session:
        from backend.tests.api.test_public_intake import _ensure_recruitment_funnels

        await _ensure_recruitment_funnels(session, tenant_id)
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
        return str(form.id)


@pytest.mark.asyncio
async def test_p6_intake_form_detail_driver_ce(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.get(f"/api/v1/settings/intake-forms/{form_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["form"]["public_slug"] == DRIVER_CE_FORM_SLUG
    assert body["entity_profile"]["code"] == DRIVER_CE_PROFILE_CODE
    assert body["presentation"]["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert len(body["presentation"]["fields"]) >= 3
    assert body["submit_destination"]["creates_lead_draft_on_create"] is True
    assert body["submit_destination"]["creates_candidate_on_create"] is False
    assert body["intake_source_profile"] is not None
    assert body["intake_source_profile"]["entity_profile_code"] == DRIVER_CE_PROFILE_CODE


@pytest.mark.asyncio
async def test_p6_smoke_test_creates_lead_draft_not_candidate(client: AsyncClient, tenant_id: str) -> None:
    form_id = await _seed_driver_ce_form(tenant_id)
    headers = await _admin_headers(tenant_id)
    resp = await client.post(f"/api/v1/settings/intake-forms/{form_id}/smoke-test", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lead_id"]
    assert body["candidate_id"] in (None, "")
    assert body["token"]

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.stage == "intake_draft"
        assert not lead.candidate_id
        count = await session.scalar(
            select(Candidate).where(
                Candidate.tenant_id == tenant_id,
                Candidate.email == body["contacts"]["email"],
                Candidate.deleted_at.is_(None),
            )
        )
        assert count is None


@pytest.mark.asyncio
async def test_archive_form_with_alias_slug_binding(client: AsyncClient, tenant_id: str) -> None:
    """Shared intake profiles keep multiple public_slug keys; archive must not rename them."""
    from backend.app.models.intake_routing import IntakeSourceBinding
    from backend.app.models.intake_routing_enums import IntakeProvider
    from backend.app.modules.intake_routing import crud as intake_crud

    form_id = await _seed_driver_ce_form(tenant_id)
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form is not None
        from backend.app.entity_profile.ingest_runtime import resolve_public_intake_source_profile_id

        profile_id = await resolve_public_intake_source_profile_id(
            session,
            tenant_id=tenant_id,
            lead_form_id=form_id,
            public_slug=form.public_slug,
        )
        assert profile_id
        alias = f"public_slug:{DRIVER_CE_FORM_SLUG}-alias"
        existing = await session.scalar(
            select(IntakeSourceBinding).where(
                IntakeSourceBinding.tenant_id == tenant_id,
                IntakeSourceBinding.external_key == alias,
            )
        )
        if existing is None:
            await intake_crud.create_binding(
                session,
                tenant_id=tenant_id,
                intake_source_profile_id=profile_id,
                provider=IntakeProvider.public_intake.value,
                external_key=alias,
                priority=10,
            )
        await session.commit()

    headers = await _admin_headers(tenant_id)
    resp = await client.patch(
        f"/api/v1/settings/intake-forms/{form_id}",
        headers=headers,
        json={"lifecycle_status": "archived"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["form"]["is_active"] is False
    assert body["form_definition"]["lifecycle_status"] == "archived"

