"""Unit tests for ADR-032 Sales billable accrual helpers."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.modules.sales_orders import accrual


def test_dec_helpers():
    assert accrual._dec(None) == Decimal("0")
    assert accrual._dec("12.50") == Decimal("12.50")
    assert accrual._dec(3) == Decimal("3")


@pytest.mark.asyncio
async def test_accrue_hired_skips_without_vacancy():
    db = AsyncMock()
    out = await accrual.accrue_on_candidate_hired(
        db, tenant_id="t1", candidate_id="c1", vacancy_id=None
    )
    assert out is None
    db.get.assert_not_called()


@pytest.mark.asyncio
async def test_accrue_hired_skips_freeform_vacancy():
    db = AsyncMock()
    vac = SimpleNamespace(id="v1", tenant_id="t1", order_line_id=None)
    db.get = AsyncMock(return_value=vac)
    out = await accrual.accrue_on_candidate_hired(
        db, tenant_id="t1", candidate_id="c1", vacancy_id="v1"
    )
    assert out is None


@pytest.mark.asyncio
async def test_accrue_hired_creates_when_trigger_matches():
    db = AsyncMock()
    vac = SimpleNamespace(id="v1", tenant_id="t1", order_line_id="line1")
    line = SimpleNamespace(
        id="line1",
        tenant_id="t1",
        sales_order_id="ord1",
        billing_trigger="candidate_hired",
        unit_rate=Decimal("500.00"),
        quantity_needed=2,
    )
    order = SimpleNamespace(id="ord1", tenant_id="t1", currency="PLN")

    async def _get(model, key):
        name = getattr(model, "__name__", str(model))
        if "Vacancy" in name:
            return vac
        if "SalesOrderLine" in name:
            return line
        if "SalesOrder" in name and "Line" not in name and "Billable" not in name:
            return order
        return None

    db.get = AsyncMock(side_effect=_get)
    # no existing billable
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    out = await accrual.accrue_on_candidate_hired(
        db, tenant_id="t1", candidate_id="c1", vacancy_id="v1"
    )
    assert out is not None
    assert out.trigger_code == "candidate_hired"
    assert out.amount == Decimal("500.00")
    assert out.source_entity_id == "c1"
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_accrue_hired_idempotent():
    db = AsyncMock()
    vac = SimpleNamespace(id="v1", tenant_id="t1", order_line_id="line1")
    line = SimpleNamespace(
        id="line1",
        tenant_id="t1",
        sales_order_id="ord1",
        billing_trigger="candidate_hired",
        unit_rate=Decimal("100"),
        quantity_needed=1,
    )
    order = SimpleNamespace(id="ord1", tenant_id="t1", currency="EUR")
    existing = SimpleNamespace(id="bi1", trigger_code="candidate_hired")

    async def _get(model, key):
        name = getattr(model, "__name__", str(model))
        if "Vacancy" in name:
            return vac
        if "SalesOrderLine" in name:
            return line
        if "SalesOrder" in name and "Line" not in name:
            return order
        return None

    db.get = AsyncMock(side_effect=_get)
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    db.execute = AsyncMock(return_value=result)

    out = await accrual.accrue_on_candidate_hired(
        db, tenant_id="t1", candidate_id="c1", vacancy_id="v1"
    )
    assert out is existing
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_notify_contract_ignores_non_hired_stage():
    from backend.app.modules.sales_orders.contracts import notify_candidate_hired

    db = AsyncMock()
    await notify_candidate_hired(
        db,
        tenant_id="t1",
        candidate_id="c1",
        vacancy_id="v1",
        stage_code="interview",
    )
    db.get.assert_not_called()


@pytest.mark.asyncio
async def test_headcount_completed_when_filled():
    db = AsyncMock()
    vac = SimpleNamespace(id="v1", tenant_id="t1", order_line_id="line1")
    line = SimpleNamespace(
        id="line1",
        tenant_id="t1",
        sales_order_id="ord1",
        billing_trigger="headcount_completed",
        unit_rate=Decimal("200"),
        quantity_needed=2,
    )
    order = SimpleNamespace(id="ord1", tenant_id="t1", currency="PLN")

    async def _get(model, key):
        name = getattr(model, "__name__", str(model))
        if "Vacancy" in name:
            return vac
        if "SalesOrderLine" in name:
            return line
        if "SalesOrder" in name and "Line" not in name and "Billable" not in name:
            return order
        return None

    db.get = AsyncMock(side_effect=_get)

    # first execute: count hired = 2; second: no existing billable
    count_result = MagicMock()
    count_result.scalar.return_value = 2
    empty_existing = MagicMock()
    empty_existing.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(side_effect=[count_result, empty_existing])
    db.add = MagicMock()
    db.flush = AsyncMock()

    out = await accrual.accrue_on_candidate_hired(
        db, tenant_id="t1", candidate_id="c1", vacancy_id="v1"
    )
    assert out is not None
    assert out.trigger_code == "headcount_completed"
    assert out.amount == Decimal("400")
    assert out.quantity == Decimal("2")
