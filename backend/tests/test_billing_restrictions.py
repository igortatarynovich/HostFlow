"""Unit tests for billing_restrictions (§2.18 past_due + expired trial gates)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

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


def test_expired_trial_license_blocks() -> None:
    t = _tenant({"billing": {"subscription": {"status": ""}}})
    lic = _license(plan="trial", expires_at=date.today() - timedelta(days=1))
    assert billing_restrictions.billing_write_block_reason(t, lic) == "trial_expired"
    assert billing_restrictions.tenant_billing_blocks_new_leads(t, lic)


def test_trial_license_still_valid_no_block() -> None:
    t = _tenant({"billing": {"subscription": {"status": ""}}})
    lic = _license(plan="trial", expires_at=date.today())
    assert billing_restrictions.billing_write_block_reason(t, lic) is None


def test_stripe_trial_end_in_past_blocks() -> None:
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
    assert billing_restrictions.billing_write_block_reason(t) == "trial_expired"
