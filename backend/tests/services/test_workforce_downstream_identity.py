"""Downstream trusted identity wiring (PR7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.employment_identity_projection import (
    PROJECTION_STATUS_COMPLETE,
    PROJECTION_STATUS_CONFLICTED,
    PROJECTION_STATUS_INCOMPLETE,
)
from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_CONTRACT_GENERATION,
    CONSUMER_PAYROLL_PREP,
    CONSUMER_ZUS_PREPARATION,
    TrustedEmploymentIdentityRead,
    TrustedIdentityAccessError,
)
from backend.app.services.workforce_downstream_identity import (
    DownstreamIdentityBlockedError,
    bindings_from_trusted_read,
    evaluate_contract_merge_identity,
    evaluate_payroll_preparation,
    evaluate_zus_preparation,
    identity_attributes_to_bindings,
)


def test_identity_attributes_to_bindings_splits_legal_name() -> None:
    b = identity_attributes_to_bindings(
        {"legal_name": "Jan Kowalski", "citizenship": "PL", "pesel": "90010112345"}
    )
    assert b["legal_first_name"] == "Jan"
    assert b["legal_last_name"] == "Kowalski"
    assert b["citizenship"] == "PL"


def test_bindings_from_trusted_read() -> None:
    trusted = TrustedEmploymentIdentityRead(
        tenant_id="t1",
        review_id="r1",
        employee_id="e1",
        handoff_id=None,
        consumer=CONSUMER_CONTRACT_GENERATION,
        projection={"status": PROJECTION_STATUS_COMPLETE},
        attributes={"legal_name": "A B", "citizenship": "UA"},
        projection_status=PROJECTION_STATUS_COMPLETE,
        access_allowed=True,
    )
    assert bindings_from_trusted_read(trusted)["legal_name"] == "A B"


@pytest.mark.asyncio
async def test_evaluate_zus_preparation_blocked_on_incomplete() -> None:
    with patch(
        "backend.app.services.workforce_downstream_identity.get_trusted_employment_identity_for_employee",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = TrustedIdentityAccessError(
            code="TRUSTED_IDENTITY_INCOMPLETE",
            consumer=CONSUMER_ZUS_PREPARATION,
            projection_status=PROJECTION_STATUS_INCOMPLETE,
            review_id="r1",
            message="blocked",
        )
        result = await evaluate_zus_preparation(AsyncMock(), "t1", "e1")
    assert result.blocked is True
    assert result.block_code == "TRUSTED_IDENTITY_INCOMPLETE"
    assert result.ready is False


@pytest.mark.asyncio
async def test_evaluate_contract_merge_complete_bindings() -> None:
    trusted = TrustedEmploymentIdentityRead(
        tenant_id="t1",
        review_id="r1",
        employee_id="e1",
        handoff_id=None,
        consumer=CONSUMER_CONTRACT_GENERATION,
        projection={"status": PROJECTION_STATUS_COMPLETE},
        attributes={"legal_name": "Jan Kowalski", "citizenship": "PL", "pesel": "123"},
        projection_status=PROJECTION_STATUS_COMPLETE,
        access_allowed=True,
    )
    with patch(
        "backend.app.services.workforce_downstream_identity.get_trusted_employment_identity_for_employee",
        new_callable=AsyncMock,
        return_value=trusted,
    ):
        result = await evaluate_contract_merge_identity(AsyncMock(), "t1", "e1")
    assert result.ready is True
    assert result.bindings["legal_name"] == "Jan Kowalski"
    assert result.block_code is None


@pytest.mark.asyncio
async def test_evaluate_payroll_prep_conflicted() -> None:
    with patch(
        "backend.app.services.workforce_downstream_identity.get_trusted_employment_identity_for_employee",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = TrustedIdentityAccessError(
            code="TRUSTED_IDENTITY_CONFLICTED",
            consumer=CONSUMER_PAYROLL_PREP,
            projection_status=PROJECTION_STATUS_CONFLICTED,
            review_id="r1",
            message="conflict",
        )
        result = await evaluate_payroll_preparation(AsyncMock(), "t1", "e1")
    assert result.blocked is True
    assert result.block_code == "TRUSTED_IDENTITY_CONFLICTED"


def test_downstream_identity_blocked_error_wraps_result() -> None:
    from backend.app.services.workforce_downstream_identity import DownstreamIdentityPrepResult

    prep = DownstreamIdentityPrepResult(
        ready=False,
        blocked=True,
        consumer=CONSUMER_PAYROLL_PREP,
        block_code="TRUSTED_IDENTITY_INCOMPLETE",
    )
    err = DownstreamIdentityBlockedError(prep)
    assert err.result.block_code == "TRUSTED_IDENTITY_INCOMPLETE"
