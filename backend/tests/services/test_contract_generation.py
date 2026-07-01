"""Contract generation MVP — trusted identity only (PR9)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.contract_generation import (
    assert_contract_generation_allowed,
    validate_contract_template_placeholders,
)
from backend.app.services.employment_identity_projection import PROJECTION_STATUS_INCOMPLETE
from backend.app.services.employment_identity_read_adapter import TrustedIdentityAccessError


def test_validate_contract_template_rejects_candidate_placeholders() -> None:
    body = "Name: {{ trusted_identity.legal_name }} / bad {{ candidate.full_name }}"
    violations = validate_contract_template_placeholders(body)
    assert "candidate.full_name" in violations


def test_validate_contract_template_allows_trusted_identity() -> None:
    body = "{{ trusted_identity.legal_name }}, {{ trusted_identity.pesel }}"
    assert validate_contract_template_placeholders(body) == []


@pytest.mark.asyncio
async def test_assert_contract_generation_blocked() -> None:
    from backend.app.services.workforce_downstream_identity import DownstreamIdentityPrepResult

    blocked = DownstreamIdentityPrepResult(
        ready=False,
        blocked=True,
        consumer="contract_generation",
        block_code="TRUSTED_IDENTITY_INCOMPLETE",
        projection_status=PROJECTION_STATUS_INCOMPLETE,
        review_id="r1",
    )
    with patch(
        "backend.app.services.contract_generation.evaluate_contract_merge_identity",
        new_callable=AsyncMock,
        return_value=blocked,
    ):
        with pytest.raises(TrustedIdentityAccessError) as exc:
            await assert_contract_generation_allowed(AsyncMock(), "t1", "e1")
    assert exc.value.code == "TRUSTED_IDENTITY_INCOMPLETE"


@pytest.mark.asyncio
async def test_generate_contract_draft_preview_success() -> None:
    from backend.app.services.contract_generation import generate_contract_draft_preview

    emp = MagicMock()
    emp.id = "e1"
    emp.tenant_id = "t1"
    emp.candidate_id = "c1"
    emp.own_company_id = None

    template = MagicMock()
    template.id = "tpl1"
    template.code = "employment_contract"
    template.name = "Contract"
    template.body_text = "Employee: {{ trusted_identity.legal_name }}"
    template.output_filename_pattern = "{{ trusted_identity.legal_name }}_draft"
    template.doc_type = "additional_document"
    template.output_mime = "text/plain"
    template.variable_bindings = {}

    log = MagicMock()
    log.id = "log1"
    log.template_id = "tpl1"
    log.status = "draft_preview"
    doc = MagicMock()
    doc.id = "doc1"
    doc.files = [{"url": "https://example.com/draft.txt"}]

    with patch(
        "backend.app.services.workforce_employees.get_employee",
        new_callable=AsyncMock,
        return_value=emp,
    ):
        with patch(
            "backend.app.services.contract_generation.evaluate_contract_merge_identity",
            new_callable=AsyncMock,
            return_value=MagicMock(
                blocked=False,
                bindings={"legal_name": "Jan Kowalski"},
                review_id="r1",
                projection_status="complete",
            ),
        ):
            with patch(
                "backend.app.services.contract_generation.get_template",
                new_callable=AsyncMock,
                return_value=template,
            ):
                with patch(
                    "backend.app.services.contract_generation.generate_merge_document",
                    new_callable=AsyncMock,
                    return_value=(log, doc),
                ):
                    log_out, doc_out, meta = await generate_contract_draft_preview(
                        AsyncMock(),
                        "t1",
                        employee_id="e1",
                        template_id="tpl1",
                    )
    assert log_out.status == "draft_preview"
    assert meta["trusted_identity_bindings"]["legal_name"] == "Jan Kowalski"
    assert meta["automation"]["sign"] is False
