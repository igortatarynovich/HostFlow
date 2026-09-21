#!/usr/bin/env python3
"""Hiring Acceptance Contract guard — nine walk steps, sealed disposition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "hiring_acceptance.py"
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"

EXPECTED_STEPS = 9
EXPECTED_ELIGIBILITY = 10


def _load_contract():
    sys.path.insert(0, str(REPO_ROOT))
    from backend.app.reference.hiring_acceptance import (  # noqa: PLC0415
        ADMISSIBLE_EVIDENCE,
        CLOSED_ROLES,
        CONTRACT_ID,
        ELIGIBILITY_ANSWERERS,
        EVIDENCE_DISPOSITION,
        FORBIDDEN_IMPLEMENTATION,
        INADMISSIBLE_EVIDENCE,
        INADMISSIBLE_EVIDENCE_PATHS,
        STAGE_EXISTENCE_LEFTOVERS,
        WALK_STEPS,
        authority_steps,
        walk_step_codes,
    )

    return {
        "ADMISSIBLE_EVIDENCE": ADMISSIBLE_EVIDENCE,
        "CLOSED_ROLES": CLOSED_ROLES,
        "CONTRACT_ID": CONTRACT_ID,
        "ELIGIBILITY_ANSWERERS": ELIGIBILITY_ANSWERERS,
        "EVIDENCE_DISPOSITION": EVIDENCE_DISPOSITION,
        "FORBIDDEN_IMPLEMENTATION": FORBIDDEN_IMPLEMENTATION,
        "INADMISSIBLE_EVIDENCE": INADMISSIBLE_EVIDENCE,
        "INADMISSIBLE_EVIDENCE_PATHS": INADMISSIBLE_EVIDENCE_PATHS,
        "STAGE_EXISTENCE_LEFTOVERS": STAGE_EXISTENCE_LEFTOVERS,
        "WALK_STEPS": WALK_STEPS,
        "authority_steps": authority_steps,
        "walk_step_codes": walk_step_codes,
    }


def _check_paths(label: str, paths: tuple[str, ...]) -> int:
    for rel in paths:
        path = REPO_ROOT / rel
        if not path.exists():
            print(f"{label} path missing: {rel}", file=sys.stderr)
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    if not CONTRACT.is_file():
        print(f"missing contract: {CONTRACT}", file=sys.stderr)
        return 1
    if not ARCH_DOC.is_file():
        print(f"missing architecture SoT: {ARCH_DOC}", file=sys.stderr)
        return 1
    if not BRIEF.is_file():
        print(f"missing Hiring brief: {BRIEF}", file=sys.stderr)
        return 1

    contract = _load_contract()
    steps = contract["WALK_STEPS"]
    if len(steps) != EXPECTED_STEPS:
        print(f"expected {EXPECTED_STEPS} walk steps, found {len(steps)}", file=sys.stderr)
        return 1

    codes = list(contract["walk_step_codes"]())
    if len(codes) != len(set(codes)):
        print("duplicate walk step codes", file=sys.stderr)
        return 1

    for step in steps:
        if step.authority_role not in contract["CLOSED_ROLES"]:
            print(f"unknown HE role: {step.code}={step.authority_role}", file=sys.stderr)
            return 1
        if _check_paths(step.code, step.authority_paths) != 0:
            return 1

    if len(contract["ELIGIBILITY_ANSWERERS"]) != EXPECTED_ELIGIBILITY:
        print(
            f"expected {EXPECTED_ELIGIBILITY} eligibility answerers, "
            f"found {len(contract['ELIGIBILITY_ANSWERERS'])}",
            file=sys.stderr,
        )
        return 1

    for row in (
        *contract["ELIGIBILITY_ANSWERERS"],
        *contract["STAGE_EXISTENCE_LEFTOVERS"],
    ):
        if row.role not in contract["CLOSED_ROLES"]:
            print(f"unknown HE role: {row.code}={row.role}", file=sys.stderr)
            return 1
        if _check_paths(row.code, row.paths) != 0:
            return 1

    if _check_paths("inadmissible", contract["INADMISSIBLE_EVIDENCE_PATHS"]) != 0:
        return 1

    if contract["EVIDENCE_DISPOSITION"] != "candidate_evidence_binds_document_link":
        print("disposition must be candidate_evidence_binds_document_link", file=sys.stderr)
        return 1

    required_forbidden = (
        "new_hiring_product",
        "new_stage_machine",
        "funnel_builder",
        "workflow_engine",
        "min_hr_handoff",
        "rs7_execution",
        "he2_runtime_in_this_pr",
        "he3_collapse_in_this_pr",
    )
    missing_forbidden = [
        item for item in required_forbidden if item not in contract["FORBIDDEN_IMPLEMENTATION"]
    ]
    if missing_forbidden:
        print("forbidden list missing: " + ", ".join(missing_forbidden), file=sys.stderr)
        return 1

    if "seed_documents_for_ready_for_handoff" not in contract["INADMISSIBLE_EVIDENCE"]:
        print("inadmissible list must name seed_documents_for_ready_for_handoff", file=sys.stderr)
        return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    if contract["CONTRACT_ID"] not in arch:
        print("architecture SoT must name the contract id", file=sys.stderr)
        return 1
    lowered = arch.lower()
    required = (
        "candidate_evidence_binds_document_link",
        "is_stage_registered",
        "requirement_policy_authority",
        "document link",
        "seed_documents_for_ready_for_handoff",
        "not a new hiring product",
        "ready_for_employment.v1",
        "tenth walk step",
    )
    missing = [item for item in required if item not in lowered]
    if missing:
        print("architecture SoT missing required contract shape: " + ", ".join(missing), file=sys.stderr)
        return 1

    print("Hiring Acceptance Contract boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
