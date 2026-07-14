"""Per-candidate ADR-018 migration audit."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.constants.stages_adapter import PIPELINE_SEQUENCE
from backend.app.document_hub.document_data_contract import build_document_data_contract_from_hub_row
from backend.app.document_types.schema_registry import validate_document_data
from backend.app.document_types.registry import is_canonical_code, is_runtime_alias, normalize_input_doc_type
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.requirement_rules.evaluation.candidate_bridge import evaluate_candidate_requirements_v2
from backend.app.requirement_rules.evaluation.result_contract import RequirementEvaluationStatus
from backend.app.requirement_rules.migration.classifier import apply_classification_to_audit
from backend.app.requirement_rules.migration.contracts import (
    CandidateAuditResult,
    DocumentAuditRow,
    EvidenceAuditRow,
    IssueCategory,
    MigrationCategory,
    MigrationStatus,
    StageConflictKind,
)
from backend.app.requirement_rules.migration.citizenship_normalizer import assess_citizenship
from backend.app.requirement_rules.migration.document_metadata_adapter import migrate_legacy_document_metadata
from backend.app.requirement_rules.migration.evidence_helpers import (
    ACTIVE_EVIDENCE_STATUSES,
    assess_evidence_supersede_eligibility,
    is_standard_manual_evidence,
)
from backend.app.requirement_rules.requirement_policy_registry import get_requirement_policy
from backend.app.services.document_type_version_assignment_resolver import (
    DocumentTypeVersionAssignmentResolver,
    VersionAssignmentStatus,
)
from backend.app.services.requirement_policy_assignment import resolve_policy_ref_for_candidate

INBOX_TYPES = frozenset({"unclassified", "other", "additional_document"})


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _pipeline_index(stage: str) -> int:
    code = _norm(stage)
    try:
        return PIPELINE_SEQUENCE.index(code)
    except ValueError:
        return -1


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _set_candidate_extra(candidate: Candidate, extra: dict[str, Any]) -> None:
    if hasattr(candidate, "_set_extra"):
        candidate._set_extra(extra)
    else:
        candidate.extra = extra


async def _audit_documents(db: AsyncSession, docs: list[Any]) -> tuple[DocumentAuditRow, ...]:
    rows: list[DocumentAuditRow] = []
    for doc in docs:
        stored = str(getattr(doc, "doc_type", "") or "")
        stored_norm = _norm(stored)
        canonical = normalize_input_doc_type(stored)
        status_raw = getattr(doc, "status", None)
        review_status = status_raw.value if hasattr(status_raw, "value") else str(status_raw or "")
        meta = getattr(doc, "meta", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        migration = migrate_legacy_document_metadata(
            stored_doc_type=stored,
            meta=meta,
            expire_date=getattr(doc, "expire_date", None),
        )
        has_legacy = bool(stored_norm and (is_runtime_alias(stored_norm) or stored_norm != canonical))
        is_unclassified = canonical in INBOX_TYPES or stored_norm in INBOX_TYPES

        version_status: Optional[str] = None
        resolvable_version_id: Optional[str] = None
        missing_version = not bool(getattr(doc, "document_type_version_id", None))

        if not is_unclassified and is_canonical_code(canonical):
            assignment = await DocumentTypeVersionAssignmentResolver.resolve_for_document(
                db,
                doc,
                canonical_type_code=canonical,
            )
            version_status = assignment.status.value
            if assignment.is_assignable:
                resolvable_version_id = assignment.document_type_version_id
                missing_version = False
            elif assignment.status == VersionAssignmentStatus.ambiguous:
                missing_version = True

        schema_valid = True
        schema_errors: tuple[str, ...] = ()
        if migration.document_data:
            schema_valid, schema_errors_list = validate_document_data(canonical, migration.document_data)
            schema_errors = tuple(schema_errors_list)
        elif _norm(review_status) == "approved" and not is_unclassified:
            contract = build_document_data_contract_from_hub_row(doc)
            schema_valid = contract.schema_valid
            schema_errors = contract.schema_errors

        rows.append(
            DocumentAuditRow(
                document_id=str(getattr(doc, "id", "")),
                stored_doc_type=stored,
                canonical_type_code=canonical,
                has_legacy_type=has_legacy,
                is_unclassified=is_unclassified,
                missing_type_version_id=missing_version,
                version_assignment_status=version_status,
                resolvable_version_id=resolvable_version_id,
                schema_valid=schema_valid,
                schema_errors=schema_errors,
                review_status=review_status,
            )
        )
    return tuple(rows)


async def _load_evidence_rows(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> tuple[EvidenceAuditRow, ...]:
    rows = list(
        (
            await db.execute(
                select(CandidateEvidence)
                .options(selectinload(CandidateEvidence.documents))
                .where(
                    CandidateEvidence.tenant_id == tenant_id,
                    CandidateEvidence.candidate_id == candidate_id,
                    CandidateEvidence.status.in_(list(ACTIVE_EVIDENCE_STATUSES)),
                )
            )
        ).scalars()
    )
    out: list[EvidenceAuditRow] = []
    for row in rows:
        status = row.status.value if hasattr(row.status, "value") else str(row.status)
        variant = str(row.evidence_variant_code or "")
        eligible, block_reason = assess_evidence_supersede_eligibility(row)
        out.append(
            EvidenceAuditRow(
                evidence_id=str(row.id),
                requirement_code=str(row.requirement_code),
                evidence_variant_code=variant,
                status=status,
                is_standard=is_standard_manual_evidence(
                    evidence_variant_code=variant,
                    status=status,
                ),
                is_protected=not eligible and block_reason == "protected_variant",
                supersede_eligible=eligible,
                supersede_block_reason=block_reason,
            )
        )
    return tuple(out)


def _detect_stage_inconsistency(
    *,
    current_stage: str,
    pipeline: list[str],
    stage_evaluations: dict[str, Any],
) -> bool:
    current_idx = _pipeline_index(current_stage)
    if current_idx <= 0:
        return False
    for stage_code in pipeline[: current_idx + 1]:
        evaluation = stage_evaluations.get(stage_code)
        if not evaluation:
            continue
        stage_idx = _pipeline_index(stage_code)
        if stage_idx < 0 or stage_idx >= current_idx:
            continue
        for row in evaluation.requirements:
            if row.is_blocking:
                return True
    return False


def _classify_stage_conflict(
    *,
    documents: tuple[DocumentAuditRow, ...],
    document_mismatch: bool,
) -> StageConflictKind:
    approved_participating = [
        d
        for d in documents
        if _norm(d.review_status) == "approved" and d.canonical_type_code not in INBOX_TYPES
    ]
    if document_mismatch or not approved_participating:
        return StageConflictKind.data_corruption_or_missing
    if any(not d.schema_valid or d.missing_type_version_id for d in approved_participating):
        return StageConflictKind.data_corruption_or_missing
    return StageConflictKind.historical_permitted_now_stricter


def _document_evaluation_mismatch(
    *,
    documents: tuple[DocumentAuditRow, ...],
    evaluation: Any,
) -> bool:
    approved_types = {
        _norm(d.canonical_type_code)
        for d in documents
        if _norm(d.review_status) == "approved" and d.canonical_type_code not in INBOX_TYPES
    }
    matched_types: set[str] = set()
    for row in evaluation.requirements:
        if row.status != RequirementEvaluationStatus.fulfilled:
            continue
        for ref in row.matched_documents:
            matched_types.add(_norm(ref.document_type_code))
    if not approved_types:
        return False
    return bool(approved_types - matched_types)


def _collect_missing_metadata(doc_rows: tuple[DocumentAuditRow, ...]) -> tuple[str, ...]:
    fields: set[str] = set()
    for d in doc_rows:
        if _norm(d.review_status) != "approved":
            continue
        for err in d.schema_errors:
            path = str(err).split(":", 1)[0].strip()
            if path and path != "$":
                fields.add(path)
    return tuple(sorted(fields))


async def audit_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    target_stage: Optional[str] = None,
) -> CandidateAuditResult:
    candidate_id = str(candidate.id)
    current_stage = _norm(getattr(candidate, "status", None) or "new")
    pinned_ref = str(getattr(candidate, "requirement_policy_ref", "") or "").strip() or None

    resolved_ref: Optional[str] = None
    try:
        resolved_ref = await resolve_policy_ref_for_candidate(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )
    except Exception:
        resolved_ref = None

    policy_valid = bool(resolved_ref and get_requirement_policy(resolved_ref))
    issues: set[IssueCategory] = set()

    if not pinned_ref:
        issues.add(IssueCategory.policy_missing)
    if resolved_ref and not policy_valid:
        issues.add(IssueCategory.policy_missing)

    if not resolved_ref or not policy_valid:
        issues.add(IssueCategory.policy_context_unresolved)

    docs = await list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        include_deleted=False,
    )

    citizenship_result = assess_citizenship(candidate, documents=docs)
    citizenship = citizenship_result.iso2
    if citizenship_result.status == "conflict":
        issues.add(IssueCategory.citizenship_conflict)
    elif citizenship_result.status == "unresolved":
        issues.add(IssueCategory.citizenship_unresolved)
    elif citizenship_result.is_resolved:
        extra = _candidate_extra(candidate)
        if not extra.get("citizenship"):
            extra = dict(extra)
            extra["citizenship"] = citizenship_result.iso2
            _set_candidate_extra(candidate, extra)

    doc_rows = await _audit_documents(db, docs)
    evidence_rows = await _load_evidence_rows(db, tenant_id=tenant_id, candidate_id=candidate_id)

    for doc in docs:
        meta = getattr(doc, "meta", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        code95_check = migrate_legacy_document_metadata(
            stored_doc_type=str(getattr(doc, "doc_type", "") or ""),
            meta=meta,
            expire_date=getattr(doc, "expire_date", None),
        )
        if code95_check.code95_validity_unresolved:
            issues.add(IssueCategory.code95_validity_unresolved)

    for d in doc_rows:
        if d.is_unclassified:
            issues.add(IssueCategory.unclassified_document)
        elif d.has_legacy_type:
            issues.add(IssueCategory.legacy_document_type)
        if d.version_assignment_status == VersionAssignmentStatus.ambiguous.value or (
            d.missing_type_version_id
            and _norm(d.review_status) == "approved"
            and d.canonical_type_code not in INBOX_TYPES
        ):
            issues.add(IssueCategory.document_version_unresolved)
        if not d.schema_valid and _norm(d.review_status) == "approved":
            issues.add(IssueCategory.document_data_incomplete)
            issues.add(IssueCategory.document_contract_invalid)

    if any(e.is_standard for e in evidence_rows):
        issues.add(IssueCategory.manual_evidence_present)

    evaluator_fingerprint: Optional[str] = None
    evaluator_can_transition: Optional[bool] = None
    blocking_requirements: tuple[str, ...] = ()
    next_blocking: Optional[str] = None
    evaluation_error: Optional[str] = None
    stage_evaluations: dict[str, Any] = {}
    document_mismatch = False
    stage_allowed = True
    stage_conflict_kind: Optional[StageConflictKind] = None

    eval_target = _norm(target_stage) if target_stage else current_stage
    current_idx = _pipeline_index(current_stage)
    stages_to_check: list[str] = []
    if current_idx >= 0:
        stages_to_check = [s for s in PIPELINE_SEQUENCE[: current_idx + 1] if s]
    else:
        stages_to_check = [eval_target]

    try:
        for stage_code in stages_to_check or [eval_target]:
            evaluation = await evaluate_candidate_requirements_v2(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                target_stage=stage_code,
            )
            stage_evaluations[stage_code] = evaluation
        primary_eval = stage_evaluations.get(eval_target) or next(iter(stage_evaluations.values()))
        evaluator_fingerprint = primary_eval.input_fingerprint
        evaluator_can_transition = primary_eval.can_transition
        blocking_requirements = tuple(primary_eval.blocking_requirements)
        next_blocking = blocking_requirements[0] if blocking_requirements else None
        document_mismatch = _document_evaluation_mismatch(documents=doc_rows, evaluation=primary_eval)
    except ValueError as exc:
        message = str(exc).lower()
        evaluation_error = str(exc)
        if "requirement policy" in message or "no requirement policy" in message:
            issues.add(IssueCategory.policy_context_unresolved)
        elif citizenship_result.status == "unresolved":
            issues.add(IssueCategory.evaluation_input_incomplete)
        else:
            issues.add(IssueCategory.evaluation_input_incomplete)
    except Exception as exc:
        issues.add(IssueCategory.evaluation_runtime_error)
        evaluation_error = str(exc)

    if _detect_stage_inconsistency(
        current_stage=current_stage,
        pipeline=list(PIPELINE_SEQUENCE),
        stage_evaluations=stage_evaluations,
    ):
        stage_conflict_kind = _classify_stage_conflict(
            documents=doc_rows,
            document_mismatch=document_mismatch,
        )
        if stage_conflict_kind == StageConflictKind.data_corruption_or_missing:
            issues.add(IssueCategory.stage_data_corruption_or_missing)
        else:
            issues.add(IssueCategory.stage_historical_permitted_now_stricter)
        stage_allowed = False

    if not citizenship and any(
        code in blocking_requirements
        for code in ("legal_stay_confirmation", "labor_market_access")
    ):
        issues.add(IssueCategory.residency_unresolved)

    missing_metadata = _collect_missing_metadata(doc_rows)
    affected_docs = tuple(
        sorted(
            {
                d.document_id
                for d in doc_rows
                if d.is_unclassified
                or d.has_legacy_type
                or not d.schema_valid
                or d.missing_type_version_id
            }
        )
    )

    audit = CandidateAuditResult(
        candidate_id=candidate_id,
        tenant_id=tenant_id,
        vacancy_id=str(getattr(candidate, "vacancy_id", "") or "") or None,
        current_stage=current_stage,
        requirement_policy_ref=pinned_ref,
        resolved_policy_ref=resolved_ref,
        policy_pinned=bool(pinned_ref),
        policy_valid=policy_valid,
        issue_categories=tuple(sorted(issues, key=lambda c: c.value)),
        migration_category=MigrationCategory.clean,
        documents=doc_rows,
        evidence_rows=evidence_rows,
        evaluator_fingerprint=evaluator_fingerprint,
        evaluator_can_transition=evaluator_can_transition,
        blocking_requirements=blocking_requirements,
        next_blocking_requirement=next_blocking,
        stage_allowed_by_policy=stage_allowed,
        stage_conflict_kind=stage_conflict_kind,
        document_evaluation_mismatch=document_mismatch,
        recommended_action="",
        migration_status=MigrationStatus.pending,
        evaluation_error=evaluation_error,
        affected_requirements=blocking_requirements,
        affected_documents=affected_docs,
        missing_metadata_fields=missing_metadata,
    )
    return apply_classification_to_audit(audit)


__all__ = ["audit_candidate"]
