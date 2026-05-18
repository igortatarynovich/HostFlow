"""Trusted employment identity read adapter (PR6)."""

from __future__ import annotations

import pytest

from backend.app.services.employment_identity_projection import (
    PROJECTION_STATUS_COMPLETE,
    PROJECTION_STATUS_CONFLICTED,
    PROJECTION_STATUS_INCOMPLETE,
    PROJECTION_STATUS_STALE,
)
from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_CLIENT_FORM,
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_EXPORT,
    CONSUMER_HR_REVIEW_DISPLAY,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_ZUS_PREPARATION,
    TrustedIdentityAccessError,
    evaluate_consumer_access,
)


@pytest.mark.parametrize(
    "consumer,status,expected_allowed,expected_code",
    [
        (CONSUMER_CONTRACT_GENERATION, PROJECTION_STATUS_COMPLETE, True, None),
        (CONSUMER_CONTRACT_GENERATION, PROJECTION_STATUS_STALE, False, "TRUSTED_IDENTITY_STALE"),
        (CONSUMER_CONTRACT_GENERATION, PROJECTION_STATUS_INCOMPLETE, False, "TRUSTED_IDENTITY_INCOMPLETE"),
        (CONSUMER_CONTRACT_GENERATION, PROJECTION_STATUS_CONFLICTED, False, "TRUSTED_IDENTITY_CONFLICTED"),
        (CONSUMER_ZUS_PREPARATION, PROJECTION_STATUS_STALE, False, "TRUSTED_IDENTITY_STALE"),
        (CONSUMER_PAYROLL_PREP, PROJECTION_STATUS_INCOMPLETE, False, "TRUSTED_IDENTITY_INCOMPLETE"),
        (CONSUMER_EXPORT, PROJECTION_STATUS_STALE, True, None),
        (CONSUMER_CLIENT_FORM, PROJECTION_STATUS_STALE, True, None),
        (CONSUMER_EXPORT, PROJECTION_STATUS_INCOMPLETE, False, "TRUSTED_IDENTITY_INCOMPLETE"),
        (CONSUMER_HR_REVIEW_DISPLAY, PROJECTION_STATUS_INCOMPLETE, True, None),
        (CONSUMER_HR_REVIEW_DISPLAY, PROJECTION_STATUS_CONFLICTED, True, None),
        (CONSUMER_HR_REVIEW_DISPLAY, PROJECTION_STATUS_STALE, True, None),
    ],
)
def test_evaluate_consumer_access_matrix(
    consumer: str, status: str, expected_allowed: bool, expected_code: str | None
) -> None:
    allowed, code = evaluate_consumer_access(consumer, status)
    assert allowed is expected_allowed
    assert code == expected_code


def test_invalid_consumer() -> None:
    with pytest.raises(ValueError, match="INVALID_IDENTITY_CONSUMER"):
        evaluate_consumer_access("unknown_consumer", PROJECTION_STATUS_COMPLETE)


def test_trusted_identity_access_error_fields() -> None:
    err = TrustedIdentityAccessError(
        code="TRUSTED_IDENTITY_STALE",
        consumer=CONSUMER_CONTRACT_GENERATION,
        projection_status=PROJECTION_STATUS_STALE,
        review_id="r1",
        message="blocked",
    )
    assert err.code == "TRUSTED_IDENTITY_STALE"
    assert err.review_id == "r1"


@pytest.mark.asyncio
async def test_get_trusted_for_employee_skips_review_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent ensure → journey → permit → ensure recursion during trusted identity reads."""
    from backend.app.services import employment_identity_read_adapter as adapter

    calls: list[bool] = []

    async def _fake_ensure(db, tenant_id, employee, *, sync_from_sources: bool = True):
        calls.append(sync_from_sources)
        review = type("R", (), {"id": "review-1"})()
        return review

    async def _fake_get_trusted(db, **kwargs):
        return type(
            "T",
            (),
            {
                "tenant_id": "t1",
                "review_id": "review-1",
                "employee_id": "e1",
                "handoff_id": None,
                "consumer": kwargs["consumer"],
                "projection": {},
                "attributes": {},
                "projection_status": PROJECTION_STATUS_COMPLETE,
                "access_allowed": True,
                "denial_code": None,
            },
        )()

    async def _fake_get_employee(db, tenant_id, employee_id):
        return type("E", (), {"id": employee_id})()

    monkeypatch.setattr(
        "backend.app.services.workforce_hr_review.ensure_hr_review_for_employee",
        _fake_ensure,
    )
    monkeypatch.setattr(adapter, "get_trusted_employment_identity", _fake_get_trusted)
    monkeypatch.setattr(
        "backend.app.services.workforce_employees.get_employee",
        _fake_get_employee,
    )

    await adapter.get_trusted_employment_identity_for_employee(
        None,
        tenant_id="t1",
        employee_id="e1",
        consumer=CONSUMER_ZUS_PREPARATION,
    )
    assert calls == [False]
