"""Document merge context trusted identity (PR7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.document_merge.context import build_merge_context
from backend.app.services.employment_identity_read_adapter import CONSUMER_CONTRACT_GENERATION
from backend.app.services.workforce_downstream_identity import DownstreamIdentityPrepResult


@pytest.mark.asyncio
async def test_merge_context_blocked_without_fallback() -> None:
    employee = MagicMock()
    employee.id = "e1"
    employee.tenant_id = "t1"
    employee.own_company_id = None
    employee.display_name = "Recruitment Name"
    employee.candidate_id = "c1"
    employee.status = "onboarding"
    employee.hire_date = None
    employee.probation_end = None
    employee.termination_date = None
    employee.company_id = None
    employee.vacancy_id = None

    blocked = DownstreamIdentityPrepResult(
        ready=False,
        blocked=True,
        consumer=CONSUMER_CONTRACT_GENERATION,
        block_code="TRUSTED_IDENTITY_INCOMPLETE",
        projection_status="incomplete",
        review_id="r1",
        message="incomplete",
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    with patch(
        "backend.app.services.document_merge.context.evaluate_contract_merge_identity",
        new_callable=AsyncMock,
        return_value=blocked,
    ):
        ctx = await build_merge_context(session, "t1", employee=employee, candidate=None)

    assert ctx["identity"]["blocked"] is True
    assert ctx["identity"]["block_code"] == "TRUSTED_IDENTITY_INCOMPLETE"
    assert ctx["trusted_identity"] == {}
    assert "legal_name" not in ctx["bindings"]


@pytest.mark.asyncio
async def test_merge_context_complete_adds_bindings() -> None:
    employee = MagicMock()
    employee.id = "e1"
    employee.tenant_id = "t1"
    employee.own_company_id = None
    employee.display_name = "Old Name"
    employee.candidate_id = None
    employee.status = "onboarding"
    employee.hire_date = None
    employee.probation_end = None
    employee.termination_date = None
    employee.company_id = None
    employee.vacancy_id = None

    ready = DownstreamIdentityPrepResult(
        ready=True,
        blocked=False,
        consumer=CONSUMER_CONTRACT_GENERATION,
        projection_status="complete",
        review_id="r1",
        bindings={"legal_name": "Jan Kowalski", "citizenship": "PL", "pesel": "123"},
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    with patch(
        "backend.app.services.document_merge.context.evaluate_contract_merge_identity",
        new_callable=AsyncMock,
        return_value=ready,
    ):
        ctx = await build_merge_context(session, "t1", employee=employee, candidate=None)

    assert ctx["identity"]["blocked"] is False
    assert ctx["bindings"]["legal_name"] == "Jan Kowalski"
    assert ctx["trusted_identity"]["pesel"] == "123"
    assert ctx["employee"]["display_name"] == "Jan Kowalski"
