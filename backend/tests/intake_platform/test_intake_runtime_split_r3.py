"""Intake Runtime Split R3 / R3.5 — Flights dispatch + package isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DISPATCHER_SALES_INQUIRY,
)
from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT,
    HANDLER_RECRUITMENT_LEAD_DRAFT,
    HANDLER_SALES_INQUIRY_DRAFT,
    LEGACY_FORBIDDEN_HANDLERS,
)
from backend.app.forms_platform.handlers import resolve_submission_handler
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
    DestinationHandlerDomainError,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import (
    DESTINATION_RECRUITMENT,
    DestinationMissingHandlerError,
    platform_destination_registry,
    reset_platform_destination_registry_for_tests,
)
from backend.app.intake_platform.handler_dispatch import (
    dispatch_destination_submit,
    get_handler_callable,
    registered_handler_callables,
    reset_handler_callables_for_tests,
)

from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture(autouse=True)
def _reset_registries() -> None:
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)
    yield
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)


def test_r3_sales_inquiry_resolves_flights_sales_dispatcher() -> None:
    row = resolve_submission_handler(route_intent="sales_inquiry")
    assert row["handler_id"] == DISPATCHER_SALES_INQUIRY
    assert row["module_owner"] == "flights"
    assert row["adapter_owner"] == "sales"
    assert row["handler_id"] != HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT
    assert row["handler_id"] != HANDLER_SALES_INQUIRY_DRAFT
    assert HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT in LEGACY_FORBIDDEN_HANDLERS


def test_r3_candidate_application_resolves_flights_candidate_dispatcher() -> None:
    row = resolve_submission_handler(route_intent="candidate_application")
    assert row["handler_id"] == DISPATCHER_CANDIDATE_APPLICATION
    assert row["module_owner"] == "flights"
    assert row["adapter_owner"] == "recruitment"
    assert row["handler_id"] != HANDLER_RECRUITMENT_LEAD_DRAFT


def test_r3_ports_registered_for_flights_dispatchers() -> None:
    callables = registered_handler_callables()
    assert DISPATCHER_SALES_INQUIRY in callables
    assert DISPATCHER_CANDIDATE_APPLICATION in callables
    assert HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT not in callables
    assert HANDLER_SALES_INQUIRY_DRAFT not in callables
    assert get_handler_callable(DISPATCHER_SALES_INQUIRY) is not None
    assert get_handler_callable(HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT) is None


def test_r3_missing_sales_port_is_unresolved_not_recruitment_fallback() -> None:
    reset_handler_callables_for_tests(
        {
            DISPATCHER_CANDIDATE_APPLICATION: registered_handler_callables()[
                DISPATCHER_CANDIDATE_APPLICATION
            ],
        }
    )
    with pytest.raises(DestinationMissingHandlerError) as exc:
        entry = platform_destination_registry().resolve("sales_inquiry")
        assert entry.handler_id == DISPATCHER_SALES_INQUIRY
        handler = get_handler_callable(entry.handler_id)
        if handler is None:
            raise DestinationMissingHandlerError(
                "destination handler callable is not registered",
                details={"handler_id": entry.handler_id, "reason": "missing_handler_callable"},
            )
    assert exc.value.details.get("handler_id") == DISPATCHER_SALES_INQUIRY


@pytest.mark.anyio
async def test_r3_dispatch_rejects_foreign_domain_result() -> None:
    async def _rogue(_db, **kwargs):  # noqa: ANN001, ANN003
        return DestinationHandlerResult(
            handler_id=DISPATCHER_SALES_INQUIRY,
            destination=DESTINATION_RECRUITMENT,
            route_intent="sales_inquiry",
            result_entity_type=RESULT_APPLICATION,
            decision=None,
        )

    reset_handler_callables_for_tests({DISPATCHER_SALES_INQUIRY: _rogue})
    with pytest.raises(DestinationHandlerDomainError):
        await dispatch_destination_submit(
            None,  # type: ignore[arg-type]
            route_intent="sales_inquiry",
            tenant_id="t",
            draft_lead=SimpleNamespace(id="lead-test"),  # type: ignore[arg-type]
            intake_state={},
        )


def test_r3_sales_package_must_not_import_recruitment() -> None:
    sales_root = ROOT / "modules" / "sales"
    assert sales_root.is_dir()
    forbidden = (
        "backend.app.modules.recruitment",
        "from backend.app.modules.recruitment",
        "import backend.app.modules.recruitment",
    )
    for path in sales_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} imports recruitment: {pattern}"


def test_r3_recruitment_package_must_not_import_sales() -> None:
    recruitment_root = ROOT / "modules" / "recruitment"
    assert recruitment_root.is_dir()
    forbidden = (
        "backend.app.modules.sales",
        "from backend.app.modules.sales",
        "import backend.app.modules.sales",
    )
    for path in recruitment_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} imports sales: {pattern}"


def test_r3_legacy_client_lead_draft_not_in_registry() -> None:
    ids = {e.handler_id for e in platform_destination_registry().list_entries()}
    assert HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT not in ids
    assert DISPATCHER_SALES_INQUIRY in ids


def test_r3_expected_result_entity_types() -> None:
    sales = resolve_submission_handler(route_intent="sales_inquiry")
    cand = resolve_submission_handler(route_intent="candidate_application")
    assert RESULT_SALES_INQUIRY in sales["creates"]
    assert RESULT_APPLICATION in cand["creates"]
    assert "application" not in sales["creates"]
    assert "sales_inquiry" not in cand["creates"]
