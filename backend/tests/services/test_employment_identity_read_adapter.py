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
