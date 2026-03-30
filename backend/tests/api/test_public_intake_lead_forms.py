"""Public intake ↔ tenant lead forms (slug / id, GET catalog)."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import TenantLicense
from backend.app.models.tenant_lead_form import TenantLeadForm

pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture(autouse=True)
async def _bump_max_candidates_for_intake_tests(tenant_id: str) -> None:
    """Default tenant DB often exceeds license cap; public intake creates new candidates."""
    async with async_session_maker() as session:
        lic = (
            await session.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
        if lic is not None:
            lic.max_candidates_active = 500_000
            await session.commit()


def _headers(tenant_id: str) -> dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


async def _seed_form(tenant_id: str, *, slug: str) -> str:
    fid = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=fid,
                tenant_id=tenant_id,
                title="Driver form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()
    return fid


@pytest.mark.asyncio
async def test_public_intake_lead_forms_list_and_create_with_slug(client: AsyncClient, tenant_id: str) -> None:
    slug = f"driver-{uuid4().hex[:10]}"
    await _seed_form(tenant_id, slug=slug)
    lf = await client.get("/api/v1/public/intake/lead-forms", headers=_headers(tenant_id))
    assert lf.status_code == 200, lf.text
    arr = [x for x in lf.json() if x.get("public_slug") == slug]
    assert len(arr) == 1
    assert arr[0]["public_slug"] == slug
    assert arr[0]["title"] == "Driver form"

    phone_suffix = uuid4().hex[:9]
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"555{phone_suffix}"},
            "lead_form_slug": slug,
        },
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    st = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert st.status_code == 200, st.text
    lf_meta = st.json().get("data", {}).get("lead_form") or {}
    assert lf_meta.get("public_slug") == slug
    assert lf_meta.get("id")


@pytest.mark.asyncio
async def test_public_intake_lead_form_wrong_slug_404(client: AsyncClient, tenant_id: str) -> None:
    await _seed_form(tenant_id, slug=f"exists-{uuid4().hex[:8]}")
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"554{uuid4().hex[:9]}"},
            "lead_form_slug": "missing-slug-xyz",
        },
    )
    assert resp.status_code == 404, resp.text
    assert resp.json().get("detail", {}).get("code") == "lead_form_not_found"


@pytest.mark.asyncio
async def test_public_intake_lead_form_id_and_slug_ambiguous_422(client: AsyncClient, tenant_id: str) -> None:
    slug = f"amb-{uuid4().hex[:10]}"
    fid = await _seed_form(tenant_id, slug=slug)
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"553{uuid4().hex[:9]}"},
            "lead_form_id": fid,
            "lead_form_slug": slug,
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json().get("detail", {}).get("code") == "lead_form_reference_ambiguous"


@pytest.mark.asyncio
async def test_public_intake_lead_form_invalid_slug_422(client: AsyncClient, tenant_id: str) -> None:
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"552{uuid4().hex[:9]}"},
            "lead_form_slug": "X",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json().get("detail", {}).get("code") == "lead_form_slug_invalid"
