"""Unit tests for ADR-033 lead lifecycle email policy resolver."""

from __future__ import annotations

from backend.app.services.lead_lifecycle_email_policy import (
    PURPOSE_GDPR_NOTICE,
    PURPOSE_SUBMISSION_ACK,
    SAFE_DEFAULT_COMPANY_POLICY,
    decide_from_layers,
    tenant_preset_to_company_policy,
)


def test_decide_company_ops_enabled_with_template_sends() -> None:
    company = {
        "ops_enabled": True,
        "application_received": {"enabled": True, "template_ref": "tpl-1"},
        "rejection": {"enabled": False, "template_ref": None},
        "moving_forward": {"enabled": False, "template_ref": None},
    }
    d = decide_from_layers(
        purpose=PURPOSE_SUBMISSION_ACK,
        vacancy_ov={},
        company=company,
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id="c1",
    )
    assert d.send is True
    assert d.template_ref == "tpl-1"
    assert d.source_layer == "company"
    assert d.block_code is None


def test_decide_enabled_without_template_fail_closed() -> None:
    company = {
        "ops_enabled": True,
        "application_received": {"enabled": True, "template_ref": None},
    }
    d = decide_from_layers(
        purpose=PURPOSE_SUBMISSION_ACK,
        vacancy_ov={},
        company=company,
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id="c1",
    )
    assert d.send is False
    assert d.enabled is True
    assert d.block_code == "policy_template_missing"


def test_decide_vacancy_override_wins_template() -> None:
    company = {
        "ops_enabled": True,
        "application_received": {"enabled": True, "template_ref": "company-tpl"},
    }
    vacancy = {"application_received": {"enabled": True, "template_ref": "vac-tpl"}}
    d = decide_from_layers(
        purpose=PURPOSE_SUBMISSION_ACK,
        vacancy_ov=vacancy,
        company=company,
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id="c1",
    )
    assert d.send is True
    assert d.template_ref == "vac-tpl"
    assert d.source_layer == "vacancy"


def test_decide_rodo_manual_no_auto_send_even_with_template() -> None:
    company = {
        "rodo_send_mode": "manual",
        "rodo_template_ref": "rodo-tpl",
    }
    d = decide_from_layers(
        purpose=PURPOSE_GDPR_NOTICE,
        vacancy_ov={},
        company=company,
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id="c1",
    )
    assert d.send is False
    assert d.send_mode == "manual"
    assert d.template_ref == "rodo-tpl"
    assert d.block_code is None


def test_decide_rodo_auto_without_template_blocks() -> None:
    company = {
        "rodo_send_mode": "auto_on_first_action",
        "rodo_template_ref": None,
    }
    d = decide_from_layers(
        purpose=PURPOSE_GDPR_NOTICE,
        vacancy_ov={},
        company=company,
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id="c1",
    )
    assert d.send is False
    assert d.block_code == "policy_template_missing"


def test_decide_missing_company_blocks() -> None:
    d = decide_from_layers(
        purpose=PURPOSE_SUBMISSION_ACK,
        vacancy_ov={},
        company={},
        tenant=SAFE_DEFAULT_COMPANY_POLICY,
        company_id=None,
    )
    assert d.send is False
    assert d.block_code == "missing_company"


def test_tenant_preset_mapping_from_legacy_json() -> None:
    preset = tenant_preset_to_company_policy(
        {
            "lead_rodo_v1": {
                "send_mode": "auto_on_lead_created",
                "message_template_id": "m1",
                "channels": ["email"],
            },
            "lead_communication_v1": {
                "enabled": True,
                "send_application_received": True,
                "application_received_template_id": "ar1",
                "send_rejection_notice": False,
                "send_moving_forward_notice": True,
                "moving_forward_template_id": "mf1",
            },
        }
    )
    assert preset["rodo_send_mode"] == "auto_on_lead_created"
    assert preset["rodo_template_ref"] == "m1"
    assert preset["ops_enabled"] is True
    assert preset["application_received"]["template_ref"] == "ar1"
    assert preset["moving_forward"]["enabled"] is True
