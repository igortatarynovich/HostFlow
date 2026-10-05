"""A missing work permit does not block ZUS registration."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.workforce_work_eligibility_rules import evaluate_zus_registration_gate


def _profile(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = dict(
        eligibility_status="not_evaluated",
        position_category="driver",
        citizenship="UA",
        requires_work_permit=True,
        work_permit_received_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_third_country_driver_without_a_permit_is_not_blocked() -> None:
    mode, blocked_by = evaluate_zus_registration_gate(_profile(), emp=None, payments=[])
    assert mode == "allow"
    assert blocked_by == []


def test_pending_permit_status_does_not_block_zus() -> None:
    mode, blocked_by = evaluate_zus_registration_gate(
        _profile(eligibility_status="work_permit_pending"),
        emp=None,
        payments=[],
    )
    assert mode == "allow"
    assert "work_permit" not in blocked_by


def test_missing_legal_stay_still_blocks_zus() -> None:
    mode, blocked_by = evaluate_zus_registration_gate(
        _profile(eligibility_status="missing_legal_stay"),
        emp=None,
        payments=[],
    )
    assert mode == "blocked"
    assert blocked_by == ["legal_stay"]
