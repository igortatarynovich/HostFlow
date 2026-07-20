"""manual_thread_reply purpose + template metadata (Sales / Recruitment)."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.communications.manual_thread_reply import (
    PURPOSE_MANUAL_THREAD_REPLY,
    manual_thread_reply_binding,
)
from backend.app.communications.context_resolver import CommunicationContext
from backend.app.communications.policy_gate import (
    evaluate_policy_for_context,
    reset_policy_adapters_for_tests,
)
from backend.app.modules.recruitment.communication.manual_thread_reply import (
    recruitment_manual_thread_reply_template_metadata,
)
from backend.app.modules.sales.communication.manual_thread_reply import (
    sales_manual_thread_reply_template_metadata,
)


def setup_function() -> None:
    reset_policy_adapters_for_tests(None)


def teardown_function() -> None:
    reset_policy_adapters_for_tests(None)


def test_sales_manual_thread_reply_metadata() -> None:
    meta = sales_manual_thread_reply_template_metadata()
    assert meta.module_owner == "sales"
    assert meta.communication_purpose == PURPOSE_MANUAL_THREAD_REPLY
    assert "email" in meta.supported_channels
    assert meta.lifecycle_status == "active"


def test_recruitment_manual_thread_reply_metadata() -> None:
    meta = recruitment_manual_thread_reply_template_metadata()
    assert meta.module_owner == "recruitment"
    assert meta.communication_purpose == PURPOSE_MANUAL_THREAD_REPLY
    assert "email" in meta.supported_channels


def test_binding_resolves_by_module_owner() -> None:
    sales = manual_thread_reply_binding(module_owner="sales", channel="email")
    assert sales is not None
    assert sales.communication_purpose == PURPOSE_MANUAL_THREAD_REPLY
    assert sales.template.module_owner == "sales"

    rec = manual_thread_reply_binding(module_owner="recruitment", channel="email")
    assert rec is not None
    assert rec.template.module_owner == "recruitment"

    assert manual_thread_reply_binding(module_owner="unknown", channel="email") is None
    assert manual_thread_reply_binding(module_owner="sales", channel="carrier_pigeon") is None


def test_sales_policy_allows_manual_thread_reply() -> None:
    ctx = CommunicationContext(
        thread_id="th-1",
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
        communication_domain="sales",
        resolution_status="resolved",
        result_link_id="link-1",
        provenance_ledger_id="lg-1",
        resolved_at=datetime.now(timezone.utc),
        resolver_version="communication.context_resolver.v1",
    )
    decision = evaluate_policy_for_context(
        ctx,
        communication_purpose=PURPOSE_MANUAL_THREAD_REPLY,
        channel="email",
    )
    assert decision.allowed is True
    assert decision.policy_owner == "sales"


def test_recruitment_policy_allows_manual_thread_reply() -> None:
    ctx = CommunicationContext(
        thread_id="th-2",
        module_owner="recruitment",
        result_type="application",
        result_id="app-1",
        communication_domain="recruitment",
        resolution_status="resolved",
        result_link_id="link-2",
        provenance_ledger_id=None,
        resolved_at=datetime.now(timezone.utc),
        resolver_version="communication.context_resolver.v1",
    )
    decision = evaluate_policy_for_context(
        ctx,
        communication_purpose=PURPOSE_MANUAL_THREAD_REPLY,
        channel="email",
    )
    assert decision.allowed is True
    assert decision.policy_owner == "recruitment"
