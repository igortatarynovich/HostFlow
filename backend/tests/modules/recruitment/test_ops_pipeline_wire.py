"""Recruitment ops emails via Communication Pipeline (ADR-031 PR-4)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.recruitment.communication.compliance_pipeline import (
    PURPOSE_SUBMISSION_ACK,
    purpose_for_ops_event,
)
from backend.app.modules.recruitment.communication.compliance_pipeline import (
    RecruitmentCompliancePipelineBinding,
)
from backend.app.communications.template_metadata import build_template_metadata
from backend.app.modules.recruitment.communication.policy_adapter import POLICY_VERSION


def test_recruitment_ops_purpose_mapping() -> None:
    assert purpose_for_ops_event("application_received") == PURPOSE_SUBMISSION_ACK
    assert purpose_for_ops_event("lead_rejected") == "intake_rejection_notice"
    assert purpose_for_ops_event("moving_forward") == "moving_forward_notice"


@pytest.mark.asyncio
async def test_recruitment_ops_auto_bind_then_pipeline_send() -> None:
    from backend.app.services.lead_communications import maybe_send_lead_communication

    lead = SimpleNamespace(
        id="lead-1",
        own_company_id="oc-1",
        vacancy_id="vac-1",
        normalized={
            "email": "ops@b.test",
            "first_name": "Ops",
            "intake_result_link_v1": {
                "result_type": "application",
                "application_id": "app-1",
            },
        },
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    template = build_template_metadata(
        template_id="tpl_test",
        template_version="1",
        module_owner="recruitment",
        communication_domain="recruitment",
        communication_purpose=PURPOSE_SUBMISSION_ACK,
        supported_channels=["email"],
        supported_locales=["pl"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )
    binding = RecruitmentCompliancePipelineBinding(
        thread_id="thread-1",
        application_id="app-1",
        candidate_id="cand-1",
        communication_purpose=PURPOSE_SUBMISSION_ACK,
        template=template,
        locale="pl",
    )
    auth = MagicMock()
    auth.allowed = True
    auth.reason_code = None
    auth.to_dict = MagicMock(return_value={"allowed": True})

    cfg = SimpleNamespace(
        enabled=True,
        send_application_received=True,
        send_rejection_notice=True,
        send_moving_forward_notice=True,
        application_received_subject=None,
        application_received_body=None,
        rejection_notice_subject=None,
        rejection_notice_body=None,
        moving_forward_subject=None,
        moving_forward_body=None,
        application_received_template_id=None,
        rejection_notice_template_id=None,
        moving_forward_template_id=None,
    )

    with (
        patch(
            "backend.app.services.lead_communications.get_lead_communication_settings",
            new_callable=AsyncMock,
            return_value=cfg,
        ),
        patch(
            "backend.app.modules.sales.communication.compliance_pipeline"
            ".resolve_lead_uses_sales_compliance_pipeline",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "backend.app.modules.recruitment.communication.compliance_pipeline"
            ".resolve_lead_uses_recruitment_compliance_pipeline",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.app.modules.recruitment.services.compliance_outbound_ensure"
            ".maybe_ensure_compliance_outbound_for_recruitment_lead",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.app.modules.recruitment.communication.compliance_pipeline"
            ".ensure_recruitment_compliance_pipeline_binding",
            new_callable=AsyncMock,
            return_value=binding,
        ) as ensure,
        patch(
            "backend.app.communications.send_pipeline.authorize_outbound_communication",
            new_callable=AsyncMock,
            return_value=auth,
        ),
        patch(
            "backend.app.services.lead_communications.resolve_lead_email_message",
            new_callable=AsyncMock,
            return_value=SimpleNamespace(subject="Got it", body="Thanks"),
        ),
        patch(
            "backend.app.communications.prepare_send.prepare_and_send_communication",
            new_callable=AsyncMock,
        ) as prep,
        patch(
            "backend.app.services.lead_communications.log_audit_event",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.app.services.lead_communications.send_email_for_tenant",
            new_callable=AsyncMock,
        ) as smtp,
        patch(
            "backend.app.services.lead_communications.flag_modified",
        ),
    ):
        sent = await maybe_send_lead_communication(
            db,
            tenant_id="t1",
            lead=lead,
            event_type="application_received",
        )

    assert sent is True
    ensure.assert_awaited_once()
    prep.assert_awaited_once()
    smtp.assert_not_called()
