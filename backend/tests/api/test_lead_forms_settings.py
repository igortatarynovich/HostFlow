"""Settings lead-forms API + cap enforcement (§2.16)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import DEFAULT_TENANT_ID, _init_data

LF_BASE = "/api/v1/settings/lead-forms"


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


async def _admin_headers() -> Dict[str, str]:
    data = await _init_data()
    token = _make_token(data["admin_id"], data["admin_email"], data["tenant_id"])
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Tenant-Id": data["tenant_id"],
    }


async def _patch_tenant_subscription(*, plan_code: str) -> None:
    async with async_session_maker() as session:
        await session.execute(delete(TenantLeadForm).where(TenantLeadForm.tenant_id == DEFAULT_TENANT_ID))
        tenant = await session.get(Tenant, DEFAULT_TENANT_ID)
        assert tenant is not None
        st = dict(tenant.settings or {})
        bill = dict(st.get("billing") or {})
        sub = dict(bill.get("subscription") or {})
        sub["plan_code"] = plan_code
        sub["status"] = "active"
        sub["provider"] = "mock"
        bill["subscription"] = sub
        st["billing"] = bill
        usage = dict(st.get("usage_v1") or {})
        packs = dict(usage.get("pack_addons_v1") or {})
        packs.pop("lead_forms_active_cap", None)
        usage["pack_addons_v1"] = packs
        st["usage_v1"] = usage
        tenant.settings = st
        lic = (
            await session.execute(
                select(TenantLicense).where(TenantLicense.tenant_id == DEFAULT_TENANT_ID).limit(1)
            )
        ).scalar_one_or_none()
        if lic is not None:
            lic.plan = plan_code
        await session.commit()


@pytest.mark.anyio
async def test_lead_forms_fourth_active_on_team_plan_402(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")
    for i in range(3):
        r = await client.post(LF_BASE, headers=headers, json={"title": f"Form {i}"})
        assert r.status_code == 200, r.text
    r4 = await client.post(LF_BASE, headers=headers, json={"title": "Form overflow"})
    assert r4.status_code == 402, r4.text
    body = r4.json()
    assert body.get("detail", {}).get("code") == "lead_forms_limit_reached"


@pytest.mark.anyio
async def test_lead_form_public_slug_conflict_409(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")
    a = await client.post(LF_BASE, headers=headers, json={"title": "A"})
    b = await client.post(LF_BASE, headers=headers, json={"title": "B"})
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)
    id_a = a.json()["id"]
    id_b = b.json()["id"]
    p1 = await client.patch(f"{LF_BASE}/{id_a}", headers=headers, json={"public_slug": "careers-main"})
    assert p1.status_code == 200, p1.text
    p2 = await client.patch(f"{LF_BASE}/{id_b}", headers=headers, json={"public_slug": "careers-main"})
    assert p2.status_code == 409, p2.text
    assert p2.json().get("detail", {}).get("code") == "lead_form_public_slug_taken"


@pytest.mark.anyio
async def test_archived_form_hidden_from_default_list(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")
    created = await client.post(LF_BASE, headers=headers, json={"title": "Disposable form"})
    assert created.status_code == 200, created.text
    form_id = created.json()["id"]

    archived = await client.patch(
        f"/api/v1/settings/intake-forms/{form_id}",
        headers=headers,
        json={"lifecycle_status": "archived"},
    )
    assert archived.status_code == 200, archived.text

    listed = await client.get(LF_BASE, headers=headers)
    assert listed.status_code == 200, listed.text
    assert all(row["id"] != form_id for row in listed.json())

    with_archived = await client.get(f"{LF_BASE}?include_archived=true", headers=headers)
    assert with_archived.status_code == 200, with_archived.text
    match = next(row for row in with_archived.json() if row["id"] == form_id)
    assert match["lifecycle_status"] == "archived"
    assert match["is_active"] is False
