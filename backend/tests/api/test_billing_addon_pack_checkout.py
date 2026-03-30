"""Integration tests: POST /settings/billing/addon-pack/checkout (mock / plan gates)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest
from httpx import AsyncClient

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.session import async_session_maker
from backend.app.api.v1.settings.billing import ADDON_PACK_CHECKOUT_UNAVAILABLE
from backend.app.models.tenant import Tenant
from backend.app.services.lead_quota import PLAN_LEADS_MONTHLY_LIMIT
from backend.tests.conftest import DEFAULT_TENANT_ID, _init_data

BILLING_BASE = "/api/v1/settings/billing"


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


async def _patch_tenant_subscription(*, plan_code: str, status: str = "active") -> None:
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, DEFAULT_TENANT_ID)
        assert tenant is not None
        st: dict[str, Any] = dict(tenant.settings or {})
        bill = dict(st.get("billing") or {})
        sub = dict(bill.get("subscription") or {})
        sub["plan_code"] = plan_code
        sub["status"] = status
        sub["provider"] = "mock"
        bill["subscription"] = sub
        st["billing"] = bill
        tenant.settings = st
        await session.commit()


@pytest.mark.anyio
async def test_addon_pack_unknown_sku_400(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")
    resp = await client.post(
        f"{BILLING_BASE}/addon-pack/checkout",
        headers=headers,
        json={"sku": "pack_nonexistent_sku_xyz"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail") == ADDON_PACK_CHECKOUT_UNAVAILABLE


@pytest.mark.anyio
async def test_addon_pack_lead_forms_mock_increases_cap(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")

    sum_before = await client.get(f"{BILLING_BASE}/summary", headers=headers)
    assert sum_before.status_code == 200, sum_before.text
    lf_before = sum_before.json().get("lead_forms") or {}
    cap_before = int(lf_before.get("cap") or 0)

    checkout = await client.post(
        f"{BILLING_BASE}/addon-pack/checkout",
        headers=headers,
        json={"sku": "pack_lead_forms_5"},
    )
    assert checkout.status_code == 200, checkout.text
    body = checkout.json()
    assert body.get("provider") == "mock"
    assert body.get("sku") == "pack_lead_forms_5"

    sum_after = await client.get(f"{BILLING_BASE}/summary", headers=headers)
    assert sum_after.status_code == 200, sum_after.text
    lf_after = sum_after.json().get("lead_forms") or {}
    inc = int(body.get("pack_increment") or 5)
    assert int(lf_after.get("cap") or 0) == cap_before + inc


@pytest.mark.anyio
async def test_custom_fields_pack_rejected_on_team_plan(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")
    resp = await client.post(
        f"{BILLING_BASE}/addon-pack/checkout",
        headers=headers,
        json={"sku": "pack_custom_fields_25"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail") == ADDON_PACK_CHECKOUT_UNAVAILABLE


@pytest.mark.anyio
async def test_addon_pack_requires_team_tier(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="starter")
    resp = await client.post(
        f"{BILLING_BASE}/addon-pack/checkout",
        headers=headers,
        json={"sku": "pack_leads_500"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail") == ADDON_PACK_CHECKOUT_UNAVAILABLE


@pytest.mark.anyio
async def test_addon_pack_mock_leads_increases_usage_cap(client: AsyncClient) -> None:
    headers = await _admin_headers()
    await _patch_tenant_subscription(plan_code="team")

    sum_before = await client.get(f"{BILLING_BASE}/summary", headers=headers)
    assert sum_before.status_code == 200, sum_before.text
    cap_before = int(sum_before.json()["usage_caps"]["max_leads_created_per_month"])

    checkout = await client.post(
        f"{BILLING_BASE}/addon-pack/checkout",
        headers=headers,
        json={"sku": "pack_leads_500"},
    )
    assert checkout.status_code == 200, checkout.text
    body = checkout.json()
    assert body.get("provider") == "mock"
    assert body.get("sku") == "pack_leads_500"

    sum_after = await client.get(f"{BILLING_BASE}/summary", headers=headers)
    assert sum_after.status_code == 200, sum_after.text
    cap_after = int(sum_after.json()["usage_caps"]["max_leads_created_per_month"])
    inc = int(body.get("pack_increment") or 500)
    assert cap_after == cap_before + inc
    assert inc == 500
    assert cap_after >= PLAN_LEADS_MONTHLY_LIMIT["team"]
