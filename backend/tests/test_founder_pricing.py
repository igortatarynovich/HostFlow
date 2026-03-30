"""founder_pricing — Stripe-inactive streak revoke (§2.16)."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.services import founder_pricing


@pytest.mark.parametrize(
    ("plan", "expected"),
    [
        (None, None),
        ("", None),
        ("starter", None),
        ("solo", None),
        ("trial", None),
        ("team", "team"),
        ("pro", "pro"),
        ("agency_basic", "team"),
        ("employer_basic", "team"),
        ("services_basic", "team"),
        ("agency_premium", "pro"),
        ("business", "pro"),
        ("enterprise", "pro"),
        ("Agency_Basic", "team"),
        ("UNKNOWN_PLAN_X", None),
    ],
)
def test_license_plan_for_founder_eligibility(plan: str | None, expected: str | None) -> None:
    assert founder_pricing.license_plan_for_founder_eligibility(plan) == expected


def _base_settings() -> dict:
    return {
        "billing": {
            "founder_pricing_v1": {
                "enrolled": True,
                "revoked": False,
                "inactive_since": None,
            }
        }
    }


def test_active_clears_inactive_since() -> None:
    now = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)
    s = _base_settings()
    s["billing"]["founder_pricing_v1"]["inactive_since"] = "2026-01-01T00:00:00+00:00"
    out = founder_pricing.apply_stripe_status_to_settings(s, "active", now_utc=now)
    assert out["billing"]["founder_pricing_v1"]["inactive_since"] is None
    assert not out["billing"]["founder_pricing_v1"].get("revoked")


def test_inactive_starts_timer() -> None:
    now = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)
    out = founder_pricing.apply_stripe_status_to_settings(_base_settings(), "past_due", now_utc=now)
    assert out["billing"]["founder_pricing_v1"]["inactive_since"] == now.isoformat()


def test_inactive_over_14_days_revokes() -> None:
    started = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    now = started + timedelta(days=15)
    s = _base_settings()
    s["billing"]["founder_pricing_v1"]["inactive_since"] = started.isoformat()
    out = founder_pricing.apply_stripe_status_to_settings(s, "canceled", now_utc=now)
    assert out["billing"]["founder_pricing_v1"]["revoked"] is True
    assert out["billing"]["founder_pricing_v1"].get("revoked_at")


def test_trial_counts_as_active() -> None:
    now = datetime(2026, 1, 5, tzinfo=UTC)
    s = _base_settings()
    s["billing"]["founder_pricing_v1"]["inactive_since"] = "2026-01-01T00:00:00+00:00"
    out = founder_pricing.apply_stripe_status_to_settings(s, "trial", now_utc=now)
    assert out["billing"]["founder_pricing_v1"]["inactive_since"] is None


def test_noop_without_enrollment() -> None:
    now = datetime(2026, 1, 5, tzinfo=UTC)
    s = {"billing": {}}
    out = founder_pricing.apply_stripe_status_to_settings(s, "canceled", now_utc=now)
    assert out == s
