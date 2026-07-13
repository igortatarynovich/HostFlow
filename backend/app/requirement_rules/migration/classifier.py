"""Migration category classifier (ADR-018 PR 2B-4)."""

from __future__ import annotations

from backend.app.requirement_rules.migration.contracts import (
    CandidateAuditResult,
    IssueCategory,
    MigrationCategory,
    MigrationStatus,
)


def classify_migration_category(
    *,
    issue_categories: set[IssueCategory],
    policy_resolvable: bool,
    policy_pinned_and_valid: bool,
    stage_inconsistent: bool,
    has_ambiguous_documents: bool,
    has_unclassified: bool,
    has_unknown_legacy: bool,
    has_standard_evidence: bool,
    has_supersede_eligible_evidence: bool,
    citizenship_unresolved: bool,
    citizenship_conflict: bool,
    residency_unresolved: bool,
    evaluation_runtime_error: bool,
    evaluation_input_incomplete: bool,
    policy_context_unresolved: bool,
    document_contract_invalid: bool,
    document_data_incomplete: bool,
    document_version_unresolved: bool,
    code95_validity_unresolved: bool,
    all_participating_docs_contract_ready: bool,
) -> tuple[MigrationCategory, str, MigrationStatus]:
    if evaluation_runtime_error:
        return (
            MigrationCategory.needs_classification,
            "Fix evaluation runtime error before migration",
            MigrationStatus.review_required,
        )

    if not policy_resolvable or policy_context_unresolved:
        return (
            MigrationCategory.needs_policy_assignment,
            "Assign requirement policy manually (vacancy/profile/work country missing)",
            MigrationStatus.review_required,
        )

    if stage_inconsistent:
        if IssueCategory.stage_data_corruption_or_missing in issue_categories:
            return (
                MigrationCategory.stage_inconsistency,
                "Stage/data corruption — high priority review (no auto rollback)",
                MigrationStatus.review_required,
            )
        return (
            MigrationCategory.stage_inconsistency,
            "Historical stage permitted under old policy — compliance review (no auto rollback)",
            MigrationStatus.review_required,
        )

    if document_version_unresolved or has_ambiguous_documents or has_unclassified or has_unknown_legacy:
        return (
            MigrationCategory.needs_classification,
            "Operator must resolve document classification/version before auto-migration",
            MigrationStatus.review_required,
        )

    if citizenship_conflict:
        return (
            MigrationCategory.needs_classification,
            "Resolve conflicting citizenship sources before auto-migration",
            MigrationStatus.review_required,
        )

    if citizenship_unresolved or residency_unresolved or evaluation_input_incomplete:
        return (
            MigrationCategory.needs_classification,
            "Resolve citizenship/residency/evaluation input before auto-migration",
            MigrationStatus.review_required,
        )

    if (
        document_data_incomplete
        or document_contract_invalid
        or code95_validity_unresolved
        or not all_participating_docs_contract_ready
    ):
        return (
            MigrationCategory.needs_classification,
            "DocumentData contract incomplete — cannot auto-migrate",
            MigrationStatus.review_required,
        )

    blocking_issues = issue_categories - {
        IssueCategory.manual_evidence_present,
        IssueCategory.policy_missing,
    }
    needs_work = bool(blocking_issues or has_supersede_eligible_evidence)

    if not needs_work and policy_pinned_and_valid and all_participating_docs_contract_ready:
        return (
            MigrationCategory.clean,
            "No migration required",
            MigrationStatus.skipped,
        )

    if (
        needs_work
        and not stage_inconsistent
        and policy_resolvable
        and all_participating_docs_contract_ready
        and not document_version_unresolved
        and not document_data_incomplete
        and not document_contract_invalid
        and not code95_validity_unresolved
        and not citizenship_conflict
    ):
        return (
            MigrationCategory.safe_auto_migration,
            "Eligible for safe auto-migration (full DocumentData + policy contract)",
            MigrationStatus.pending,
        )

    return (
        MigrationCategory.needs_classification,
        "Manual review required",
        MigrationStatus.review_required,
    )


def apply_classification_to_audit(audit: CandidateAuditResult) -> CandidateAuditResult:
    issue_set = set(audit.issue_categories)
    has_ambiguous = any(
        d.version_assignment_status == "ambiguous"
        or (d.is_unclassified or d.canonical_type_code in {"other", "unclassified"})
        for d in audit.documents
    )
    version_unresolved = IssueCategory.document_version_unresolved in issue_set
    participating_ready = all(
        (not d.missing_type_version_id or d.resolvable_version_id)
        and d.schema_valid
        for d in audit.documents
        if d.canonical_type_code not in {"unclassified", "other", "additional_document"}
        and d.review_status.lower() == "approved"
    ) if audit.documents else True

    category, action, status = classify_migration_category(
        issue_categories=issue_set,
        policy_resolvable=bool(audit.resolved_policy_ref and audit.policy_valid),
        policy_pinned_and_valid=bool(
            audit.policy_pinned and audit.policy_valid and audit.requirement_policy_ref
        ),
        stage_inconsistent={
            IssueCategory.stage_historical_permitted_now_stricter,
            IssueCategory.stage_data_corruption_or_missing,
        }.intersection(issue_set),
        has_ambiguous_documents=has_ambiguous,
        has_unclassified=IssueCategory.unclassified_document in issue_set,
        has_unknown_legacy=any(
            d.has_legacy_type and d.canonical_type_code == "other" for d in audit.documents
        ),
        has_standard_evidence=IssueCategory.manual_evidence_present in issue_set,
        has_supersede_eligible_evidence=any(e.supersede_eligible for e in audit.evidence_rows),
        citizenship_unresolved=IssueCategory.citizenship_unresolved in issue_set,
        citizenship_conflict=IssueCategory.citizenship_conflict in issue_set,
        residency_unresolved=IssueCategory.residency_unresolved in issue_set,
        evaluation_runtime_error=IssueCategory.evaluation_runtime_error in issue_set,
        evaluation_input_incomplete=IssueCategory.evaluation_input_incomplete in issue_set,
        policy_context_unresolved=IssueCategory.policy_context_unresolved in issue_set,
        document_contract_invalid=IssueCategory.document_contract_invalid in issue_set,
        document_data_incomplete=IssueCategory.document_data_incomplete in issue_set,
        document_version_unresolved=version_unresolved,
        code95_validity_unresolved=IssueCategory.code95_validity_unresolved in issue_set,
        all_participating_docs_contract_ready=participating_ready,
    )
    audit.migration_category = category
    audit.recommended_action = action
    audit.migration_status = status
    return audit


__all__ = ["apply_classification_to_audit", "classify_migration_category"]
