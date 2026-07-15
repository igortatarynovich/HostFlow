"""PR 2B-3 cutover tests — stage guard uses RequirementEvaluationService only."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.document_hub.document_data_contract import DocumentDataContract, DocumentEntityLink
from backend.app.requirement_rules.evaluation.result_contract import (
    OverallEvaluationStatus,
    RequirementApplicability,
    RequirementEvaluationResult,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
    NextActionCode,
)
from backend.app.services.candidate_doc_pipeline_guard import enforce_pipeline_doc_forward_block
from backend.app.services.hiring_pipeline_gates import default_hiring_pipeline_gates


def _evaluation(*, can_transition: bool, blocking: tuple[str, ...] = ()) -> RequirementEvaluationResult:
    rows = []
    for code in blocking:
        rows.append(
            RequirementEvaluationRow(
                requirement_code=code,
                applicability=RequirementApplicability.applicable,
                status=RequirementEvaluationStatus.missing,
                is_blocking=True,
                required_by_stage="docs_received",
                blocks_stage="docs_received",
                matched_alternative=None,
                matched_documents=(),
                matched_person_facts=(),
                matched_process=None,
                excluded_alternatives=(),
                missing_fields=(),
                reasons=(),
                ownership=None,
                next_action=NextActionCode.upload_document,
            )
        )
    return RequirementEvaluationResult(
        entity_type="candidate",
        entity_id="cand-1",
        policy_ref="recruitment.driver_ce.pl/v1",
        policy_version="v1",
        target_stage="docs_received",
        evaluated_at=datetime(2026, 7, 13, 12, 0, 0),
        input_fingerprint="fp",
        overall_status=OverallEvaluationStatus.blocked if blocking else OverallEvaluationStatus.ready,
        can_transition=can_transition,
        blocking_requirements=blocking,
        requirements=tuple(rows),
    )


@pytest.mark.anyio
async def test_stage_guard_uses_evaluator_only() -> None:
    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.tenant_id = "tenant-1"
    db.get = AsyncMock(return_value=candidate)

    evaluation = _evaluation(can_transition=False, blocking=("identity_document",))

    with patch(
        "backend.app.requirement_rules.evaluation.candidate_bridge.evaluate_candidate_requirements_v2",
        new=AsyncMock(return_value=evaluation),
    ) as evaluate_mock, patch(
        "backend.app.services.candidate_doc_pipeline_guard.resolve_hiring_pipeline_gates",
        new=AsyncMock(return_value=default_hiring_pipeline_gates()),
    ), patch(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_pipeline_relaxed_requirements",
        new=AsyncMock(return_value=set()),
    ):
        with pytest.raises(HTTPException) as exc:
            await enforce_pipeline_doc_forward_block(
                db,
                tenant_id="tenant-1",
                candidate_id="cand-1",
                old_stage="docs_wait",
                new_stage="docs_got",
                extra={},
                personal={},
            )

    evaluate_mock.assert_awaited_once()
    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert detail["blocker_source"] == "requirement_evaluation_v2"
    assert "identity_document" in detail["blocking_requirements"]


@pytest.mark.anyio
async def test_stage_guard_no_legacy_owner_summary_import() -> None:
    import backend.app.services.candidate_doc_pipeline_guard as guard

    source = open(guard.__file__, encoding="utf-8").read()
    assert "owner_summary" not in source
    assert "shadow_comparator" not in source
    assert "REQUIREMENT_EVALUATION_SHADOW" not in source
    assert "_legacy_document_type_blockers" not in source
    assert "_requirement_fulfillment_blockers" not in source


@pytest.mark.anyio
async def test_stage_guard_allows_when_evaluator_can_transition() -> None:
    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.tenant_id = "tenant-1"
    db.get = AsyncMock(return_value=candidate)

    with patch(
        "backend.app.requirement_rules.evaluation.candidate_bridge.evaluate_candidate_requirements_v2",
        new=AsyncMock(return_value=_evaluation(can_transition=True)),
    ), patch(
        "backend.app.services.candidate_doc_pipeline_guard.resolve_hiring_pipeline_gates",
        new=AsyncMock(return_value=default_hiring_pipeline_gates()),
    ), patch(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_pipeline_relaxed_requirements",
        new=AsyncMock(return_value=set()),
    ):
        await enforce_pipeline_doc_forward_block(
            db,
            tenant_id="tenant-1",
            candidate_id="cand-1",
            old_stage="docs_wait",
            new_stage="docs_got",
            extra={},
            personal={},
        )
