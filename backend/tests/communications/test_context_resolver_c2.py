"""C2 — Communication Context Resolver."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.acquisition.flights.destination_contract import (
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
)
from backend.app.communications.context_resolver import (
    RESOLVER_VERSION,
    CommunicationContextResolveError,
    resolve_communication_context,
)
from backend.app.communications.domain_registry import (
    CommunicationDomainDuplicateError,
    CommunicationDomainIncompatibleError,
    CommunicationDomainRegistry,
    CommunicationDomainUnknownOwnerError,
    CommunicationDomainUnknownTypeError,
    build_default_communication_domain_registry,
    platform_communication_domain_registry,
    reset_communication_domain_registry_for_tests,
)
from backend.app.models.communication_thread_result_link import LINK_STATUS_CONFIRMED
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED


ROOT = Path(__file__).resolve().parents[2] / "app"
COMMS = ROOT / "communications"


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    reset_communication_domain_registry_for_tests()
    yield
    reset_communication_domain_registry_for_tests()


def test_c2_communications_must_not_import_destination_orm_or_services() -> None:
    forbidden_imports = (
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "from backend.app.models.lead",
        "import backend.app.models.lead",
    )
    for path in COMMS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_imports:
            assert pattern not in text, f"{path} violates C2: {pattern}"
    resolver = (COMMS / "context_resolver.py").read_text(encoding="utf-8")
    assert "resolve_communication_context" in resolver
    assert "allowed_communication_purposes" not in resolver


def test_c2_registry_closed_and_rejects_duplicates_and_cross_owned() -> None:
    reg = build_default_communication_domain_registry()
    with pytest.raises(CommunicationDomainDuplicateError):
        reg.register(
            module_owner="sales",
            result_type=RESULT_SALES_INQUIRY,
            communication_domain="sales",
        )
    with pytest.raises(CommunicationDomainIncompatibleError):
        CommunicationDomainRegistry().register(
            module_owner="sales",
            result_type=RESULT_SALES_INQUIRY,
            communication_domain="recruitment",
        )


def test_c2_registry_fail_closed_unknown_owner_and_type() -> None:
    reg = platform_communication_domain_registry()
    with pytest.raises(CommunicationDomainUnknownOwnerError):
        reg.resolve(module_owner="billing", result_type=RESULT_APPLICATION)
    with pytest.raises(CommunicationDomainUnknownTypeError):
        reg.resolve(module_owner="sales", result_type="unknown_thing")
    with pytest.raises(CommunicationDomainIncompatibleError):
        reg.resolve(module_owner="sales", result_type=RESULT_APPLICATION)
    with pytest.raises(CommunicationDomainIncompatibleError):
        reg.resolve(module_owner="recruitment", result_type=RESULT_SALES_INQUIRY)


def _link(
    *,
    module_owner: str,
    result_type: str,
    result_id: str = "rid-1",
    status: str = LINK_STATUS_CONFIRMED,
    ledger_id: str | None = "lg-1",
    link_id: str = "link-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=link_id,
        tenant_id="t1",
        thread_id="th-1",
        module_owner=module_owner,
        result_type=result_type,
        result_id=result_id,
        ledger_id=ledger_id,
        status=status,
        meta={},
    )


def _db_with_links(rows: list[SimpleNamespace], ledger: SimpleNamespace | None = None) -> MagicMock:
    db = MagicMock()

    class _Scalars:
        def all(self):
            return rows

    class _Result:
        def scalars(self):
            return _Scalars()

    db.execute = AsyncMock(return_value=_Result())
    if ledger is not None:
        db.get = AsyncMock(return_value=ledger)
    else:
        db.get = AsyncMock(return_value=None)
    return db


@pytest.mark.anyio
async def test_c2_application_resolves_only_to_recruitment() -> None:
    ledger = SimpleNamespace(
        id="lg-1", tenant_id="t1", status=STATUS_CONFIRMED
    )
    db = _db_with_links(
        [_link(module_owner="recruitment", result_type=RESULT_APPLICATION)],
        ledger=ledger,
    )
    ctx = await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ctx.communication_domain == "recruitment"
    assert ctx.module_owner == "recruitment"
    assert ctx.result_type == RESULT_APPLICATION
    assert ctx.resolution_status == "resolved"
    assert ctx.resolver_version == RESOLVER_VERSION


@pytest.mark.anyio
async def test_c2_sales_inquiry_resolves_only_to_sales() -> None:
    ledger = SimpleNamespace(id="lg-1", tenant_id="t1", status=STATUS_CONFIRMED)
    db = _db_with_links(
        [_link(module_owner="sales", result_type=RESULT_SALES_INQUIRY)],
        ledger=ledger,
    )
    ctx = await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ctx.communication_domain == "sales"
    assert ctx.module_owner == "sales"
    assert ctx.result_type == RESULT_SALES_INQUIRY


@pytest.mark.anyio
async def test_c2_sales_inquiry_with_recruitment_owner_rejected() -> None:
    db = _db_with_links(
        [_link(module_owner="recruitment", result_type=RESULT_SALES_INQUIRY, ledger_id=None)]
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "incompatible_result_type"
    assert "recruitment" not in (ei.value.details.get("communication_domain") or "")


@pytest.mark.anyio
async def test_c2_application_with_sales_owner_rejected() -> None:
    db = _db_with_links(
        [_link(module_owner="sales", result_type=RESULT_APPLICATION, ledger_id=None)]
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "incompatible_result_type"


@pytest.mark.anyio
async def test_c2_missing_result_link_blocked() -> None:
    db = _db_with_links([])
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "missing_result_link"


@pytest.mark.anyio
async def test_c2_multiple_links_blocked() -> None:
    db = _db_with_links(
        [
            _link(module_owner="sales", result_type=RESULT_SALES_INQUIRY, link_id="a", ledger_id=None),
            _link(module_owner="sales", result_type=RESULT_SALES_INQUIRY, link_id="b", ledger_id=None),
        ]
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "multiple_active_result_links"


@pytest.mark.anyio
async def test_c2_unconfirmed_ledger_blocked() -> None:
    ledger = SimpleNamespace(id="lg-1", tenant_id="t1", status="dispatched")
    db = _db_with_links(
        [_link(module_owner="sales", result_type=RESULT_SALES_INQUIRY)],
        ledger=ledger,
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "unconfirmed_provenance"


@pytest.mark.anyio
async def test_c2_legacy_kwargs_do_not_resolve_and_are_rejected() -> None:
    db = _db_with_links(
        [_link(module_owner="sales", result_type=RESULT_SALES_INQUIRY, ledger_id=None)]
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(
            db,
            tenant_id="t1",
            thread_id="th-1",
            application_kind="candidate",
            entity_type="application",
            lead_id="lead-9",
        )
    assert ei.value.details.get("reason") == "legacy_entity_link_forbidden"


@pytest.mark.anyio
async def test_c2_lead_form_purpose_url_do_not_change_context() -> None:
    """Passing only thread_id yields same context regardless of external noise."""
    db = _db_with_links(
        [_link(module_owner="sales", result_type=RESULT_SALES_INQUIRY, ledger_id=None)]
    )
    a = await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    b = await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert a.module_owner == b.module_owner == "sales"
    assert a.result_type == b.result_type
    assert a.result_id == b.result_id
    assert a.communication_domain == b.communication_domain
    assert a.result_link_id == b.result_link_id
    assert a.resolver_version == b.resolver_version


@pytest.mark.anyio
async def test_c2_incomplete_opaque_blocked() -> None:
    bad = _link(module_owner="sales", result_type=RESULT_SALES_INQUIRY, ledger_id=None)
    bad.result_id = ""
    db = _db_with_links([bad])
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "ambiguous_or_missing_result"


@pytest.mark.anyio
async def test_c2_unresolved_link_blocked() -> None:
    db = _db_with_links(
        [
            _link(
                module_owner="sales",
                result_type=RESULT_SALES_INQUIRY,
                status="unresolved",
                ledger_id=None,
            )
        ]
    )
    with pytest.raises(CommunicationContextResolveError) as ei:
        await resolve_communication_context(db, tenant_id="t1", thread_id="th-1")
    assert ei.value.details.get("reason") == "damaged_or_archived_link"
