"""Apply ADR-018 safe migration steps for a single candidate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.document_hub.document_data_contract import build_document_data_contract_from_hub_row
from backend.app.document_types.registry import is_runtime_alias, normalize_input_doc_type
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.enums import CandidateEvidenceStatus
from backend.app.modules.documents.crud import list_candidate_documents
from backend.app.requirement_rules.evaluation.candidate_bridge import evaluate_candidate_requirements_v2
from backend.app.requirement_rules.migration.contracts import (
    CandidateApplyResult,
    CandidateAuditResult,
    MigrationCategory,
)
from backend.app.requirement_rules.migration.citizenship_normalizer import (
    apply_citizenship_normalization,
    assess_citizenship,
)
from backend.app.requirement_rules.migration.document_metadata_adapter import migrate_legacy_document_metadata
from backend.app.requirement_rules.migration.evidence_helpers import (
    ACTIVE_EVIDENCE_STATUSES,
    assess_evidence_supersede_eligibility,
)
from backend.app.services.document_type_version_assignment_resolver import (
    DocumentTypeVersionAssignmentResolver,
)
from backend.app.services.requirement_policy_assignment import pin_requirement_policy

MIGRATION_VERSION = "2B-4.2"
SUPERSEDE_REASON = "ADR-018 fleet migration supersede (standard document flow replaced by evaluation)"
INBOX_TYPES = frozenset({"unclassified", "other", "additional_document"})


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _set_candidate_extra(candidate: Candidate, extra: dict[str, Any]) -> None:
    if hasattr(candidate, "_set_extra"):
        candidate._set_extra(extra)
    else:
        candidate.extra = extra


def _write_minimal_migration_marker(
    candidate: Candidate,
    *,
    run_id: str,
    fingerprint: str,
    status: str,
) -> None:
    extra = _candidate_extra(candidate)
    extra["adr018_migration"] = {
        "migration_version": MIGRATION_VERSION,
        "status": status,
        "input_fingerprint": fingerprint,
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
    }
    _set_candidate_extra(candidate, extra)


async def _supersede_eligible_evidence(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    dry_run: bool,
) -> int:
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
    count = 0
    for row in rows:
        eligible, block_reason = assess_evidence_supersede_eligibility(row)
        if not eligible:
            continue
        count += 1
        if dry_run:
            continue
        source_link = f"candidate_evidence:{row.id}"
        row.status = CandidateEvidenceStatus.superseded.value
        row.rejection_reason = f"{SUPERSEDE_REASON}; source={source_link}; reason=standard_flow_replaced"
        await db.flush()
    return count


def _normalize_document_row(doc: Any, *, dry_run: bool) -> tuple[bool, bool]:
    """Return (type_normalized, metadata_migrated)."""
    stored = str(getattr(doc, "doc_type", "") or "")
    stored_norm = _norm(stored)
    canonical = normalize_input_doc_type(stored)
    type_changed = False
    meta_changed = False

    if canonical in INBOX_TYPES or stored_norm in INBOX_TYPES:
        return False, False

    if stored_norm != canonical and (is_runtime_alias(stored_norm) or stored_norm != canonical):
        if not dry_run:
            doc.doc_type = canonical
        type_changed = True

    meta = getattr(doc, "meta", None) or {}
    if not isinstance(meta, dict):
        meta = {}

    migration = migrate_legacy_document_metadata(
        stored_doc_type=stored,
        meta=meta,
        expire_date=getattr(doc, "expire_date", None),
    )
    if migration.document_data:
        existing = meta.get("document_data")
        if not isinstance(existing, dict) or existing != migration.document_data:
            if not dry_run:
                meta = dict(meta)
                meta["document_data"] = dict(migration.document_data)
                doc.meta = meta
            meta_changed = True
    elif not meta.get("document_data"):
        contract = build_document_data_contract_from_hub_row(doc)
        if contract.document_data:
            if not dry_run:
                meta = dict(meta)
                meta["document_data"] = dict(contract.document_data)
                doc.meta = meta
            meta_changed = True

    return type_changed, meta_changed


async def _assign_document_versions(
    db: AsyncSession,
    docs: list[Any],
    *,
    dry_run: bool,
) -> int:
    assigned = 0
    for doc in docs:
        canonical = normalize_input_doc_type(getattr(doc, "doc_type", ""))
        if canonical in INBOX_TYPES:
            continue
        assignment = await DocumentTypeVersionAssignmentResolver.resolve_for_document(
            db,
            doc,
            canonical_type_code=canonical,
        )
        if not assignment.is_assignable:
            continue
        if str(getattr(doc, "document_type_version_id", "") or "") == assignment.document_type_version_id:
            continue
        assigned += 1
        if dry_run:
            continue
        if assignment.document_type_id:
            doc.document_type_id = assignment.document_type_id
        doc.document_type_version_id = assignment.document_type_version_id
        await db.flush()
    return assigned


async def apply_candidate_migration(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    audit: CandidateAuditResult,
    dry_run: bool = True,
    target_stage: Optional[str] = None,
    run_id: Optional[str] = None,
) -> CandidateApplyResult:
    candidate_id = str(candidate.id)
    steps: list[str] = []

    if audit.migration_category not in {
        MigrationCategory.safe_auto_migration,
        MigrationCategory.clean,
    }:
        return CandidateApplyResult(
            candidate_id=candidate_id,
            applied=False,
            dry_run=dry_run,
            policy_ref=audit.resolved_policy_ref,
            superseded_evidence_count=0,
            normalized_documents_count=0,
            metadata_migrated_count=0,
            version_assigned_count=0,
            input_fingerprint=audit.evaluator_fingerprint,
            run_id=run_id,
            steps=[],
            error=f"not eligible: {audit.migration_category.value}",
        )

    policy_ref = audit.resolved_policy_ref
    if not policy_ref:
        return CandidateApplyResult(
            candidate_id=candidate_id,
            applied=False,
            dry_run=dry_run,
            policy_ref=None,
            superseded_evidence_count=0,
            normalized_documents_count=0,
            metadata_migrated_count=0,
            version_assigned_count=0,
            input_fingerprint=None,
            run_id=run_id,
            error="no resolvable policy_ref",
        )

    if audit.migration_category == MigrationCategory.clean:
        return CandidateApplyResult(
            candidate_id=candidate_id,
            applied=False,
            dry_run=dry_run,
            policy_ref=policy_ref,
            superseded_evidence_count=0,
            normalized_documents_count=0,
            metadata_migrated_count=0,
            version_assigned_count=0,
            input_fingerprint=audit.evaluator_fingerprint,
            run_id=run_id,
            steps=["already_clean"],
        )

    pinned = str(getattr(candidate, "requirement_policy_ref", "") or "").strip()
    if pinned != policy_ref:
        if not dry_run:
            await pin_requirement_policy(db, candidate=candidate, policy_ref=policy_ref, force=False)
        steps.append("pin_policy")

    docs = await list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        include_deleted=False,
    )

    citizenship_result = assess_citizenship(candidate, documents=docs)
    if apply_citizenship_normalization(candidate, citizenship_result, dry_run=dry_run):
        steps.append("normalize_citizenship")

    normalized_count = 0
    metadata_count = 0
    for doc in docs:
        type_changed, meta_changed = _normalize_document_row(doc, dry_run=dry_run)
        if type_changed:
            normalized_count += 1
        if meta_changed:
            metadata_count += 1
    if normalized_count:
        steps.append("normalize_document_types")
    if metadata_count:
        steps.append("migrate_metadata_to_document_data")

    version_assigned = await _assign_document_versions(db, docs, dry_run=dry_run)
    if version_assigned:
        steps.append("assign_document_type_versions")

    superseded = await _supersede_eligible_evidence(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        dry_run=dry_run,
    )
    if superseded:
        steps.append("supersede_standard_manual_evidence")

    eval_stage = _norm(target_stage or audit.current_stage or "new")
    fingerprint: Optional[str] = None
    effective_run_id = run_id or "local"
    if not dry_run:
        await db.flush()
        evaluation = await evaluate_candidate_requirements_v2(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
            target_stage=eval_stage,
        )
        fingerprint = evaluation.input_fingerprint
        _write_minimal_migration_marker(
            candidate,
            run_id=effective_run_id,
            fingerprint=fingerprint,
            status="migrated",
        )
        await db.flush()
    else:
        fingerprint = audit.evaluator_fingerprint
        steps.append("recalculate_evaluation")

    return CandidateApplyResult(
        candidate_id=candidate_id,
        applied=not dry_run,
        dry_run=dry_run,
        policy_ref=policy_ref,
        superseded_evidence_count=superseded,
        normalized_documents_count=normalized_count,
        metadata_migrated_count=metadata_count,
        version_assigned_count=version_assigned,
        input_fingerprint=fingerprint,
        run_id=effective_run_id,
        steps=steps,
    )


__all__ = ["apply_candidate_migration", "MIGRATION_VERSION", "SUPERSEDE_REASON"]
