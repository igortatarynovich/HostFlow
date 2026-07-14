"""PR 2B-4 — fleet migration audit & apply tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.models.enums import CandidateEvidenceStatus
from backend.app.requirement_rules.evaluation.result_contract import (
    OverallEvaluationStatus,
    RequirementApplicability,
    RequirementEvaluationResult,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
    NextActionCode,
)
from backend.app.requirement_rules.migration.apply import apply_candidate_migration
from backend.app.requirement_rules.migration.batch_runner import run_batch
from backend.app.requirement_rules.migration.candidate_auditor import audit_candidate
from backend.app.requirement_rules.migration.classifier import classify_migration_category
from backend.app.requirement_rules.migration.contracts import (
    CandidateAuditResult,
    IssueCategory,
    MigrationCategory,
    MigrationStatus,
)
from backend.app.requirement_rules.migration.evidence_helpers import (
    assess_evidence_supersede_eligibility,
    is_protected_evidence_variant,
    is_standard_manual_evidence,
)


def _evaluation(*, can_transition: bool = True, fingerprint: str = "fp-1") -> RequirementEvaluationResult:
    return RequirementEvaluationResult(
        entity_type="candidate",
        entity_id="cand-1",
        policy_ref="recruitment.driver_ce.pl/v1",
        policy_version="v1",
        target_stage="docs_received",
        evaluated_at=datetime(2026, 7, 13, 12, 0, 0),
        input_fingerprint=fingerprint,
        overall_status=OverallEvaluationStatus.ready if can_transition else OverallEvaluationStatus.blocked,
        can_transition=can_transition,
        blocking_requirements=() if can_transition else ("identity_document",),
        requirements=(
            RequirementEvaluationRow(
                requirement_code="identity_document",
                applicability=RequirementApplicability.applicable,
                status=RequirementEvaluationStatus.fulfilled if can_transition else RequirementEvaluationStatus.missing,
                is_blocking=not can_transition,
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
            ),
        ),
    )


def _audit_result(**overrides) -> CandidateAuditResult:
    base = CandidateAuditResult(
        candidate_id="cand-1",
        tenant_id="tenant-1",
        vacancy_id="vac-1",
        current_stage="docs_received",
        requirement_policy_ref=None,
        resolved_policy_ref="recruitment.driver_ce.pl/v1",
        policy_pinned=False,
        policy_valid=True,
        issue_categories=(IssueCategory.policy_missing, IssueCategory.manual_evidence_present),
        migration_category=MigrationCategory.safe_auto_migration,
        documents=(),
        evidence_rows=(),
        evaluator_fingerprint="fp-1",
        evaluator_can_transition=True,
        blocking_requirements=(),
        next_blocking_requirement=None,
        stage_allowed_by_policy=True,
        stage_conflict_kind=None,
        document_evaluation_mismatch=False,
        recommended_action="",
        migration_status=MigrationStatus.pending,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _classify_kwargs(**overrides):
    base = {
        "issue_categories": set(),
        "policy_resolvable": True,
        "policy_pinned_and_valid": True,
        "stage_inconsistent": False,
        "has_ambiguous_documents": False,
        "has_unclassified": False,
        "has_unknown_legacy": False,
        "has_standard_evidence": False,
        "has_supersede_eligible_evidence": False,
        "citizenship_unresolved": False,
        "citizenship_conflict": False,
        "residency_unresolved": False,
        "evaluation_runtime_error": False,
        "evaluation_input_incomplete": False,
        "policy_context_unresolved": False,
        "document_contract_invalid": False,
        "document_data_incomplete": False,
        "document_version_unresolved": False,
        "code95_validity_unresolved": False,
        "all_participating_docs_contract_ready": True,
    }
    base.update(overrides)
    return base


def test_dry_run_apply_does_not_write() -> None:
    import asyncio

    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.requirement_policy_ref = None
    candidate._get_extra = MagicMock(return_value={})
    audit = _audit_result()

    with patch(
        "backend.app.requirement_rules.migration.apply.list_candidate_documents",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.requirement_rules.migration.apply._supersede_eligible_evidence",
        new=AsyncMock(return_value=2),
    ) as supersede_mock, patch(
        "backend.app.requirement_rules.migration.apply._assign_document_versions",
        new=AsyncMock(return_value=0),
    ):
        result = asyncio.run(
            apply_candidate_migration(
                db,
                tenant_id="tenant-1",
                candidate=candidate,
                audit=audit,
                dry_run=True,
            )
        )
    assert result.dry_run is True
    assert result.applied is False
    supersede_mock.assert_awaited_once()
    db.commit.assert_not_called()


def test_idempotent_apply_skips_clean_candidate() -> None:
    import asyncio

    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    audit = _audit_result(
        migration_category=MigrationCategory.clean,
        requirement_policy_ref="recruitment.driver_ce.pl/v1",
        policy_pinned=True,
        issue_categories=(),
    )

    result = asyncio.run(
        apply_candidate_migration(
            db,
            tenant_id="tenant-1",
            candidate=candidate,
            audit=audit,
            dry_run=False,
        )
    )
    assert result.steps == ["already_clean"]
    assert result.applied is False


def test_waiver_evidence_not_superseded() -> None:
    assert is_protected_evidence_variant("waiver_identity")
    assert is_protected_evidence_variant("driver_attestation")
    assert not is_protected_evidence_variant("approved_passport")
    assert is_standard_manual_evidence(
        evidence_variant_code="approved_passport",
        status=CandidateEvidenceStatus.approved.value,
    )
    assert not is_standard_manual_evidence(
        evidence_variant_code="waiver_identity",
        status=CandidateEvidenceStatus.approved.value,
    )


def test_operator_decision_blocks_supersede() -> None:
    evidence = MagicMock()
    evidence.evidence_variant_code = "approved_passport"
    evidence.requirement_code = "identity_document"
    evidence.status = CandidateEvidenceStatus.approved.value
    evidence.approved_by = "user-1"
    evidence.rejected_by = None
    evidence.notes = None
    evidence.documents = []
    eligible, reason = assess_evidence_supersede_eligibility(evidence)
    assert not eligible
    assert reason == "operator_decision_present"


def test_ambiguous_document_not_safe_auto_migration() -> None:
    category, _, _ = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.unclassified_document},
            has_unclassified=True,
            has_ambiguous_documents=True,
            policy_pinned_and_valid=False,
        )
    )
    assert category == MigrationCategory.needs_classification


def test_unresolved_version_not_safe_auto_migration() -> None:
    category, _, _ = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.document_version_unresolved},
            document_version_unresolved=True,
            all_participating_docs_contract_ready=False,
        )
    )
    assert category == MigrationCategory.needs_classification


def test_missing_policy_goes_to_review() -> None:
    category, action, status = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.policy_missing},
            policy_resolvable=False,
            policy_pinned_and_valid=False,
        )
    )
    assert category == MigrationCategory.needs_policy_assignment
    assert status == MigrationStatus.review_required
    assert "policy" in action.lower()


def test_stage_inconsistency_never_auto_rollback() -> None:
    category, action, status = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.stage_data_corruption_or_missing},
            stage_inconsistent={IssueCategory.stage_data_corruption_or_missing},
        )
    )
    assert category == MigrationCategory.stage_inconsistency
    assert status == MigrationStatus.review_required
    assert "rollback" in action.lower()


@pytest.mark.anyio
async def test_audit_dry_run_no_db_writes() -> None:
    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.tenant_id = "tenant-1"
    candidate.status = "docs_received"
    candidate.vacancy_id = "vac-1"
    candidate.requirement_policy_ref = None
    candidate._get_extra = MagicMock(return_value={"citizenship": "ua"})
    candidate._get_personal_data = MagicMock(return_value={})

    with patch(
        "backend.app.requirement_rules.migration.candidate_auditor.resolve_policy_ref_for_candidate",
        new=AsyncMock(return_value="recruitment.driver_ce.pl/v1"),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.list_candidate_documents",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor._load_evidence_rows",
        new=AsyncMock(return_value=()),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.evaluate_candidate_requirements_v2",
        new=AsyncMock(return_value=_evaluation()),
    ):
        audit = await audit_candidate(db, tenant_id="tenant-1", candidate=candidate)
    assert audit.migration_category in {
        MigrationCategory.safe_auto_migration,
        MigrationCategory.clean,
        MigrationCategory.needs_classification,
    }
    db.commit.assert_not_called()


@pytest.mark.anyio
async def test_fingerprint_stable_after_reaudit() -> None:
    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.tenant_id = "tenant-1"
    candidate.status = "docs_received"
    candidate.vacancy_id = "vac-1"
    candidate.requirement_policy_ref = "recruitment.driver_ce.pl/v1"
    candidate._get_extra = MagicMock(return_value={"citizenship": "pl"})
    candidate._get_personal_data = MagicMock(return_value={})

    eval_mock = AsyncMock(return_value=_evaluation(fingerprint="stable-fp"))
    with patch(
        "backend.app.requirement_rules.migration.candidate_auditor.resolve_policy_ref_for_candidate",
        new=AsyncMock(return_value="recruitment.driver_ce.pl/v1"),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.list_candidate_documents",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor._load_evidence_rows",
        new=AsyncMock(return_value=()),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.evaluate_candidate_requirements_v2",
        new=eval_mock,
    ):
        first = await audit_candidate(db, tenant_id="tenant-1", candidate=candidate)
        second = await audit_candidate(db, tenant_id="tenant-1", candidate=candidate)
    assert first.evaluator_fingerprint == second.evaluator_fingerprint == "stable-fp"


@pytest.mark.anyio
async def test_tenant_isolation_in_batch() -> None:
    db = AsyncMock()
    with patch(
        "backend.app.requirement_rules.migration.batch_runner._load_candidates",
        new=AsyncMock(return_value=[]),
    ) as load_mock:
        await run_batch(db, tenant_id="tenant-1", audit_only=True)
    assert load_mock.await_args.kwargs["tenant_id"] == "tenant-1"


@pytest.mark.anyio
async def test_batch_resume_checkpoint() -> None:
    db = AsyncMock()
    tmp = Path("/tmp/adr018-test-checkpoint.json")
    tmp.write_text(json.dumps({"last_candidate_id": "cand-0", "run_id": "run-1"}), encoding="utf-8")

    with patch(
        "backend.app.requirement_rules.migration.batch_runner._load_candidates",
        new=AsyncMock(return_value=[]),
    ) as load_mock:
        report = await run_batch(db, tenant_id="tenant-1", resume_checkpoint=tmp)
    load_mock.assert_awaited_once()
    assert load_mock.await_args.kwargs["resume_after_id"] == "cand-0"
    assert report.run_id == "run-1"
    tmp.unlink(missing_ok=True)


@pytest.mark.anyio
async def test_new_candidate_finalize_hook_wired() -> None:
    from backend.app.api.v1.candidates import service as candidate_service
    from backend.app.api.v1.communications._helpers.telegram_intake import candidate_link

    canonical = Path(candidate_service.__file__).read_text(encoding="utf-8")
    telegram = Path(candidate_link.__file__).read_text(encoding="utf-8")
    assert "finalize_new_candidate_record" in canonical
    assert "finalize_new_candidate_record" in telegram


@pytest.mark.anyio
async def test_safe_candidate_apply_pins_policy_and_minimal_marker() -> None:
    db = AsyncMock()

    class _Candidate:
        id = "cand-1"
        status = "docs_received"
        requirement_policy_ref = None

        def __init__(self) -> None:
            self._extra: dict = {}

        def _get_extra(self):
            return self._extra

        def _set_extra(self, value):
            self._extra = dict(value)

    candidate = _Candidate()
    audit = _audit_result()

    with patch(
        "backend.app.requirement_rules.migration.apply.pin_requirement_policy",
        new=AsyncMock(return_value="recruitment.driver_ce.pl/v1"),
    ) as pin_mock, patch(
        "backend.app.requirement_rules.migration.apply.list_candidate_documents",
        new=AsyncMock(return_value=[]),
    ), patch(
        "backend.app.requirement_rules.migration.apply._supersede_eligible_evidence",
        new=AsyncMock(return_value=1),
    ), patch(
        "backend.app.requirement_rules.migration.apply._assign_document_versions",
        new=AsyncMock(return_value=0),
    ), patch(
        "backend.app.requirement_rules.migration.apply.evaluate_candidate_requirements_v2",
        new=AsyncMock(return_value=_evaluation(fingerprint="post-migrate-fp")),
    ):
        result = await apply_candidate_migration(
            db,
            tenant_id="tenant-1",
            candidate=candidate,
            audit=audit,
            dry_run=False,
            run_id="run-test",
        )
    pin_mock.assert_awaited_once()
    assert result.applied is True
    assert "pin_policy" in result.steps
    assert result.input_fingerprint == "post-migrate-fp"
    marker = candidate._extra["adr018_migration"]
    assert set(marker.keys()) == {
        "migration_version",
        "status",
        "input_fingerprint",
        "migrated_at",
        "run_id",
    }
