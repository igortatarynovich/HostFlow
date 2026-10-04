#!/usr/bin/env python3
"""Hiring Stage Authority Consumption guard — LI-1 on the hiring path."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "hiring_stage_authority.py"
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-stage-authority-consumption.md"
PARENT = REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
EXISTENCE = (
    REPO_ROOT / "backend" / "app" / "platform" / "module_stage_registry" / "existence.py"
)


def _load_contract():
    sys.path.insert(0, str(REPO_ROOT))
    from backend.app.reference.hiring_stage_authority import (  # noqa: PLC0415
        CONTRACT_ID,
        EXISTENCE_API,
        FORBIDDEN_IMPLEMENTATION,
        HIRING_PATH_EXISTENCE_CONSUMERS,
        OCCUPANCY_AUTHORITY,
        PARENT_CONTRACT_ID,
        TRANSITION_ORDER,
        TRANSITION_RULE,
        hiring_stage_exists,
        leftover_existence_codes,
    )

    return {
        "CONTRACT_ID": CONTRACT_ID,
        "EXISTENCE_API": EXISTENCE_API,
        "FORBIDDEN_IMPLEMENTATION": FORBIDDEN_IMPLEMENTATION,
        "HIRING_PATH_EXISTENCE_CONSUMERS": HIRING_PATH_EXISTENCE_CONSUMERS,
        "OCCUPANCY_AUTHORITY": OCCUPANCY_AUTHORITY,
        "PARENT_CONTRACT_ID": PARENT_CONTRACT_ID,
        "TRANSITION_ORDER": TRANSITION_ORDER,
        "TRANSITION_RULE": TRANSITION_RULE,
        "hiring_stage_exists": hiring_stage_exists,
        "leftover_existence_codes": leftover_existence_codes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    for path in (CONTRACT, ARCH_DOC, PARENT, BRIEF, EXISTENCE):
        if not path.is_file():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    contract = _load_contract()
    if contract["CONTRACT_ID"] != "hiring_stage_authority.v1":
        print("contract id must be hiring_stage_authority.v1", file=sys.stderr)
        return 1
    if contract["PARENT_CONTRACT_ID"] != "hiring_acceptance.v1":
        print("parent must remain hiring_acceptance.v1", file=sys.stderr)
        return 1
    if contract["EXISTENCE_API"] != "is_stage_registered":
        print("existence API must be is_stage_registered", file=sys.stderr)
        return 1
    if contract["OCCUPANCY_AUTHORITY"] != "candidate_stage":
        print("occupancy must remain candidate_stage", file=sys.stderr)
        return 1
    if contract["TRANSITION_RULE"] != "forward_moves_guarded_jumps_rejected":
        print("transition rule must be forward_moves_guarded_jumps_rejected", file=sys.stderr)
        return 1

    order = contract["TRANSITION_ORDER"]
    if len(order) != len(set(order)):
        print("TRANSITION_ORDER must be unique", file=sys.stderr)
        return 1
    missing = [key for key in order if not contract["hiring_stage_exists"](key)]
    if missing:
        print("TRANSITION_ORDER keys not registered: " + ", ".join(missing), file=sys.stderr)
        return 1

    leftovers = contract["leftover_existence_codes"]()
    if leftovers != (
        "static_new_to_hired_list",
        "tenant_candidate_stages_dictionary",
        "funnel_stages_as_existence",
    ):
        print(f"leftover existence set drifted: {leftovers}", file=sys.stderr)
        return 1

    required_forbidden = (
        "new_stage_machine",
        "he3_collapse_in_this_pr",
        "rs7_execution",
        "min_hr_handoff",
        "li2_lifecycle_cutover",
        "funnel_ui_rework",
    )
    missing_forbidden = [
        item for item in required_forbidden if item not in contract["FORBIDDEN_IMPLEMENTATION"]
    ]
    if missing_forbidden:
        print("forbidden list missing: " + ", ".join(missing_forbidden), file=sys.stderr)
        return 1

    helpers = REPO_ROOT / "backend" / "app" / "api" / "v1" / "candidates" / "helpers.py"
    helpers_text = helpers.read_text(encoding="utf-8")
    if "FunnelStage" in helpers_text:
        print("hiring-path helpers must not query FunnelStage for existence", file=sys.stderr)
        return 1
    if "resolve_hiring_stage_key" not in helpers_text:
        print("helpers must consume resolve_hiring_stage_key", file=sys.stderr)
        return 1
    if "assert_hiring_stage_transition" not in helpers_text:
        print("helpers must consume assert_hiring_stage_transition", file=sys.stderr)
        return 1

    consumer_markers = {
        "backend/app/api/v1/candidates/helpers.py": (
            "resolve_hiring_stage_key",
            "assert_hiring_stage_transition",
        ),
        "backend/app/api/v1/candidates/service.py": (
            "resolve_writable_stage_code",
            "_validate_stage_transition",
        ),
        "backend/app/services/candidate_doc_pipeline_guard.py": (
            "hiring_stage_exists",
        ),
    }
    for rel, markers in consumer_markers.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            print(f"missing hiring-path consumer: {rel}", file=sys.stderr)
            return 1
        text = path.read_text(encoding="utf-8")
        missing_markers = [item for item in markers if item not in text]
        if missing_markers:
            print(f"{rel} must consume LI-1 existence: missing {missing_markers}", file=sys.stderr)
            return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    lowered = arch.lower()
    required = (
        "hiring_stage_authority.v1",
        "is_stage_registered",
        "candidate.stage",
        "forward_moves_guarded_jumps_rejected",
        "funnel",
        "not a new hiring product",
        "jump",
    )
    missing_arch = [item for item in required if item not in lowered]
    if missing_arch:
        print("architecture SoT missing: " + ", ".join(missing_arch), file=sys.stderr)
        return 1
    if "Stage Authority Consumption Gate" not in arch:
        print("architecture SoT must name Stage Authority Consumption Gate", file=sys.stderr)
        return 1

    print("Hiring Stage Authority Consumption boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
