"""ADR-031 PR-2 — early Candidate shell + Application for compliance outbound."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.modules.recruitment.services.application_result_service import (
    ApplicationTransportConflictError,
)
from backend.app.modules.recruitment.services.compliance_outbound_ensure import (
    ComplianceOutboundEnsureError,
    SHELL_EXTRA_KEY,
    attach_compliance_shell_candidate_on_process,
    ensure_candidate_shell_and_application_for_compliance_outbound,
    lead_has_recruitment_intent,
    lead_is_recruitment_destination_for_compliance,
    lead_is_sales_bound_for_recruitment_ensure,
)


def test_sales_bound_detection() -> None:
    lead = SimpleNamespace(
        id="l1",
        vacancy_id=None,
        funnel_id=None,
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    assert lead_is_sales_bound_for_recruitment_ensure(lead) is True
    assert lead_is_recruitment_destination_for_compliance(lead) is False


def test_recruitment_intent_from_vacancy() -> None:
    lead = SimpleNamespace(
        id="l1",
        vacancy_id="v1",
        funnel_id=None,
        normalized={},
    )
    assert lead_has_recruitment_intent(lead) is True
    assert lead_is_recruitment_destination_for_compliance(lead) is True


@pytest.mark.asyncio
async def test_ensure_blocks_duplicate_review() -> None:
    lead = SimpleNamespace(
        id="l1",
        status="duplicate_review",
        vacancy_id="v1",
        funnel_id=None,
        candidate_id=None,
        normalized={},
    )
    with pytest.raises(ComplianceOutboundEnsureError) as exc:
        await ensure_candidate_shell_and_application_for_compliance_outbound(
            AsyncMock(), tenant_id="t1", lead=lead
        )
    assert exc.value.details.get("reason") == "duplicate_review"


@pytest.mark.asyncio
async def test_ensure_conflicts_when_sales_bound() -> None:
    lead = SimpleNamespace(
        id="l1",
        status="new",
        vacancy_id="v1",
        funnel_id=None,
        candidate_id=None,
        normalized={
            "intake_result_link_v1": {
                "result_type": "sales_inquiry",
                "sales_inquiry_id": "si-1",
            }
        },
    )
    with pytest.raises(ApplicationTransportConflictError):
        await ensure_candidate_shell_and_application_for_compliance_outbound(
            AsyncMock(), tenant_id="t1", lead=lead
        )


@pytest.mark.asyncio
async def test_ensure_creates_shell_without_linking_lead_candidate_id() -> None:
    lead = SimpleNamespace(
        id="lead-1",
        status="new",
        vacancy_id="vac-1",
        funnel_id=None,
        candidate_id=None,
        own_company_id="oc-1",
        company_id="co-1",
        source="meta",
        normalized={"email": "a@b.test", "first_name": "Ada", "last_name": "Lovelace"},
    )
    shell = SimpleNamespace(
        id="cand-shell",
        tenant_id="t1",
        deleted_at=None,
        extra={SHELL_EXTRA_KEY: True},
    )
    app = SimpleNamespace(id="app-1", candidate_id="cand-shell", lead_id="lead-1")
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.get = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    with (
        patch(
            "backend.app.modules.recruitment.services.compliance_outbound_ensure"
            ".create_candidate_full",
            new_callable=AsyncMock,
            return_value=shell,
        ) as create_full,
        patch(
            "backend.app.modules.recruitment.services.compliance_outbound_ensure"
            ".ensure_application_result_for_transport_lead",
            new_callable=AsyncMock,
            return_value=app,
        ) as ensure_app,
    ):
        result = await ensure_candidate_shell_and_application_for_compliance_outbound(
            db, tenant_id="t1", lead=lead, source="meta"
        )

    assert result.candidate_id == "cand-shell"
    assert result.application_id == "app-1"
    assert result.created_shell is True
    assert lead.candidate_id is None  # UX: Lead not converted
    create_full.assert_awaited_once()
    assert create_full.await_args.kwargs.get("source_lead") is None
    ensure_app.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_attaches_shell_candidate() -> None:
    lead = SimpleNamespace(id="lead-1", candidate_id=None)
    shell = SimpleNamespace(
        id="cand-shell",
        tenant_id="t1",
        deleted_at=None,
        extra={SHELL_EXTRA_KEY: True},
    )
    app = SimpleNamespace(id="app-1", candidate_id="cand-shell")
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=app)
    db.get = AsyncMock(return_value=shell)
    db.flush = AsyncMock()

    with patch(
        "backend.app.modules.recruitment.services.compliance_outbound_ensure.flag_modified",
    ):
        attached = await attach_compliance_shell_candidate_on_process(
            db, tenant_id="t1", lead=lead
        )
    assert attached is shell
    assert lead.candidate_id == "cand-shell"
    assert shell.extra.get("compliance_shell_attached_at_process")
