from __future__ import annotations

from backend.app.services import portal_candidate_usage


def test_resolve_plan_code_for_portal_cap_keeps_trial_status() -> None:
    plan = portal_candidate_usage.resolve_plan_code_for_portal_cap(
        {"status": "trial", "plan_code": "pro"},
        None,
    )
    assert plan == "trial"


def test_monthly_cap_for_trial_plan_code() -> None:
    assert portal_candidate_usage.monthly_cap_for_plan_code("trial") == 2
