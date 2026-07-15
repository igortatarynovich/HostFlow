#!/usr/bin/env python3
"""ADR-018 PR 2B-4 — Candidate Evaluation Audit & Migration Tool.

Fleet-wide audit and safe batch migration for pre-ADR-018 candidates.

Usage examples:

  # Dry-run audit for one tenant
  python3 backend/scripts/migrate_candidate_adr018_evaluation.py \\
    --audit-only --tenant-id <uuid> --export-report /tmp/adr018-audit.json

  # Single candidate (legacy flags still supported)
  python3 backend/scripts/migrate_candidate_adr018_evaluation.py \\
    --candidate-id <uuid> --tenant-id <uuid> --dry-run

  # Apply safe auto-migration only
  python3 backend/scripts/migrate_candidate_adr018_evaluation.py \\
    --tenant-id <uuid> --apply --only-safe --export-report /tmp/adr018-apply.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT.parent))

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.requirement_rules.migration.apply import apply_candidate_migration
from backend.app.requirement_rules.migration.batch_runner import run_batch
from backend.app.requirement_rules.migration.candidate_auditor import audit_candidate


def _parse_candidate_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(",", " ").split() if p.strip()]
    return parts or None


async def _run_single(
    *,
    tenant_id: str,
    candidate_id: str,
    target_stage: str,
    dry_run: bool,
    apply: bool,
) -> dict:
    async with async_session_maker() as db:
        candidate = await db.get(Candidate, candidate_id)
        if not candidate or str(candidate.tenant_id) != tenant_id:
            raise SystemExit("Candidate not found for tenant")

        audit = await audit_candidate(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
            target_stage=target_stage,
        )
        report: dict = {"audit": audit.to_dict()}

        if apply and not dry_run:
            apply_result = await apply_candidate_migration(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                audit=audit,
                dry_run=False,
                target_stage=target_stage,
            )
            await db.commit()
            report["apply"] = apply_result.to_dict()
        elif apply:
            apply_result = await apply_candidate_migration(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                audit=audit,
                dry_run=True,
                target_stage=target_stage,
            )
            report["apply"] = apply_result.to_dict()

        return report


async def _run_batch_cli(args: argparse.Namespace) -> dict:
    async with async_session_maker() as db:
        report = await run_batch(
            db,
            tenant_id=args.tenant_id,
            vacancy_id=args.vacancy_id,
            candidate_ids=_parse_candidate_ids(args.candidate_ids),
            target_stage=args.target_stage,
            audit_only=args.audit_only and not args.apply,
            apply=args.apply,
            only_safe=args.only_safe,
            dry_run=not args.apply or args.dry_run,
            limit=args.limit,
            resume_checkpoint=Path(args.resume) if args.resume else None,
        )
        return report.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ADR-018 Candidate Evaluation Audit & Migration Tool (PR 2B-4)",
    )
    parser.add_argument("--tenant-id", help="Scope to tenant UUID")
    parser.add_argument("--vacancy-id", help="Scope to vacancy UUID")
    parser.add_argument("--candidate-id", help="Single candidate UUID (legacy)")
    parser.add_argument(
        "--candidate-ids",
        help="Comma/space-separated candidate UUIDs for batch",
    )
    parser.add_argument("--target-stage", default="permit_ordered")
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Audit without applying changes (default for batch)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate apply without writes")
    parser.add_argument("--apply", action="store_true", help="Apply safe migration steps")
    parser.add_argument(
        "--only-safe",
        action="store_true",
        help="Apply only safe_auto_migration category",
    )
    parser.add_argument("--limit", type=int, help="Max candidates per batch run")
    parser.add_argument(
        "--resume",
        help="Checkpoint JSON path for resumable batch",
    )
    parser.add_argument(
        "--export-report",
        help="Write JSON report to path",
    )
    args = parser.parse_args()

    batch_mode = bool(args.tenant_id or args.vacancy_id or args.candidate_ids) and not (
        args.candidate_id and not args.tenant_id
    )

    if args.candidate_id:
        if not args.tenant_id:
            raise SystemExit("--tenant-id required with --candidate-id")
        payload = asyncio.run(
            _run_single(
                tenant_id=args.tenant_id,
                candidate_id=args.candidate_id,
                target_stage=args.target_stage,
                dry_run=args.dry_run or not args.apply,
                apply=args.apply,
            )
        )
    elif batch_mode or args.audit_only:
        if not args.tenant_id and not args.candidate_ids and args.apply:
            raise SystemExit("Batch mode requires --tenant-id or --candidate-ids")
        payload = asyncio.run(_run_batch_cli(args))
    else:
        raise SystemExit(
            "Specify --candidate-id + --tenant-id, or batch scope (--tenant-id / --candidate-ids)",
        )

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.export_report:
        Path(args.export_report).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
