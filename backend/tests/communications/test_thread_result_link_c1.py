"""C1 — Thread Result Link Contract (opaque ref + Flights provenance)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.acquisition.flights.destination_contract import OpaqueResultRef
from backend.app.communications.result_link import (
    ThreadResultLinkConflictError,
    ThreadResultLinkUnresolvedError,
    attach_thread_result_from_confirmed_ledger,
    attach_thread_result_link,
    require_confirmed_thread_result_link,
)
from backend.app.models.communication_thread_result_link import LINK_STATUS_CONFIRMED
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED


ROOT = Path(__file__).resolve().parents[2] / "app"
COMMS = ROOT / "communications"


def test_c1_communications_must_not_import_destination_orm() -> None:
    assert COMMS.is_dir()
    forbidden = (
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
    )
    for path in COMMS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} violates C1: {pattern}"


def test_c1_model_has_no_fk_to_destination_tables() -> None:
    text = (ROOT / "models" / "communication_thread_result_link.py").read_text(
        encoding="utf-8"
    )
    assert "sales_inquiries" not in text
    assert "recruitment_applications" not in text
    assert 'ForeignKey("leads' not in text
    assert "module_owner" in text
    assert "result_type" in text
    assert "result_id" in text
    assert "ledger_id" in text


@pytest.mark.anyio
async def test_c1_attach_opaque_ref_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.communications.result_link as rl

    store: dict[str, SimpleNamespace] = {}

    async def _scalar(stmt):  # noqa: ANN001
        return next(iter(store.values())) if store else None

    db = MagicMock()
    db.scalar = AsyncMock(side_effect=_scalar)
    db.flush = AsyncMock()

    def _fake_row(**kwargs):  # noqa: ANN003
        row = SimpleNamespace(**kwargs)
        if not hasattr(row, "meta") or row.meta is None:
            row.meta = {}
        store[row.thread_id] = row
        return row

    monkeypatch.setattr(rl, "_new_link_row", _fake_row)
    db.add = MagicMock()

    opaque = OpaqueResultRef(
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
    )
    first = await attach_thread_result_link(
        db,
        tenant_id="t1",
        thread_id="th-1",
        opaque=opaque,
        ledger_id="lg-1",
    )
    assert first.module_owner == "sales"
    assert first.result_id == "si-1"
    assert first.provenance_ref == "lg-1"
    assert first.status == LINK_STATUS_CONFIRMED

    second = await attach_thread_result_link(
        db,
        tenant_id="t1",
        thread_id="th-1",
        opaque=opaque,
        ledger_id="lg-1",
    )
    assert second.link_id == first.link_id
    assert len(store) == 1


@pytest.mark.anyio
async def test_c1_incompatible_second_link_fail_closed() -> None:
    existing = SimpleNamespace(
        id="link-1",
        tenant_id="t1",
        thread_id="th-1",
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
        ledger_id="lg-1",
        status=LINK_STATUS_CONFIRMED,
        meta={},
    )
    db = MagicMock()
    db.scalar = AsyncMock(return_value=existing)
    db.flush = AsyncMock()

    with pytest.raises(ThreadResultLinkConflictError) as ei:
        await attach_thread_result_link(
            db,
            tenant_id="t1",
            thread_id="th-1",
            opaque=OpaqueResultRef(
                module_owner="recruitment",
                result_type="application",
                result_id="app-9",
            ),
        )
    assert ei.value.details.get("reason") == "incompatible_result_references"


@pytest.mark.anyio
async def test_c1_require_confirmed_missing_fail_closed() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    with pytest.raises(ThreadResultLinkUnresolvedError) as ei:
        await require_confirmed_thread_result_link(
            db, tenant_id="t1", thread_id="th-missing"
        )
    assert ei.value.details.get("reason") == "missing_result_link"


@pytest.mark.anyio
async def test_c1_attach_from_unconfirmed_ledger_fail_closed() -> None:
    ledger = SimpleNamespace(
        id="lg-1",
        tenant_id="t1",
        status="dispatched",
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
    )
    db = MagicMock()
    db.get = AsyncMock(return_value=ledger)
    with pytest.raises(ThreadResultLinkUnresolvedError) as ei:
        await attach_thread_result_from_confirmed_ledger(
            db, tenant_id="t1", thread_id="th-1", ledger_id="lg-1"
        )
    assert ei.value.details.get("reason") == "unconfirmed_provenance"


@pytest.mark.anyio
async def test_c1_attach_from_confirmed_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.app.communications.result_link as rl

    ledger = SimpleNamespace(
        id="lg-1",
        tenant_id="t1",
        status=STATUS_CONFIRMED,
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
    )
    store: dict[str, SimpleNamespace] = {}

    async def _scalar(stmt):  # noqa: ANN001
        return next(iter(store.values())) if store else None

    def _fake_row(**kwargs):  # noqa: ANN003
        row = SimpleNamespace(**kwargs)
        if not hasattr(row, "meta") or row.meta is None:
            row.meta = {}
        store[row.thread_id] = row
        return row

    monkeypatch.setattr(rl, "_new_link_row", _fake_row)

    db = MagicMock()
    db.get = AsyncMock(return_value=ledger)
    db.scalar = AsyncMock(side_effect=_scalar)
    db.flush = AsyncMock()
    db.add = MagicMock()

    view = await attach_thread_result_from_confirmed_ledger(
        db, tenant_id="t1", thread_id="th-1", ledger_id="lg-1"
    )
    assert view.module_owner == "sales"
    assert view.result_type == "sales_inquiry"
    assert view.result_id == "si-1"
    assert view.ledger_id == "lg-1"
