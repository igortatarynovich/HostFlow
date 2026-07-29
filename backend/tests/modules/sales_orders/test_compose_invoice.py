"""Unit tests for compose_invoice validation paths."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.sales_orders.compose_invoice import (
    ComposeInvoiceError,
    compose_invoice_from_billables,
)


@pytest.mark.asyncio
async def test_compose_requires_ids():
    db = AsyncMock()
    with pytest.raises(ComposeInvoiceError) as exc:
        await compose_invoice_from_billables(
            db,
            tenant_id="t1",
            sales_order_id="o1",
            billable_item_ids=[],
            actor_user_id="u1",
        )
    assert exc.value.code == "empty"


@pytest.mark.asyncio
async def test_compose_order_not_found():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(ComposeInvoiceError) as exc:
        await compose_invoice_from_billables(
            db,
            tenant_id="t1",
            sales_order_id="o1",
            billable_item_ids=["b1"],
            actor_user_id="u1",
        )
    assert exc.value.code == "not_found"


@pytest.mark.asyncio
async def test_compose_rejects_void():
    db = AsyncMock()
    order = SimpleNamespace(id="o1", tenant_id="t1", company_id="c1", payer_company_id=None)
    billable = SimpleNamespace(
        id="b1",
        status="void",
        invoice_id=None,
        currency="PLN",
        amount=100,
        quantity=1,
        sales_order_line_id=None,
        trigger_code="candidate_hired",
        notes=None,
    )

    async def _get(model, key):
        if getattr(model, "__name__", "") == "SalesOrder":
            return order
        return None

    db.get = AsyncMock(side_effect=_get)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [billable]
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(ComposeInvoiceError) as exc:
        await compose_invoice_from_billables(
            db,
            tenant_id="t1",
            sales_order_id="o1",
            billable_item_ids=["b1"],
            actor_user_id="u1",
        )
    assert exc.value.code == "void"


@pytest.mark.asyncio
async def test_compose_creates_and_marks_invoiced():
    db = AsyncMock()
    order = SimpleNamespace(
        id="o1",
        tenant_id="t1",
        company_id="c1",
        payer_company_id=None,
        currency="PLN",
        payment_term_days=14,
        vat_rate=23,
        billing_notes=None,
    )
    billable = SimpleNamespace(
        id="b1",
        status="pending",
        invoice_id=None,
        currency="PLN",
        amount=500,
        quantity=1,
        sales_order_line_id="line1",
        trigger_code="candidate_hired",
        notes=None,
    )
    line = SimpleNamespace(id="line1", title="Magazynier")
    invoice = SimpleNamespace(id="inv1", invoice_number="INV/1", status="draft", currency="PLN", total_amount=500)

    async def _get(model, key):
        name = getattr(model, "__name__", "")
        if name == "SalesOrder":
            return order
        return None

    db.get = AsyncMock(side_effect=_get)

    billables_result = MagicMock()
    billables_result.scalars.return_value.all.return_value = [billable]
    lines_result = MagicMock()
    lines_result.scalars.return_value.all.return_value = [line]
    db.execute = AsyncMock(side_effect=[billables_result, lines_result])
    db.flush = AsyncMock()

    with patch(
        "backend.app.modules.sales_orders.compose_invoice.invoice_crud.create_invoice",
        new=AsyncMock(return_value=invoice),
    ) as create_mock:
        out = await compose_invoice_from_billables(
            db,
            tenant_id="t1",
            sales_order_id="o1",
            billable_item_ids=["b1"],
            actor_user_id="u1",
            own_company_id="own1",
        )

    assert out is invoice
    assert billable.status == "invoiced"
    assert billable.invoice_id == "inv1"
    create_mock.assert_awaited_once()
    payload = create_mock.await_args.args[2]
    assert payload["order_id"] == "o1"
    assert payload["company_id"] == "c1"
    assert len(payload["items"]) == 1
    assert "Magazynier" in payload["items"][0]["description"]
