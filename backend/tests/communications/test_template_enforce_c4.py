"""C4 — Template metadata enforcement."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from backend.app.communications.context_resolver import CommunicationContext
from backend.app.communications.template_enforce import (
    REASON_CHANNEL_UNSUPPORTED,
    REASON_DOMAIN_MISMATCH,
    REASON_LIFECYCLE_INACTIVE,
    REASON_MISSING_TEMPLATE,
    REASON_MODULE_MISMATCH,
    REASON_PURPOSE_MISMATCH,
    enforce_template_metadata,
)
from backend.app.communications.template_metadata import (
    LIFECYCLE_ARCHIVED,
    LIFECYCLE_DISABLED,
    build_template_metadata,
)


COMMS = Path(__file__).resolve().parents[2] / "app" / "communications"


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


def _recruitment_ctx() -> CommunicationContext:
    return CommunicationContext(
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


def _sales_questionnaire_template(**overrides):  # noqa: ANN003
    base = dict(
        template_id="tpl_sales_questionnaire_v1",
        template_version="1",
        module_owner="sales",
        communication_domain="sales",
        communication_purpose="qualification_questionnaire_request",
        supported_channels=["email"],
        supported_locales=["pl", "en"],
        lifecycle_status="active",
        policy_version="sales.communication_policy.v1",
    )
    base.update(overrides)
    return build_template_metadata(**base)


def _recruitment_ack_template(**overrides):  # noqa: ANN003
    base = dict(
        template_id="tpl_recruitment_ack_v1",
        template_version="1",
        module_owner="recruitment",
        communication_domain="recruitment",
        communication_purpose="submission_acknowledgement",
        supported_channels=["email"],
        supported_locales=["pl", "en"],
        lifecycle_status="active",
        policy_version="recruitment.communication_policy.v1",
    )
    base.update(overrides)
    return build_template_metadata(**base)


def test_c4_shared_does_not_import_destination_orm() -> None:
    forbidden = (
        "backend.app.models.sales_inquiry",
        "backend.app.models.recruitment_application",
        "backend.app.modules.sales.services",
        "backend.app.modules.recruitment.services",
    )
    for path in (COMMS / "template_enforce.py", COMMS / "template_metadata.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text


def test_c4_does_not_select_or_fallback_templates() -> None:
    text = (COMMS / "template_enforce.py").read_text(encoding="utf-8")
    assert "Does NOT" in text
    assert "fallback" in text  # only as deny detail / prohibition


def test_c4_sales_inquiry_allows_matching_sales_template() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
        locale="pl",
    )
    assert decision.allowed is True
    assert decision.reason_code == "allowed"


def test_c4_blocks_recruitment_template_for_sales_inquiry() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_recruitment_ack_template(),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_MODULE_MISMATCH
    assert decision.details.get("fallback") is None


def test_c4_blocks_candidate_acknowledgement_for_sales() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_recruitment_ack_template(),
        channel="email",
        communication_purpose="submission_acknowledgement",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_MODULE_MISMATCH


def test_c4_blocks_sales_template_for_application() -> None:
    decision = enforce_template_metadata(
        context=_recruitment_ctx(),
        template=_sales_questionnaire_template(),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_MODULE_MISMATCH


def test_c4_blocks_purpose_mismatch() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(),
        channel="email",
        communication_purpose="meeting_invitation",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_PURPOSE_MISMATCH
    assert decision.details.get("fallback") is None


def test_c4_blocks_archived_template() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(lifecycle_status=LIFECYCLE_ARCHIVED),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_LIFECYCLE_INACTIVE


def test_c4_blocks_disabled_template() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(lifecycle_status=LIFECYCLE_DISABLED),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_LIFECYCLE_INACTIVE


def test_c4_blocks_unknown_missing_template() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=None,
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_MISSING_TEMPLATE


def test_c4_blocks_other_module_owner() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(module_owner="recruitment"),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code in {REASON_MODULE_MISMATCH, REASON_DOMAIN_MISMATCH}


def test_c4_blocks_incompatible_channel() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(supported_channels=["sms"]),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
    )
    assert decision.allowed is False
    assert decision.reason_code == REASON_CHANNEL_UNSUPPORTED
    assert decision.details.get("fallback") is None


def test_c4_no_locale_fallback() -> None:
    decision = enforce_template_metadata(
        context=_sales_ctx(),
        template=_sales_questionnaire_template(supported_locales=["pl"]),
        channel="email",
        communication_purpose="qualification_questionnaire_request",
        locale="de",
    )
    assert decision.allowed is False
    assert decision.details.get("fallback") is None
