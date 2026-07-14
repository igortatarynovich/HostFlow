"""PR 2B-4.2 — historical data normalization tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.app.document_types.schema_registry import normalize_driver_categories, normalize_raw_to_document_data
from backend.app.requirement_rules.migration.candidate_auditor import audit_candidate
from backend.app.requirement_rules.migration.citizenship_normalizer import assess_citizenship
from backend.app.requirement_rules.migration.classifier import classify_migration_category
from backend.app.requirement_rules.migration.contracts import IssueCategory, MigrationCategory, MigrationStatus
from backend.app.requirement_rules.migration.document_metadata_adapter import migrate_legacy_document_metadata
from backend.app.requirement_rules.migration.redaction import occurrence_id, stable_issue_id
from backend.app.requirement_rules.migration.review_queue import build_review_queue_entries


def _classify_kwargs(**overrides):
    base = {
        "issue_categories": set(),
        "policy_resolvable": True,
        "policy_pinned_and_valid": False,
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


def test_policy_missing_alone_allows_safe_auto_migration() -> None:
    category, _, status = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.policy_missing, IssueCategory.legacy_document_type},
            policy_resolvable=True,
            policy_pinned_and_valid=False,
        )
    )
    assert category == MigrationCategory.safe_auto_migration
    assert status == MigrationStatus.pending


def test_evaluation_runtime_error_blocks_safe_migration() -> None:
    category, action, _ = classify_migration_category(
        **_classify_kwargs(
            issue_categories={IssueCategory.evaluation_runtime_error},
            evaluation_runtime_error=True,
        )
    )
    assert category == MigrationCategory.needs_classification
    assert "runtime" in action.lower()


def test_stable_issue_id_independent_of_run_id() -> None:
    first = stable_issue_id(
        candidate_id="cand-1",
        issue_category="citizenship_unresolved",
        affected_source="",
    )
    second = stable_issue_id(
        candidate_id="cand-1",
        issue_category="citizenship_unresolved",
        affected_source="",
    )
    assert first == second
    different_run = occurrence_id(run_id="run-a", issue_id=first)
    different_run_2 = occurrence_id(run_id="run-b", issue_id=first)
    assert different_run != different_run_2
    assert occurrence_id(run_id="run-a", issue_id=first) == different_run


def test_citizenship_from_approved_passport() -> None:
    candidate = MagicMock()
    candidate._get_extra = MagicMock(return_value={})
    candidate._get_personal_data = MagicMock(return_value={})
    doc = MagicMock()
    doc.id = "doc-1"
    doc.doc_type = "passport"
    doc.status = MagicMock(value="approved")
    doc.meta = {"extracted_fields": {"nationality": "UA"}}

    result = assess_citizenship(candidate, documents=[doc])
    assert result.status == "resolved"
    assert result.iso2 == "UA"
    assert result.provenance.startswith("approved_identity_document")


def test_citizenship_conflict_detected() -> None:
    candidate = MagicMock()
    candidate._get_extra = MagicMock(return_value={"citizenship": "PL"})
    candidate._get_personal_data = MagicMock(return_value={"citizenship": "UA"})

    result = assess_citizenship(candidate, documents=[])
    assert result.status == "conflict"
    assert set(result.conflict_values) == {"PL", "UA"}


def test_legacy_document_type_mapping_via_canonical_bridge() -> None:
    from backend.app.document_types.registry import normalize_input_doc_type

    assert normalize_input_doc_type("tacho_card") == "tachograph_card"
    assert normalize_input_doc_type("national_id") == "national_identity_card"
    assert normalize_input_doc_type("code95") == "driver_qualification_card"
    assert normalize_input_doc_type("psych_tests") == "psychological_certificate"


def test_driver_categories_normalization() -> None:
    assert normalize_driver_categories("C+E") == ["CE"]
    assert normalize_driver_categories(["c", " ce "]) == ["C", "CE"]
    raw = normalize_raw_to_document_data(
        "driver_license",
        {"categories": "C+E, B", "issuing_country": "pl"},
    )
    assert raw["categories"] == ["CE", "B"]
    assert raw["issuing_country"] == "PL"


def test_code95_unresolved_issue_when_ce_without_validity() -> None:
    result = migrate_legacy_document_metadata(
        stored_doc_type="driver_license",
        meta={
            "extracted_fields": {
                "categories": ["CE"],
                "document_number": "DL1",
                "issuing_country": "PL",
                "expiry_date": "2030-01-01",
            }
        },
    )
    assert result.code95_validity_unresolved is True
    assert "code95_validity_unresolved" in result.issues


def test_code95_resolved_from_legacy_field() -> None:
    result = migrate_legacy_document_metadata(
        stored_doc_type="driver_license",
        meta={
            "categories": ["CE"],
            "document_number": "DL1",
            "issuing_country": "PL",
            "expiry_date": "2030-01-01",
            "code95_valid_to": "2030-06-01",
        },
    )
    assert result.document_data.get("code_95_valid_to") == "2030-06-01"
    assert result.code95_validity_unresolved is False


def test_review_queue_per_issue_with_occurrence_id() -> None:
    from backend.app.requirement_rules.migration.contracts import CandidateAuditResult

    audit = CandidateAuditResult(
        candidate_id="cand-1",
        tenant_id="tenant-1",
        vacancy_id=None,
        current_stage="docs_received",
        requirement_policy_ref=None,
        resolved_policy_ref="recruitment.driver_ce.pl/v1",
        policy_pinned=False,
        policy_valid=True,
        issue_categories=(
            IssueCategory.policy_missing,
            IssueCategory.legacy_document_type,
        ),
        migration_category=MigrationCategory.needs_classification,
        documents=(),
        evidence_rows=(),
        evaluator_fingerprint="fp",
        evaluator_can_transition=True,
        blocking_requirements=(),
        next_blocking_requirement=None,
        stage_allowed_by_policy=True,
        stage_conflict_kind=None,
        document_evaluation_mismatch=False,
        recommended_action="review",
        migration_status=MigrationStatus.review_required,
    )
    entries = build_review_queue_entries(audit, run_id="run-1")
    assert len(entries) == 2
    assert entries[0].issue_category != entries[1].issue_category
    assert all(entry.occurrence_id for entry in entries)


@pytest.mark.anyio
async def test_audit_resolves_citizenship_from_document_without_db_write() -> None:
    from datetime import datetime
    from unittest.mock import AsyncMock, patch

    from backend.app.requirement_rules.evaluation.result_contract import (
        NextActionCode,
        OverallEvaluationStatus,
        RequirementApplicability,
        RequirementEvaluationResult,
        RequirementEvaluationRow,
        RequirementEvaluationStatus,
    )

    db = AsyncMock()
    candidate = MagicMock()
    candidate.id = "cand-1"
    candidate.tenant_id = "tenant-1"
    candidate.status = "docs_received"
    candidate.vacancy_id = "vac-1"
    candidate.requirement_policy_ref = None
    candidate._get_extra = MagicMock(return_value={})
    candidate._get_personal_data = MagicMock(return_value={})

    passport = MagicMock()
    passport.id = "doc-passport"
    passport.doc_type = "passport"
    passport.status = MagicMock(value="approved")
    passport.meta = {
        "extracted_fields": {
            "nationality": "UA",
            "document_number": "P1",
            "issuing_country": "UA",
            "expiry_date": "2030-01-01",
        }
    }
    passport.document_type_version_id = "ver-1"
    passport.expire_date = None

    evaluation = RequirementEvaluationResult(
        entity_type="candidate",
        entity_id="cand-1",
        policy_ref="recruitment.driver_ce.pl/v1",
        policy_version="v1",
        target_stage="docs_received",
        evaluated_at=datetime(2026, 7, 13, 12, 0, 0),
        input_fingerprint="fp-1",
        overall_status=OverallEvaluationStatus.ready,
        can_transition=True,
        blocking_requirements=(),
        requirements=(
            RequirementEvaluationRow(
                requirement_code="identity_document",
                applicability=RequirementApplicability.applicable,
                status=RequirementEvaluationStatus.fulfilled,
                is_blocking=False,
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

    with patch(
        "backend.app.requirement_rules.migration.candidate_auditor.resolve_policy_ref_for_candidate",
        new=AsyncMock(return_value="recruitment.driver_ce.pl/v1"),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.list_candidate_documents",
        new=AsyncMock(return_value=[passport]),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor._audit_documents",
        new=AsyncMock(return_value=()),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor._load_evidence_rows",
        new=AsyncMock(return_value=()),
    ), patch(
        "backend.app.requirement_rules.migration.candidate_auditor.evaluate_candidate_requirements_v2",
        new=AsyncMock(return_value=evaluation),
    ):
        audit = await audit_candidate(db, tenant_id="tenant-1", candidate=candidate)

    assert IssueCategory.citizenship_unresolved not in audit.issue_categories
    assert IssueCategory.citizenship_conflict not in audit.issue_categories
