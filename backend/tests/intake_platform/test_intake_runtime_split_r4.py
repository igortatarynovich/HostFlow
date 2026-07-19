"""Intake Runtime Split R4 — independent Application / SalesInquiry result objects."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_LEAD_DRAFT,
    HANDLER_SALES_INQUIRY_DRAFT,
)
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
    DestinationHandlerDomainError,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import (
    DESTINATION_RECRUITMENT,
    DESTINATION_SALES,
)
from backend.app.intake_platform.handler_dispatch import (
    dispatch_destination_submit,
    reset_handler_callables_for_tests,
)
from backend.app.intake_platform.destination_registry import reset_platform_destination_registry_for_tests
from backend.app.modules.recruitment.services.application_result_service import (
    ApplicationTransportConflictError,
    _stamp_transport_link,
)
from backend.app.modules.sales.services.sales_inquiry_service import (
    SalesInquiryTransportConflictError,
    _stamp_transport_link as _stamp_sales_link,
)


ROOT = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture(autouse=True)
def _reset_registries() -> None:
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)
    yield
    reset_platform_destination_registry_for_tests()
    reset_handler_callables_for_tests(None)


def test_r4_typed_result_requires_id_when_created() -> None:
    row = DestinationHandlerResult(
        handler_id=HANDLER_SALES_INQUIRY_DRAFT,
        destination=DESTINATION_SALES,
        route_intent="sales_inquiry",
        result_entity_type=RESULT_SALES_INQUIRY,
        decision=None,
        result_created=True,
        result_entity_id=None,
    )
    with pytest.raises(DestinationHandlerDomainError):
        row.assert_owns_domain(
            expected_destination=DESTINATION_SALES,
            expected_result=RESULT_SALES_INQUIRY,
            require_result_id=True,
        )


def test_r4_sales_handler_cannot_return_application() -> None:
    row = DestinationHandlerResult(
        handler_id=HANDLER_SALES_INQUIRY_DRAFT,
        destination=DESTINATION_SALES,
        route_intent="sales_inquiry",
        result_entity_type=RESULT_APPLICATION,
        decision=None,
        result_entity_id="app-1",
        result_created=True,
    )
    with pytest.raises(DestinationHandlerDomainError):
        row.assert_owns_domain(
            expected_destination=DESTINATION_SALES,
            expected_result=RESULT_SALES_INQUIRY,
        )


def test_r4_recruitment_handler_cannot_return_sales_inquiry() -> None:
    row = DestinationHandlerResult(
        handler_id=HANDLER_RECRUITMENT_LEAD_DRAFT,
        destination=DESTINATION_RECRUITMENT,
        route_intent="candidate_application",
        result_entity_type=RESULT_SALES_INQUIRY,
        decision=None,
        result_entity_id="si-1",
        result_created=True,
    )
    with pytest.raises(DestinationHandlerDomainError):
        row.assert_owns_domain(
            expected_destination=DESTINATION_RECRUITMENT,
            expected_result=RESULT_APPLICATION,
        )


@pytest.mark.anyio
async def test_r4_dispatch_rejects_sales_returning_application() -> None:
    async def _rogue(_db, **kwargs):  # noqa: ANN001, ANN003
        return DestinationHandlerResult(
            handler_id=HANDLER_SALES_INQUIRY_DRAFT,
            destination=DESTINATION_SALES,
            route_intent="sales_inquiry",
            result_entity_type=RESULT_APPLICATION,
            decision=None,
            result_entity_id="app-x",
            result_created=True,
        )

    reset_handler_callables_for_tests({HANDLER_SALES_INQUIRY_DRAFT: _rogue})
    with pytest.raises(DestinationHandlerDomainError):
        await dispatch_destination_submit(
            None,  # type: ignore[arg-type]
            route_intent="sales_inquiry",
            tenant_id="t",
            draft_lead=None,  # type: ignore[arg-type]
            intake_state={},
        )


def test_r4_transport_cannot_link_both_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.modules.recruitment.services.application_result_service.flag_modified",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "backend.app.modules.sales.services.sales_inquiry_service.flag_modified",
        lambda *_a, **_k: None,
    )
    lead = SimpleNamespace(id="lead-1", normalized={})
    _stamp_transport_link(lead, application_id="app-1")  # type: ignore[arg-type]
    with pytest.raises(SalesInquiryTransportConflictError):
        _stamp_sales_link(lead, sales_inquiry_id="si-1")  # type: ignore[arg-type]

    lead2 = SimpleNamespace(id="lead-2", normalized={})
    _stamp_sales_link(lead2, sales_inquiry_id="si-2")  # type: ignore[arg-type]
    with pytest.raises(ApplicationTransportConflictError):
        _stamp_transport_link(lead2, application_id="app-2")  # type: ignore[arg-type]


def test_r4_sales_package_still_isolated_from_recruitment() -> None:
    sales_root = ROOT / "modules" / "sales"
    forbidden = (
        "backend.app.modules.recruitment",
        "from backend.app.modules.recruitment",
        "import backend.app.modules.recruitment",
    )
    for path in sales_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} imports recruitment"


def test_r4_recruitment_package_still_isolated_from_sales() -> None:
    recruitment_root = ROOT / "modules" / "recruitment"
    forbidden = (
        "backend.app.modules.sales",
        "from backend.app.modules.sales",
        "import backend.app.modules.sales",
    )
    for path in recruitment_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path} imports sales"


def test_r4_lead_to_sales_inquiry_marked_legacy() -> None:
    text = (ROOT / "modules" / "applications" / "mappers.py").read_text(encoding="utf-8")
    assert "LEGACY PROJECTION" in text
    assert "SalesInquiry" in text


@pytest.mark.anyio
async def test_r4_ensure_sales_inquiry_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.modules.sales.services import sales_inquiry_service as svc

    monkeypatch.setattr(svc, "flag_modified", lambda *_a, **_k: None)

    existing = SimpleNamespace(id="si-existing", lead_id="lead-1")
    lead = SimpleNamespace(id="lead-1", normalized={}, own_company_id=None, assigned_to=None, recruiter_id=None)

    async def _scalar(stmt):  # noqa: ANN001
        return existing

    db = MagicMock()
    db.scalar = AsyncMock(side_effect=_scalar)
    db.flush = AsyncMock()
    db.add = MagicMock()

    row = await svc.ensure_sales_inquiry_for_transport_lead(
        db,
        tenant_id="tenant-1",
        lead=lead,  # type: ignore[arg-type]
        idempotency_key="key-1",
    )
    assert row.id == "si-existing"
    db.add.assert_not_called()
