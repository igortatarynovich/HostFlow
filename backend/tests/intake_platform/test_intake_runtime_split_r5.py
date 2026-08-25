"""R5 — Flights dispatch provenance / exactly-once ledger."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
    DestinationDispatchResult,
    OpaqueResultRef,
)
from backend.app.acquisition.flights.dispatch_ledger import (
    DispatchProvenanceError,
    build_dispatch_idempotency_key,
    extract_handoff_id,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_SALES
from backend.app.intake_platform.destination_registry import reset_platform_destination_registry_for_tests
from backend.app.intake_platform.handler_dispatch import (
    dispatch_destination_submit,
    reset_handler_callables_for_tests,
)
from backend.app.models.flight_dispatch_ledger import (
    STATUS_CONFIRMED,
    FlightDispatchLedger,
)


ROOT = Path(__file__).resolve().parents[2] / "app"
FLIGHTS = ROOT / "acquisition" / "flights"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)
    yield
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)


def test_r5_idempotency_key_is_flights_scoped_not_foreign_orm() -> None:
    key = build_dispatch_idempotency_key(
        tenant_id="t1",
        transport_lead_id="lead-1",
        route_intent="sales_inquiry",
        dispatcher_id=DISPATCHER_SALES_INQUIRY,
        handoff_id="sub-9",
    )
    assert key.startswith("flights.dispatch:")
    assert "Application" not in key
    assert "SalesInquiry" not in key
    assert "sub-9" in key


def test_r5_extract_handoff_id_from_intake_state() -> None:
    assert extract_handoff_id({"submission_id": "s-1"}) == "s-1"
    assert extract_handoff_id({"intake_handoff": {"submission_id": "s-2"}}) == "s-2"
    assert extract_handoff_id({}) is None


def test_r5_flights_still_forbids_destination_orm_and_services() -> None:
    forbidden = (
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "ensure_sales_inquiry_for_transport_lead",
        "ensure_application_result_for_transport_lead",
        "SELECT … FOR UPDATE",
        "select_for_update",
        "with_for_update",
    )
    for path in FLIGHTS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} violates R5/L0: {pattern}"


def test_r5_no_shared_cross_module_transaction_helpers() -> None:
    """Flights must not coordinate destination ORM inside a joint transaction helper."""
    text = (FLIGHTS / "dispatcher.py").read_text(encoding="utf-8") + (
        FLIGHTS / "dispatch_ledger.py"
    ).read_text(encoding="utf-8")
    for pattern in (
        "RecruitmentApplication",
        "models.sales_inquiry",
        "begin_nested",
        "shared_transaction",
    ):
        assert pattern not in text, pattern


@pytest.mark.anyio
async def test_r5_replay_after_confirmed_does_not_call_adapter_twice() -> None:
    calls = {"n": 0}

    class _Port:
        async def accept(self, _db, request):  # noqa: ANN001
            calls["n"] += 1
            return DestinationDispatchResult(
                handler_id=DISPATCHER_SALES_INQUIRY,
                destination=DESTINATION_SALES,
                route_intent="sales_inquiry",
                result_entity_type=RESULT_SALES_INQUIRY,
                decision=None,
                result_entity_id="si-1",
                result_created=True,
                transport_lead_id=request.transport_lead_id,
            )

    reset_handler_callables_for_tests({DISPATCHER_SALES_INQUIRY: _Port()})

    ledger_store: dict[str, FlightDispatchLedger] = {}

    async def _scalar(stmt):  # noqa: ANN001
        if ledger_store:
            return next(iter(ledger_store.values()))
        return None

    db = MagicMock()
    db.scalar = AsyncMock(side_effect=_scalar)
    db.flush = AsyncMock()
    db.get = AsyncMock(return_value=None)

    def _add(row):  # noqa: ANN001
        ledger_store[row.idempotency_key] = row

    db.add = MagicMock(side_effect=_add)

    lead = SimpleNamespace(id="lead-1")
    first = await dispatch_destination_submit(
        db,
        route_intent="sales_inquiry",
        tenant_id="t1",
        draft_lead=lead,  # type: ignore[arg-type]
        intake_state={"submission_id": "sub-1"},
    )
    assert calls["n"] == 1
    assert first.opaque_result == OpaqueResultRef(
        module_owner="sales",
        result_type=RESULT_SALES_INQUIRY,
        result_id="si-1",
    )
    assert first.ledger_id
    row = next(iter(ledger_store.values()))
    assert row.status == STATUS_CONFIRMED
    assert row.result_id == "si-1"

    second = await dispatch_destination_submit(
        db,
        route_intent="sales_inquiry",
        tenant_id="t1",
        draft_lead=lead,  # type: ignore[arg-type]
        intake_state={"submission_id": "sub-1"},
    )
    assert calls["n"] == 1, "adapter must not be invoked again after confirmed"
    assert second.replayed_from_ledger is True
    assert second.result_entity_id == "si-1"
    assert second.opaque_result is not None
    assert second.opaque_result.result_id == "si-1"


@pytest.mark.anyio
async def test_r5_missing_result_id_fail_closed_no_recruitment_fallback() -> None:
    class _Port:
        async def accept(self, _db, request):  # noqa: ANN001
            return DestinationDispatchResult(
                handler_id=DISPATCHER_SALES_INQUIRY,
                destination=DESTINATION_SALES,
                route_intent="sales_inquiry",
                result_entity_type=RESULT_SALES_INQUIRY,
                decision=None,
                result_entity_id=None,
                result_created=True,
            )

    reset_handler_callables_for_tests({DISPATCHER_SALES_INQUIRY: _Port()})
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(Exception) as ei:
        await dispatch_destination_submit(
            db,
            route_intent="sales_inquiry",
            tenant_id="t1",
            draft_lead=SimpleNamespace(id="lead-x"),  # type: ignore[arg-type]
            intake_state={},
        )
    msg = str(ei.value).lower()
    assert "destination result object id is required" in msg or "opaque" in msg
    assert "fallback" not in msg


@pytest.mark.anyio
async def test_r5_confirmed_incomplete_opaque_fail_closed() -> None:
    from backend.app.acquisition.flights.dispatch_ledger import opaque_ref_from_ledger

    row = FlightDispatchLedger(
        id="lg-1",
        tenant_id="t1",
        idempotency_key="k",
        transport_lead_id="lead-1",
        route_intent="sales_inquiry",
        destination="sales",
        dispatcher_id=DISPATCHER_SALES_INQUIRY,
        status=STATUS_CONFIRMED,
        module_owner="sales",
        result_type=RESULT_SALES_INQUIRY,
        result_id=None,
    )
    with pytest.raises(DispatchProvenanceError) as ei:
        opaque_ref_from_ledger(row)
    assert ei.value.details.get("reason") == "ambiguous_or_missing_result"
