"""C3 — Module-owned Communication Policy Ports."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.communications.context_resolver import CommunicationContext
from backend.app.communications.policy_contract import (
    REASON_NO_ADAPTER,
    REASON_UNKNOWN_CHANNEL,
    REASON_UNKNOWN_PURPOSE,
    CommunicationPolicyRequest,
)
from backend.app.communications.policy_gate import (
    evaluate_communication_policy,
    evaluate_policy_for_context,
    reset_policy_adapters_for_tests,
)


ROOT = Path(__file__).resolve().parents[2] / "app"
COMMS = ROOT / "communications"
RECRUITMENT = ROOT / "modules" / "recruitment"
SALES = ROOT / "modules" / "sales"


@pytest.fixture(autouse=True)
def _reset_adapters() -> None:
    reset_policy_adapters_for_tests(None)
    yield
    reset_policy_adapters_for_tests(None)


def _sales_ctx() -> CommunicationContext:
    return CommunicationContext(
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


def test_c3_shared_layer_has_no_hardcoded_module_purpose_lists() -> None:
    """Purpose allow-lists must live in module adapters, not shared gate/contract."""
    forbidden_purpose_names = (
        "qualification_questionnaire_request",
        "interview_invitation",
        "document_request",
        "proposal_follow_up",
        "additional_information_request",
        "meeting_invitation",
    )
    for name in ("policy_gate.py", "policy_contract.py", "context_resolver.py"):
        text = (COMMS / name).read_text(encoding="utf-8")
        for purpose in forbidden_purpose_names:
            assert purpose not in text, f"{name} hardcodes purpose {purpose}"


def test_c3_modules_do_not_import_each_others_policy() -> None:
    for path in (RECRUITMENT / "communication").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "modules.sales" not in text
        assert "SalesCommunicationPolicy" not in text
    for path in (SALES / "communication").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "modules.recruitment" not in text
        assert "RecruitmentCommunicationPolicy" not in text


def test_c3_shared_must_not_import_destination_orm() -> None:
    forbidden = (
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
    )
    for path in COMMS.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{path}: {pattern}"


def test_c3_sales_qualification_questionnaire_allowed() -> None:
    decision = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="qualification_questionnaire_request",
        channel="email",
        locale="pl",
    )
    assert decision.allowed is True
    assert decision.policy_owner == "sales"
    assert decision.reason_code == "allowed"
    assert decision.decision_id


def test_c3_sales_rejects_recruitment_acknowledgement_purpose() -> None:
    """Critical acceptance: Sales context never allows recruitment acknowledgement."""
    decision = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="recruitment_submission_acknowledgement",
        channel="email",
        locale="pl",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_UNKNOWN_PURPOSE
    assert decision.policy_owner == "sales"
    # Independent of form/locale/UI noise — same deny.
    again = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="recruitment_submission_acknowledgement",
        channel="email",
        locale="en",
    )
    assert again.allowed is False
    assert again.reason_code == REASON_UNKNOWN_PURPOSE


def test_c3_sales_rejects_recruitment_only_purpose_interview() -> None:
    decision = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="interview_invitation",
        channel="email",
    )
    assert decision.allowed is False


def test_c3_recruitment_allows_submission_acknowledgement() -> None:
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
        communication_purpose="submission_acknowledgement",
        channel="email",
    )
    assert decision.allowed is True
    assert decision.policy_owner == "recruitment"


def test_c3_unknown_channel_denied() -> None:
    decision = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="qualification_questionnaire_request",
        channel="carrier_pigeon",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_UNKNOWN_CHANNEL


def test_c3_missing_adapter_denied_no_recruitment_fallback() -> None:
    reset_policy_adapters_for_tests({})  # empty registry
    req = CommunicationPolicyRequest(
        module_owner="sales",
        result_type="sales_inquiry",
        result_id="si-1",
        communication_domain="sales",
        communication_purpose="qualification_questionnaire_request",
        channel="email",
    )
    decision = evaluate_communication_policy(req)
    assert decision.allowed is False
    assert decision.reason_code == REASON_NO_ADAPTER
    assert decision.details.get("fallback") is None


def test_c3_deterministic_for_same_input() -> None:
    a = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="qualification_questionnaire_request",
        channel="email",
        locale="pl",
    )
    b = evaluate_policy_for_context(
        _sales_ctx(),
        communication_purpose="qualification_questionnaire_request",
        channel="email",
        locale="pl",
    )
    assert a.allowed == b.allowed
    assert a.reason_code == b.reason_code
    assert a.policy_owner == b.policy_owner
    assert a.policy_version == b.policy_version
    # decision_id is unique per call (audit), outcome fields match
    assert a.decision_id != b.decision_id
