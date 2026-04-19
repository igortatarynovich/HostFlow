"""Public intake ↔ tenant lead forms (slug / id, GET catalog)."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text

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


@pytest.mark.asyncio
async def test_public_intake_resolves_tenant_from_slug_without_x_tenant_header(
    client: AsyncClient, tenant_id: str
) -> None:
    """Candidates must land in the form owner's tenant even if the browser sends another X-Tenant-Id (or none)."""
    slug = f"no-header-{uuid4().hex[:10]}"
    await _seed_form(tenant_id, slug=slug)
    phone_suffix = uuid4().hex[:9]
    create = await client.post(
        "/api/v1/public/intake",
        headers={"X-Tenant-Id": "22222222-2222-2222-2222-222222222222"},
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"551{phone_suffix}"},
            "lead_form_slug": slug,
        },
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    st = await client.get(f"/api/v1/public/apply/{token}")
    assert st.status_code == 200, st.text
    assert st.json().get("candidate_id")
    lf = await client.get(f"/api/v1/public/intake/lead-forms?public_slug={slug}")
    assert lf.status_code == 200, lf.text
    assert len(lf.json()) == 1
    assert lf.json()[0].get("public_slug") == slug


@pytest.mark.asyncio
async def test_public_intake_without_slug_requires_non_default_tenant(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/public/intake",
        headers={"X-Tenant-Id": "11111111-1111-1111-1111-111111111111"},
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"550{uuid4().hex[:9]}"},
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail", {}).get("code") == "intake_default_tenant_forbidden"


@pytest.mark.asyncio
async def test_public_intake_without_slug_and_no_header_is_400(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/public/intake",
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"549{uuid4().hex[:9]}"},
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail", {}).get("code") == "intake_tenant_required"


@pytest.mark.asyncio
async def test_public_magic_link_request_uses_intake_token_not_x_tenant_header(
    client: AsyncClient, tenant_id: str
) -> None:
    """Resend-magic-link must find the candidate in the form owner's tenant even if the browser sends demo X-Tenant-Id."""
    slug = f"ml-tok-{uuid4().hex[:8]}"
    await _seed_form(tenant_id, slug=slug)
    email = f"ml-{uuid4().hex[:8]}@example.com"
    create = await client.post(
        "/api/v1/public/intake",
        headers={"X-Tenant-Id": "22222222-2222-2222-2222-222222222222"},
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    intake_token = create.json()["token"]

    req = await client.post(
        "/api/v1/public/magic-link/request",
        headers={"X-Tenant-Id": "11111111-1111-1111-1111-111111111111"},
        json={"email": email, "intake_token": intake_token},
    )
    assert req.status_code == 200, req.text

    async with async_session_maker() as session:
        r = await session.execute(
            text("SELECT tenant_id FROM magic_links WHERE contact_value = :cv LIMIT 1"),
            {"cv": email.lower()},
        )
        row = r.first()
        assert row is not None
        assert row[0] == tenant_id
