"""Stripe webhook idempotency (claim + release) and invoice.finalized (§2.18)."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.api.v1.settings import billing
from backend.app.db.session import async_session_maker
from backend.app.models.stripe_webhook_event import StripeWebhookEventLog
from backend.app.models.tenant import Tenant
from backend.tests.conftest import DEFAULT_TENANT_ID


@pytest.mark.anyio
async def test_stripe_webhook_try_claim_event_second_call_false() -> None:
    eid = f"evt_test_claim_once_{uuid4().hex}"
    async with async_session_maker() as db:
        first = await billing._stripe_webhook_try_claim_event(db, eid, "checkout.session.completed")
        assert first is True
        second = await billing._stripe_webhook_try_claim_event(db, eid, "checkout.session.completed")
        assert second is False


@pytest.mark.anyio
async def test_stripe_webhook_release_claim_allows_retry() -> None:
    eid = f"evt_test_release_retry_{uuid4().hex}"
    async with async_session_maker() as db:
        assert await billing._stripe_webhook_try_claim_event(db, eid, "invoice.paid") is True
        await billing._stripe_webhook_release_claim(db, eid)
        assert await billing._stripe_webhook_try_claim_event(db, eid, "invoice.paid") is True


@pytest.mark.anyio
async def test_handle_invoice_finalized_appends_history() -> None:
    suffix = uuid4().hex[:12]
    customer_id = f"cus_test_finalized_{suffix}"
    async with async_session_maker() as db:
        tenant = await db.get(Tenant, DEFAULT_TENANT_ID)
        assert tenant is not None
        st: dict[str, Any] = dict(tenant.settings or {})
        bill = dict(st.get("billing") or {})
        sub = dict(bill.get("subscription") or {})
        sub["customer_id"] = customer_id
        sub["subscription_id"] = f"sub_test_finalized_{suffix}"
        sub["plan_code"] = "team"
        sub["status"] = "active"
        bill["subscription"] = sub
        st["billing"] = bill
        tenant.settings = st
        await db.commit()

    inv_id = f"in_test_finalized_{suffix}"
    obj: Dict[str, Any] = {
        "id": inv_id,
        "customer": customer_id,
        "subscription": f"sub_test_finalized_{suffix}",
        "currency": "eur",
        "amount_due": 12900,
        "hosted_invoice_url": "https://stripe.example/inv",
        "invoice_pdf": "https://stripe.example/inv.pdf",
        "lines": {"data": []},
    }

    async with async_session_maker() as db:
        detail = await billing._handle_invoice_finalized(db, obj)
        assert "Processed invoice.finalized" in detail

    async with async_session_maker() as db:
        tenant = await db.get(Tenant, DEFAULT_TENANT_ID)
        assert tenant is not None
        hist = billing._billing_history(tenant)
        assert any(str(h.get("dedupe_key") or "") == f"stripe:{inv_id}:invoice.finalized" for h in hist)

    async with async_session_maker() as db:
        detail2 = await billing._handle_invoice_finalized(db, obj)
        assert "Skipped duplicate" in detail2


@pytest.mark.anyio
async def test_stripe_webhook_endpoint_duplicate_ignored(client: AsyncClient) -> None:
    dup_id = f"evt_dup_{uuid4().hex}"
    payload = (
        b'{"id":"'
        + dup_id.encode()
        + b'","type":"customer.subscription.updated","data":{"object":{"id":"sub_x","customer":"cus_x","status":"active"}}}'
    )
    fake_event = MagicMock()
    fake_event.id = dup_id
    fake_event.type = "customer.subscription.updated"
    fake_event.data = MagicMock()
    fake_event.data.object = {"id": "sub_x", "customer": "cus_x", "status": "active"}

    prev_secret = billing.settings.stripe_webhook_secret
    prev_key = billing.settings.stripe_secret_key
    prev_stripe = billing.stripe
    billing.settings.stripe_webhook_secret = "whsec_test"
    billing.settings.stripe_secret_key = "sk_test"
    mock_stripe_mod = MagicMock()
    mock_stripe_mod.Webhook.construct_event = MagicMock(return_value=fake_event)
    try:
        with patch.object(billing, "stripe", mock_stripe_mod):
            r1 = await client.post(
                "/api/v1/settings/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": "t=1,v1=fake"},
            )
            r2 = await client.post(
                "/api/v1/settings/billing/webhook",
                content=payload,
                headers={"Stripe-Signature": "t=1,v1=fake"},
            )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert "Duplicate" in (r2.json().get("detail") or "")
    finally:
        billing.settings.stripe_webhook_secret = prev_secret
        billing.settings.stripe_secret_key = prev_key
        billing.stripe = prev_stripe

    async with async_session_maker() as db:
        row = (
            await db.execute(select(StripeWebhookEventLog).where(StripeWebhookEventLog.event_id == dup_id))
        ).scalar_one_or_none()
        assert row is not None
