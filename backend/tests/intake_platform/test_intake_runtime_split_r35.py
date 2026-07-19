"""R3.5 — Flights-owned dispatch boundary (L0 module independence)."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DISPATCHER_SALES_INQUIRY,
)
from backend.app.forms_platform.handlers import resolve_submission_handler
from backend.app.intake_platform.destination_registry import (
    reset_platform_destination_registry_for_tests,
)
from backend.app.intake_platform.handler_dispatch import reset_handler_callables_for_tests


ROOT = Path(__file__).resolve().parents[2] / "app"
FLIGHTS = ROOT / "acquisition" / "flights"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)
    yield
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)


def test_r35_flights_package_must_not_import_destination_orm_or_services() -> None:
    assert FLIGHTS.is_dir()
    forbidden = (
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "inquiry_draft_handler",
        "lead_draft_handler",
        "ensure_sales_inquiry_for_transport_lead",
        "ensure_application_result_for_transport_lead",
    )
    for path in FLIGHTS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} violates L0: {pattern}"


def test_r35_flights_may_import_only_port_adapters_from_modules() -> None:
    """Dispatcher may lazy-import published adapters — not domain handlers."""
    text = (FLIGHTS / "dispatcher.py").read_text(encoding="utf-8")
    assert "port_adapter" in text
    assert "inquiry_draft_handler" not in text
    assert "lead_draft_handler" not in text


def test_r35_registry_module_owner_is_flights() -> None:
    cand = resolve_submission_handler(route_intent="candidate_application")
    sales = resolve_submission_handler(route_intent="sales_inquiry")
    assert cand["module_owner"] == "flights"
    assert sales["module_owner"] == "flights"
    assert cand["handler_id"] == DISPATCHER_CANDIDATE_APPLICATION
    assert sales["handler_id"] == DISPATCHER_SALES_INQUIRY


def test_r35_destination_adapters_exist() -> None:
    assert (ROOT / "modules" / "recruitment" / "intake" / "port_adapter.py").is_file()
    assert (ROOT / "modules" / "sales" / "intake" / "port_adapter.py").is_file()
