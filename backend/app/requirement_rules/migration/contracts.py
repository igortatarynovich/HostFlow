"""Contracts for ADR-018 fleet migration audit & apply."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class IssueCategory(str, Enum):
    policy_missing = "policy_missing"
    legacy_document_type = "legacy_document_type"
    document_data_incomplete = "document_data_incomplete"
    document_version_unresolved = "document_version_unresolved"
    unclassified_document = "unclassified_document"
    manual_evidence_present = "manual_evidence_present"
    stage_historical_permitted_now_stricter = "stage_historical_permitted_now_stricter"
    stage_data_corruption_or_missing = "stage_data_corruption_or_missing"
    citizenship_unresolved = "citizenship_unresolved"
    citizenship_conflict = "citizenship_conflict"
    residency_unresolved = "residency_unresolved"
    code95_validity_unresolved = "code95_validity_unresolved"
    evaluation_input_incomplete = "evaluation_input_incomplete"
    policy_context_unresolved = "policy_context_unresolved"
    document_contract_invalid = "document_contract_invalid"
    evaluation_runtime_error = "evaluation_runtime_error"
    evaluation_error = "evaluation_error"


class MigrationCategory(str, Enum):
    clean = "clean"
    safe_auto_migration = "safe_auto_migration"
    needs_classification = "needs_classification"
    needs_policy_assignment = "needs_policy_assignment"
    stage_inconsistency = "stage_inconsistency"


class MigrationStatus(str, Enum):
    pending = "pending"
    migrated = "migrated"
    review_required = "review_required"
    skipped = "skipped"
    failed = "failed"


class StageConflictKind(str, Enum):
    historical_permitted_now_stricter = "historical_permitted_now_stricter"
    data_corruption_or_missing = "data_corruption_or_missing"


@dataclass(frozen=True)
class DocumentAuditRow:
    document_id: str
    stored_doc_type: str
    canonical_type_code: str
    has_legacy_type: bool
    is_unclassified: bool
    missing_type_version_id: bool
    version_assignment_status: Optional[str]
    resolvable_version_id: Optional[str]
    schema_valid: bool
    schema_errors: tuple[str, ...]
    review_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "stored_doc_type": self.stored_doc_type,
            "canonical_type_code": self.canonical_type_code,
            "has_legacy_type": self.has_legacy_type,
            "is_unclassified": self.is_unclassified,
            "missing_type_version_id": self.missing_type_version_id,
            "version_assignment_status": self.version_assignment_status,
            "resolvable_version_id": self.resolvable_version_id,
            "schema_valid": self.schema_valid,
            "schema_errors": list(self.schema_errors),
            "review_status": self.review_status,
        }


@dataclass(frozen=True)
class EvidenceAuditRow:
    evidence_id: str
    requirement_code: str
    evidence_variant_code: str
    status: str
    is_standard: bool
    is_protected: bool
    supersede_eligible: bool
    supersede_block_reason: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "requirement_code": self.requirement_code,
            "evidence_variant_code": self.evidence_variant_code,
            "status": self.status,
            "is_standard": self.is_standard,
            "is_protected": self.is_protected,
            "supersede_eligible": self.supersede_eligible,
            "supersede_block_reason": self.supersede_block_reason,
        }


@dataclass
class CandidateAuditResult:
    candidate_id: str
    tenant_id: str
    vacancy_id: Optional[str]
    current_stage: str
    requirement_policy_ref: Optional[str]
    resolved_policy_ref: Optional[str]
    policy_pinned: bool
    policy_valid: bool
    issue_categories: tuple[IssueCategory, ...]
    migration_category: MigrationCategory
    documents: tuple[DocumentAuditRow, ...]
    evidence_rows: tuple[EvidenceAuditRow, ...]
    evaluator_fingerprint: Optional[str]
    evaluator_can_transition: Optional[bool]
    blocking_requirements: tuple[str, ...]
    next_blocking_requirement: Optional[str]
    stage_allowed_by_policy: bool
    stage_conflict_kind: Optional[StageConflictKind]
    document_evaluation_mismatch: bool
    recommended_action: str
    migration_status: MigrationStatus
    evaluation_error: Optional[str] = None
    affected_requirements: tuple[str, ...] = ()
    affected_documents: tuple[str, ...] = ()
    missing_metadata_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "tenant_id": self.tenant_id,
            "vacancy_id": self.vacancy_id,
            "current_stage": self.current_stage,
            "requirement_policy_ref": self.requirement_policy_ref,
            "resolved_policy_ref": self.resolved_policy_ref,
            "policy_pinned": self.policy_pinned,
            "policy_valid": self.policy_valid,
            "issue_categories": [c.value for c in self.issue_categories],
            "migration_category": self.migration_category.value,
            "documents": [d.to_dict() for d in self.documents],
            "evidence_rows": [e.to_dict() for e in self.evidence_rows],
            "evaluator_fingerprint": self.evaluator_fingerprint,
            "evaluator_can_transition": self.evaluator_can_transition,
            "blocking_requirements": list(self.blocking_requirements),
            "next_blocking_requirement": self.next_blocking_requirement,
            "stage_allowed_by_policy": self.stage_allowed_by_policy,
            "stage_conflict_kind": self.stage_conflict_kind.value if self.stage_conflict_kind else None,
            "document_evaluation_mismatch": self.document_evaluation_mismatch,
            "recommended_action": self.recommended_action,
            "migration_status": self.migration_status.value,
            "evaluation_error": self.evaluation_error,
            "affected_requirements": list(self.affected_requirements),
            "affected_documents": list(self.affected_documents),
            "missing_metadata_fields": list(self.missing_metadata_fields),
        }


@dataclass
class CandidateApplyResult:
    candidate_id: str
    applied: bool
    dry_run: bool
    policy_ref: Optional[str]
    superseded_evidence_count: int
    normalized_documents_count: int
    metadata_migrated_count: int
    version_assigned_count: int
    input_fingerprint: Optional[str]
    run_id: Optional[str]
    steps: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "applied": self.applied,
            "dry_run": self.dry_run,
            "policy_ref": self.policy_ref,
            "superseded_evidence_count": self.superseded_evidence_count,
            "normalized_documents_count": self.normalized_documents_count,
            "metadata_migrated_count": self.metadata_migrated_count,
            "version_assigned_count": self.version_assigned_count,
            "input_fingerprint": self.input_fingerprint,
            "run_id": self.run_id,
            "steps": list(self.steps),
            "error": self.error,
        }


@dataclass
class FleetAggregateSummary:
    total_candidates: int
    by_tenant: dict[str, int]
    by_policy: dict[str, int]
    without_policy: int
    with_legacy_aliases: int
    with_unclassified: int
    without_document_type_version: int
    with_invalid_document_data: int
    with_standard_manual_evidence: int
    citizenship_unresolved: int
    citizenship_conflict: int
    residency_unresolved: int
    stage_conflict: int
    evaluation_runtime_error: int
    evaluation_input_incomplete: int
    policy_context_unresolved: int
    document_contract_invalid: int
    code95_validity_unresolved: int
    evaluation_error: int
    safe_auto_migration: int
    top_legacy_document_codes: dict[str, int]
    top_missing_metadata_fields: dict[str, int]
    top_blocking_requirements: dict[str, int]
    policy_assignment_blocked: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_candidates": self.total_candidates,
            "by_tenant": dict(self.by_tenant),
            "by_policy": dict(self.by_policy),
            "without_policy": self.without_policy,
            "with_legacy_aliases": self.with_legacy_aliases,
            "with_unclassified": self.with_unclassified,
            "without_document_type_version": self.without_document_type_version,
            "with_invalid_document_data": self.with_invalid_document_data,
            "with_standard_manual_evidence": self.with_standard_manual_evidence,
            "citizenship_unresolved": self.citizenship_unresolved,
            "citizenship_conflict": self.citizenship_conflict,
            "residency_unresolved": self.residency_unresolved,
            "stage_conflict": self.stage_conflict,
            "evaluation_runtime_error": self.evaluation_runtime_error,
            "evaluation_input_incomplete": self.evaluation_input_incomplete,
            "policy_context_unresolved": self.policy_context_unresolved,
            "document_contract_invalid": self.document_contract_invalid,
            "code95_validity_unresolved": self.code95_validity_unresolved,
            "evaluation_error": self.evaluation_error,
            "safe_auto_migration": self.safe_auto_migration,
            "top_legacy_document_codes": dict(self.top_legacy_document_codes),
            "top_missing_metadata_fields": dict(self.top_missing_metadata_fields),
            "top_blocking_requirements": dict(self.top_blocking_requirements),
            "policy_assignment_blocked": self.policy_assignment_blocked,
        }


@dataclass
class BatchReport:
    generated_at: datetime
    run_id: str
    mode: str
    tenant_id: Optional[str]
    vacancy_id: Optional[str]
    total_candidates: int
    by_migration_category: dict[str, int]
    by_issue_category: dict[str, int]
    by_tenant: dict[str, int]
    by_vacancy: dict[str, int]
    by_stage: dict[str, int]
    aggregate: FleetAggregateSummary
    candidates: list[dict[str, Any]]
    review_queue: list[dict[str, Any]]
    apply_results: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "run_id": self.run_id,
            "mode": self.mode,
            "tenant_id": self.tenant_id,
            "vacancy_id": self.vacancy_id,
            "summary": {
                "total_candidates": self.total_candidates,
                "by_migration_category": dict(self.by_migration_category),
                "by_issue_category": dict(self.by_issue_category),
                "by_tenant": dict(self.by_tenant),
                "by_vacancy": dict(self.by_vacancy),
                "by_stage": dict(self.by_stage),
            },
            "aggregate": self.aggregate.to_dict(),
            "candidates": self.candidates,
            "review_queue": self.review_queue,
            "apply_results": self.apply_results,
        }


__all__ = [
    "BatchReport",
    "CandidateApplyResult",
    "CandidateAuditResult",
    "DocumentAuditRow",
    "EvidenceAuditRow",
    "FleetAggregateSummary",
    "IssueCategory",
    "MigrationCategory",
    "MigrationStatus",
    "StageConflictKind",
]
