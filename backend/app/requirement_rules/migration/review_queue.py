"""Review queue read-model for ADR-018 fleet migration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.requirement_rules.migration.contracts import (
    CandidateAuditResult,
    IssueCategory,
    MigrationStatus,
)
from backend.app.requirement_rules.migration.redaction import occurrence_id, stable_issue_id


@dataclass
class ReviewQueueEntry:
    issue_id: str
    occurrence_id: str
    run_id: str
    candidate_id: str
    tenant_id: str
    current_stage: str
    issue_category: IssueCategory
    affected_source: str
    issue_categories: tuple[IssueCategory, ...]
    affected_requirements: tuple[str, ...]
    affected_documents: tuple[str, ...]
    recommended_action: str
    migration_status: MigrationStatus
    evaluator_fingerprint: Optional[str]
    previous_fingerprint: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "occurrence_id": self.occurrence_id,
            "run_id": self.run_id,
            "candidate_id": self.candidate_id,
            "tenant_id": self.tenant_id,
            "current_stage": self.current_stage,
            "issue_category": self.issue_category.value,
            "affected_source": self.affected_source,
            "issue_categories": [c.value for c in self.issue_categories],
            "affected_requirements": list(self.affected_requirements),
            "affected_documents": list(self.affected_documents),
            "recommended_action": self.recommended_action,
            "migration_status": self.migration_status.value,
            "evaluator_fingerprint": self.evaluator_fingerprint,
            "previous_fingerprint": self.previous_fingerprint,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


def _affected_source_for_issue(
    issue: IssueCategory,
    audit: CandidateAuditResult,
) -> str:
    if issue == IssueCategory.legacy_document_type:
        legacy_docs = sorted(
            d.document_id for d in audit.documents if d.has_legacy_type
        )
        return ",".join(legacy_docs[:5])
    if issue in {
        IssueCategory.document_data_incomplete,
        IssueCategory.document_contract_invalid,
        IssueCategory.document_version_unresolved,
        IssueCategory.unclassified_document,
        IssueCategory.code95_validity_unresolved,
    }:
        doc_ids = sorted(audit.affected_documents)
        return ",".join(doc_ids[:5])
    if issue in {
        IssueCategory.residency_unresolved,
        IssueCategory.evaluation_input_incomplete,
        IssueCategory.evaluation_runtime_error,
    }:
        return ",".join(audit.blocking_requirements[:3])
    return ""


def build_review_queue_entries(
    audit: CandidateAuditResult,
    *,
    run_id: str,
    previous_fingerprint: Optional[str] = None,
) -> list[ReviewQueueEntry]:
    if audit.migration_status not in {
        MigrationStatus.review_required,
        MigrationStatus.failed,
    }:
        return []
    if not audit.issue_categories:
        return []

    created = datetime.now(timezone.utc)
    categories = tuple(audit.issue_categories)
    entries: list[ReviewQueueEntry] = []
    for issue in categories:
        affected_source = _affected_source_for_issue(issue, audit)
        issue_id = stable_issue_id(
            candidate_id=audit.candidate_id,
            issue_category=issue.value,
            affected_source=affected_source,
        )
        entries.append(
            ReviewQueueEntry(
                issue_id=issue_id,
                occurrence_id=occurrence_id(run_id=run_id, issue_id=issue_id),
                run_id=run_id,
                candidate_id=audit.candidate_id,
                tenant_id=audit.tenant_id,
                current_stage=audit.current_stage,
                issue_category=issue,
                affected_source=affected_source,
                issue_categories=categories,
                affected_requirements=audit.affected_requirements,
                affected_documents=audit.affected_documents,
                recommended_action=audit.recommended_action,
                migration_status=audit.migration_status,
                evaluator_fingerprint=audit.evaluator_fingerprint,
                previous_fingerprint=previous_fingerprint,
                created_at=created,
            )
        )
    return entries


def build_review_queue_entry(
    audit: CandidateAuditResult,
    *,
    run_id: str,
    previous_fingerprint: Optional[str] = None,
) -> Optional[ReviewQueueEntry]:
    """Backward-compatible single entry — returns first issue only."""
    entries = build_review_queue_entries(
        audit,
        run_id=run_id,
        previous_fingerprint=previous_fingerprint,
    )
    return entries[0] if entries else None


__all__ = ["ReviewQueueEntry", "build_review_queue_entries", "build_review_queue_entry"]
