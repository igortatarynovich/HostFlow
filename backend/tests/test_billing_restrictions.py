"""Unit tests for billing_restrictions (§2.18 past_due + expired trial gates)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.services import billing_restrictions


def _tenant(settings: dict | None) -> SimpleNamespace:
    return SimpleNamespace(settings=settings)


def _license(*, plan: str = "trial", expires_at: date | None = None) -> SimpleNamespace:
    return SimpleNamespace(plan=plan, expires_at=expires_at)


def test_past_due_blocks_leads_and_outbound() -> None:
    t = _tenant({"billing": {"subscription": {"status": "past_due"}}})
    assert billing_restrictions.tenant_subscription_status(t) == "past_due"
    assert billing_restrictions.tenant_billing_blocks_new_leads(t)
    assert billing_restrictions.tenant_billing_blocks_outbound_comms(t)
    assert billing_restrictions.billing_write_block_reason(t) == "past_due"


def test_active_does_not_block() -> None:
    t = _tenant({"billing": {"subscription": {"status": "active"}}})
    assert not billing_restrictions.tenant_billing_blocks_new_leads(t)
    assert not billing_restrictions.tenant_billing_blocks_outbound_comms(t)
    expired_lic = _license(expires_at=date(2020, 1, 1))
    assert not billing_restrictions.tenant_billing_blocks_new_leads(t, expired_lic)


def test_none_tenant_safe() -> None:
    assert not billing_restrictions.tenant_billing_blocks_new_leads(None)
    assert not billing_restrictions.tenant_billing_blocks_outbound_comms(None)


def test_status_case_insensitive() -> None:
    t = _tenant({"billing": {"subscription": {"status": "PAST_DUE"}}})
    assert billing_restrictions.tenant_billing_blocks_new_leads(t)


def test_expired_trial_license_blocks_after_grace() -> None:
    t = _tenant({"billing": {"subscription": {"status": ""}}})
    lic = _license(plan="trial", expires_at=date.today() - timedelta(days=10))
    assert billing_restrictions.billing_write_block_reason(t, lic) == "trial_expired"
    assert billing_restrictions.tenant_billing_blocks_new_leads(t, lic)


def test_expired_trial_license_in_grace_no_block() -> None:
    t = _tenant({"billing": {"subscription": {"status": ""}}})
    lic = _license(plan="trial", expires_at=date.today() - timedelta(days=1))
    assert billing_restrictions.billing_write_block_reason(t, lic) is None
    assert not billing_restrictions.tenant_billing_blocks_new_leads(t, lic)


def test_trial_license_still_valid_no_block() -> None:
    t = _tenant({"billing": {"subscription": {"status": ""}}})
    lic = _license(plan="trial", expires_at=date.today())
    assert billing_restrictions.billing_write_block_reason(t, lic) is None


def test_stripe_trial_end_in_past_blocks_after_grace() -> None:
    old = (date.today() - timedelta(days=10)).isoformat()
    t = _tenant(
        {
            "billing": {
                "subscription": {
                    "status": "trial",
                    "trial_ends_at": f"{old}T12:00:00+00:00",
                }
            }
        }
    )
    assert billing_restrictions.billing_write_block_reason(t) == "trial_expired"


def test_stripe_trial_end_in_grace_no_block() -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    t = _tenant(
        {
            "billing": {
                "subscription": {
                    "status": "trial",
                    "trial_ends_at": f"{yesterday}T12:00:00+00:00",
                }
            }
        }
    )
    assert billing_restrictions.billing_write_block_reason(t) is None


def test_ensure_billing_allows_side_effects_raises_past_due() -> None:
    t = _tenant({"billing": {"subscription": {"status": "past_due"}}})
    with pytest.raises(HTTPException) as ei:
        billing_restrictions.ensure_billing_allows_side_effects(t, None)
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "billing_past_due"


def test_ensure_billing_allows_side_effects_ok_when_active() -> None:
    t = _tenant({"billing": {"subscription": {"status": "active"}}})
    billing_restrictions.ensure_billing_allows_side_effects(t, None)


def test_ensure_billing_allows_action_past_due_allows_task_complete() -> None:
    t = _tenant({"billing": {"subscription": {"status": "past_due"}}})
    billing_restrictions.ensure_billing_allows_action(t, None, action="task_complete")


def test_ensure_billing_allows_action_past_due_blocks_generic_side_effects() -> None:
    t = _tenant({"billing": {"subscription": {"status": "past_due"}}})
    with pytest.raises(HTTPException) as ei:
        billing_restrictions.ensure_billing_allows_action(t, None, action="side_effect_write")
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "billing_past_due"
    assert ei.value.detail["action"] == "side_effect_write"


def test_trialing_status_respects_trial_ends_at() -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    t = _tenant(
        {
            "billing": {
                "subscription": {
                    "status": "trialing",
                    "trial_ends_at": f"{tomorrow}T12:00:00+00:00",
                }
            }
        }
    )
    assert billing_restrictions.billing_write_block_reason(t) is None


def test_compute_gate_snapshot_trial_active() -> None:
    ends = datetime.now(UTC) + timedelta(days=5)
    t = _tenant(
        {"billing": {"subscription": {"status": "trial", "trial_ends_at": ends.replace(microsecond=0).isoformat()}}}
    )
    snap = billing_restrictions.compute_billing_gate_snapshot(t, None)
    assert snap.trial_active
    assert not snap.trial_grace_active
    assert not snap.side_effects_blocked


def test_compute_gate_snapshot_grace_window() -> None:
    ends = datetime.now(UTC) - timedelta(hours=6)
    t = _tenant(
        {"billing": {"subscription": {"status": "trial", "trial_ends_at": ends.replace(microsecond=0).isoformat()}}}
    )
    snap = billing_restrictions.compute_billing_gate_snapshot(t, None)
    assert snap.trial_grace_active
    assert not snap.trial_active
    assert not snap.side_effects_blocked
    assert snap.side_effect_grace_hours_remaining is not None


def test_compute_gate_snapshot_blocked_past_due() -> None:
    t = _tenant({"billing": {"subscription": {"status": "past_due"}}})
    snap = billing_restrictions.compute_billing_gate_snapshot(t, None)
    assert snap.side_effects_blocked
    assert snap.block_reason == "past_due"
