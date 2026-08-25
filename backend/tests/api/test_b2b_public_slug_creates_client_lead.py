"""B2B public slug forms must create Sales inquiries, not candidate drafts."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.anyio


@pytest.mark.asyncio
async def test_targeted_advertising_slug_defaults_to_client_lead(
    client: AsyncClient,
    tenant_id: str,
) -> None:
    from backend.app.db.session import async_session_maker
    from backend.tests.api.test_sales_targeted_advertising_intake import _seed_sales_profile
    from backend.app.models.tenant_lead_form import TenantLeadForm
    from sqlalchemy import select

    await _seed_sales_profile(tenant_id)

    async with async_session_maker() as db:
        form = await db.scalar(
            select(TenantLeadForm)
            .where(
                TenantLeadForm.tenant_id == str(tenant_id),
                TenantLeadForm.public_slug.is_not(None),
                TenantLeadForm.is_active.is_(True),
            )
            .limit(1)
        )
        assert form is not None
        form.purpose = "inquiry"
        form.target_entity_profile_code = "service_sales.targeted_advertising"
        slug = form.public_slug
        await db.commit()

    create = await client.post(
        "/api/v1/public/intake",
        json={
            "contacts": {"email": "b2b-slug-client@example.com", "phone": "+48111222333"},
            "source": "public_intake",
            "lead_form_slug": slug,
            # intentionally omit application_kind
        },
    )
    assert create.status_code == 200, create.text
    body = create.json()
    assert body.get("lead_id")
    assert body.get("candidate_id") in (None, "")

    token = body["token"]
    get_resp = await client.get(f"/api/v1/public/apply/{token}")
    assert get_resp.status_code == 200, get_resp.text
    state = get_resp.json()
    assert state.get("status_share_token") in (None, "")
    assert (state.get("data") or {}).get("application_kind") == "client"

    async with async_session_maker() as db:
        from backend.app.modules.leads import crud as leads_crud

        lead = await leads_crud.get_lead(db, tenant_id=tenant_id, lead_id=str(body["lead_id"]))
        assert lead is not None
        assert str(lead.lead_type) == "client"
        assert str(lead.lead_target_type) == "client_lead"
