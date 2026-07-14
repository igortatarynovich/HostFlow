#!/usr/bin/env python3
"""Compare ADR-018 fleet dry-run reports (baseline vs post-normalization)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metrics(report: dict[str, Any]) -> dict[str, int]:
    agg = report.get("aggregate") or {}
    candidates = report.get("candidates") or []
    issue_counts: Counter[str] = Counter()
    for row in candidates:
        for cat in row.get("issue_categories") or []:
            issue_counts[str(cat)] += 1
    legacy_aliases = sum(
        1
        for row in candidates
        if any(doc.get("has_legacy_type") for doc in (row.get("documents") or []))
    )
    return {
        "total_candidates": int(report.get("total") or len(candidates)),
        "safe_auto_migration": int(agg.get("safe_auto_migration") or 0),
        "citizenship_unresolved": int(issue_counts.get("citizenship_unresolved", 0)),
        "evaluation_runtime_error": int(issue_counts.get("evaluation_runtime_error", 0)),
        "evaluation_error": int(issue_counts.get("evaluation_error", 0)),
        "legacy_aliases": int(agg.get("with_legacy_aliases") or legacy_aliases),
        "schema_invalid_approved": int(issue_counts.get("document_contract_invalid", 0)),
        "stage_conflicts": int(agg.get("stage_conflict") or issue_counts.get("stage_inconsistency", 0)),
        "policy_unresolved": int(
            issue_counts.get("policy_context_unresolved", 0) + issue_counts.get("policy_missing", 0)
        ),
        "citizenship_conflict": int(issue_counts.get("citizenship_conflict", 0)),
    }


def _candidate_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["candidate_id"]): row for row in report.get("candidates") or []}


def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-018 fleet delta report")
    parser.add_argument("--baseline", required=True, help="Baseline fleet JSON report")
    parser.add_argument("--current", required=True, help="Current fleet JSON report")
    parser.add_argument("--out", required=True, help="Output delta JSON path")
    args = parser.parse_args()

    baseline_report = _load(Path(args.baseline))
    current_report = _load(Path(args.current))
    baseline = _metrics(baseline_report)
    current = _metrics(current_report)
    metric_delta = {key: current.get(key, 0) - baseline.get(key, 0) for key in set(baseline) | set(current)}

    base_idx = _candidate_index(baseline_report)
    cur_idx = _candidate_index(current_report)
    category_moves: Counter[str] = Counter()
    fingerprint_changed: list[str] = []
    for cid, cur_row in cur_idx.items():
        base_row = base_idx.get(cid)
        if not base_row:
            continue
        bcat = base_row.get("migration_category")
        ccat = cur_row.get("migration_category")
        if bcat != ccat:
            category_moves[f"{bcat}_to_{ccat}"] += 1
        if base_row.get("evaluator_fingerprint") != cur_row.get("evaluator_fingerprint"):
            fingerprint_changed.append(cid)

    former_safe = [
        cid
        for cid, row in base_idx.items()
        if row.get("migration_category") == "safe_auto_migration"
        and cur_idx.get(cid, {}).get("migration_category") != "safe_auto_migration"
    ]

    payload = {
        "baseline_metrics": baseline,
        "current_metrics": current,
        "metric_delta": metric_delta,
        "category_moves": dict(category_moves),
        "fingerprint_changed_count": len(fingerprint_changed),
        "former_safe_candidates": former_safe,
    }
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
