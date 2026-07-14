"""Batch orchestration for ADR-018 fleet migration."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.migration.apply import apply_candidate_migration
from backend.app.requirement_rules.migration.candidate_auditor import audit_candidate
from backend.app.requirement_rules.migration.contracts import (
    BatchReport,
    FleetAggregateSummary,
    IssueCategory,
    MigrationCategory,
)
from backend.app.requirement_rules.migration.redaction import redact_candidate_audit
from backend.app.requirement_rules.migration.review_queue import build_review_queue_entries


async def _load_candidates(
    db: AsyncSession,
    *,
    tenant_id: Optional[str],
    vacancy_id: Optional[str],
    candidate_ids: Optional[Sequence[str]],
    limit: Optional[int],
    resume_after_id: Optional[str],
) -> list[Candidate]:
    if candidate_ids:
        q = select(Candidate).where(
            Candidate.id.in_(list(candidate_ids)),
            Candidate.deleted_at.is_(None),
        )
        if tenant_id:
            q = q.where(Candidate.tenant_id == tenant_id)
        result = await db.execute(q.order_by(Candidate.id))
        return list(result.scalars())

    q = select(Candidate).where(Candidate.deleted_at.is_(None))
    if tenant_id:
        q = q.where(Candidate.tenant_id == tenant_id)
    if vacancy_id:
        q = q.where(Candidate.vacancy_id == vacancy_id)
    if resume_after_id:
        q = q.where(Candidate.id > resume_after_id)
    q = q.order_by(Candidate.id)
    if limit:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars())


def _load_checkpoint(path: Optional[Path]) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_checkpoint(path: Optional[Path], payload: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _previous_fingerprint(candidate: Candidate) -> Optional[str]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    if not isinstance(extra, dict):
        return None
    marker = extra.get("adr018_migration")
    if isinstance(marker, dict):
        fp = marker.get("input_fingerprint")
        return str(fp) if fp else None
    return None


def _build_aggregate(
    audits: list[Any],
    *,
    by_tenant: dict[str, int],
) -> FleetAggregateSummary:
    by_policy: Counter[str] = Counter()
    legacy_codes: Counter[str] = Counter()
    missing_fields: Counter[str] = Counter()
    blocking: Counter[str] = Counter()

    without_policy = 0
    legacy_aliases = 0
    unclassified = 0
    no_version = 0
    invalid_data = 0
    manual_evidence = 0
    citizenship = 0
    citizenship_conflict = 0
    residency = 0
    stage_conflict = 0
    eval_runtime = 0
    eval_input = 0
    policy_context = 0
    doc_contract = 0
    code95_unresolved = 0
    eval_error = 0
    safe = 0
    policy_blocked = 0

    for audit in audits:
        policy_key = audit.resolved_policy_ref or audit.requirement_policy_ref or "(unresolved)"
        by_policy[policy_key] += 1
        issues = set(audit.issue_categories)

        if IssueCategory.policy_missing in issues:
            without_policy += 1
        if audit.migration_category == MigrationCategory.needs_policy_assignment:
            policy_blocked += 1
        if IssueCategory.legacy_document_type in issues:
            legacy_aliases += 1
            for doc in audit.documents:
                if doc.has_legacy_type:
                    legacy_codes[doc.stored_doc_type] += 1
        if IssueCategory.unclassified_document in issues:
            unclassified += 1
        if IssueCategory.document_version_unresolved in issues or any(
            d.missing_type_version_id for d in audit.documents
        ):
            no_version += 1
        if IssueCategory.document_data_incomplete in issues:
            invalid_data += 1
        if IssueCategory.manual_evidence_present in issues:
            manual_evidence += 1
        if IssueCategory.citizenship_unresolved in issues:
            citizenship += 1
        if IssueCategory.citizenship_conflict in issues:
            citizenship_conflict += 1
        if IssueCategory.residency_unresolved in issues:
            residency += 1
        if {
            IssueCategory.stage_historical_permitted_now_stricter,
            IssueCategory.stage_data_corruption_or_missing,
        }.intersection(issues):
            stage_conflict += 1
        if IssueCategory.evaluation_runtime_error in issues:
            eval_runtime += 1
        if IssueCategory.evaluation_input_incomplete in issues:
            eval_input += 1
        if IssueCategory.policy_context_unresolved in issues:
            policy_context += 1
        if IssueCategory.document_contract_invalid in issues:
            doc_contract += 1
        if IssueCategory.code95_validity_unresolved in issues:
            code95_unresolved += 1
        if IssueCategory.evaluation_error in issues:
            eval_error += 1
        if audit.migration_category == MigrationCategory.safe_auto_migration:
            safe += 1
        for field in audit.missing_metadata_fields:
            missing_fields[field] += 1
        for req in audit.blocking_requirements:
            blocking[req] += 1

    return FleetAggregateSummary(
        total_candidates=len(audits),
        by_tenant=dict(by_tenant),
        by_policy=dict(by_policy),
        without_policy=without_policy,
        with_legacy_aliases=legacy_aliases,
        with_unclassified=unclassified,
        without_document_type_version=no_version,
        with_invalid_document_data=invalid_data,
        with_standard_manual_evidence=manual_evidence,
        citizenship_unresolved=citizenship,
        citizenship_conflict=citizenship_conflict,
        residency_unresolved=residency,
        stage_conflict=stage_conflict,
        evaluation_runtime_error=eval_runtime,
        evaluation_input_incomplete=eval_input,
        policy_context_unresolved=policy_context,
        document_contract_invalid=doc_contract,
        code95_validity_unresolved=code95_unresolved,
        evaluation_error=eval_error,
        safe_auto_migration=safe,
        top_legacy_document_codes=dict(legacy_codes.most_common(20)),
        top_missing_metadata_fields=dict(missing_fields.most_common(20)),
        top_blocking_requirements=dict(blocking.most_common(20)),
        policy_assignment_blocked=policy_blocked,
    )


async def run_batch(
    db: AsyncSession,
    *,
    tenant_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    candidate_ids: Optional[Sequence[str]] = None,
    target_stage: Optional[str] = None,
    audit_only: bool = True,
    apply: bool = False,
    only_safe: bool = False,
    dry_run: bool = True,
    limit: Optional[int] = None,
    resume_checkpoint: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> BatchReport:
    checkpoint = _load_checkpoint(resume_checkpoint)
    resume_after_id = checkpoint.get("last_candidate_id")
    seen_issue_ids: set[str] = set(checkpoint.get("seen_issue_ids") or [])
    effective_run_id = run_id or str(checkpoint.get("run_id") or uuid4())

    candidates = await _load_candidates(
        db,
        tenant_id=tenant_id,
        vacancy_id=vacancy_id,
        candidate_ids=candidate_ids,
        limit=limit,
        resume_after_id=str(resume_after_id) if resume_after_id else None,
    )

    mode = "audit_only" if audit_only and not apply else ("dry_run" if dry_run else "apply")
    candidate_rows: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    apply_results: list[dict[str, Any]] = []
    audit_objects: list[Any] = []
    by_migration: Counter[str] = Counter()
    by_issue: Counter[str] = Counter()
    by_tenant: Counter[str] = Counter()
    by_vacancy: Counter[str] = Counter()
    by_stage: Counter[str] = Counter()

    last_id: Optional[str] = None
    for candidate in candidates:
        cid = str(candidate.id)
        tid = str(candidate.tenant_id)
        if tenant_id and tid != tenant_id:
            continue

        prev_fp = _previous_fingerprint(candidate)
        audit = await audit_candidate(
            db,
            tenant_id=tid,
            candidate=candidate,
            target_stage=target_stage,
        )
        audit_objects.append(audit)
        candidate_rows.append(redact_candidate_audit(audit.to_dict()))
        by_migration[audit.migration_category.value] += 1
        by_tenant[tid] += 1
        by_vacancy[audit.vacancy_id or "(none)"] += 1
        by_stage[audit.current_stage or "(none)"] += 1
        for issue in audit.issue_categories:
            by_issue[issue.value] += 1

        review_entries = build_review_queue_entries(
            audit,
            run_id=effective_run_id,
            previous_fingerprint=prev_fp,
        )
        for review_entry in review_entries:
            if review_entry.issue_id not in seen_issue_ids:
                seen_issue_ids.add(review_entry.issue_id)
                review_queue.append(review_entry.to_dict())

        should_apply = apply and audit.migration_category == MigrationCategory.safe_auto_migration
        if only_safe and should_apply and audit.migration_category != MigrationCategory.safe_auto_migration:
            should_apply = False
        if should_apply and not audit_only:
            apply_result = await apply_candidate_migration(
                db,
                tenant_id=tid,
                candidate=candidate,
                audit=audit,
                dry_run=dry_run,
                target_stage=target_stage,
                run_id=effective_run_id,
            )
            apply_results.append(apply_result.to_dict())
            if not dry_run:
                await db.commit()
                await db.refresh(candidate)

        last_id = cid
        if resume_checkpoint:
            _save_checkpoint(
                resume_checkpoint,
                {
                    "run_id": effective_run_id,
                    "last_candidate_id": last_id,
                    "processed_count": len(candidate_rows),
                    "seen_issue_ids": sorted(seen_issue_ids),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    aggregate = _build_aggregate(audit_objects, by_tenant=dict(by_tenant))

    return BatchReport(
        generated_at=datetime.now(timezone.utc),
        run_id=effective_run_id,
        mode=mode,
        tenant_id=tenant_id,
        vacancy_id=vacancy_id,
        total_candidates=len(candidate_rows),
        by_migration_category=dict(by_migration),
        by_issue_category=dict(by_issue),
        by_tenant=dict(by_tenant),
        by_vacancy=dict(by_vacancy),
        by_stage=dict(by_stage),
        aggregate=aggregate,
        candidates=candidate_rows,
        review_queue=review_queue,
        apply_results=apply_results,
    )


__all__ = ["run_batch"]
