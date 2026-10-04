#!/usr/bin/env python3
"""Hiring Eligibility Composition guard — one decision, RPM requirement conjunct."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "hiring_eligibility_composition.py"
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-eligibility-composition.md"
PARENT = REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
RESOLVER = REPO_ROOT / "backend" / "app" / "services" / "transfer_policy_resolver.py"
GUARD = REPO_ROOT / "backend" / "app" / "services" / "candidate_doc_pipeline_guard.py"
STAGE = REPO_ROOT / "backend" / "app" / "reference" / "hiring_stage_authority.py"


def _load_contract():
    sys.path.insert(0, str(REPO_ROOT))
    from backend.app.reference.hiring_eligibility_composition import (  # noqa: PLC0415
        CLASSIFIED_ANSWERER_CODES,
        CONTRACT_ID,
        ENGINE_SPLIT,
        FORBIDDEN_IMPLEMENTATION,
        NOT_ELIGIBILITY_AUTHORITIES,
        PARENT_CONTRACT_ID,
        REQUIREMENT_CONJUNCT_API,
        REQUIREMENT_CONJUNCT_SOURCE,
        compose_hiring_eligibility,
        neutral_conjuncts,
    )

    return {
        "CLASSIFIED_ANSWERER_CODES": CLASSIFIED_ANSWERER_CODES,
        "CONTRACT_ID": CONTRACT_ID,
        "ENGINE_SPLIT": ENGINE_SPLIT,
        "FORBIDDEN_IMPLEMENTATION": FORBIDDEN_IMPLEMENTATION,
        "NOT_ELIGIBILITY_AUTHORITIES": NOT_ELIGIBILITY_AUTHORITIES,
        "PARENT_CONTRACT_ID": PARENT_CONTRACT_ID,
        "REQUIREMENT_CONJUNCT_API": REQUIREMENT_CONJUNCT_API,
        "REQUIREMENT_CONJUNCT_SOURCE": REQUIREMENT_CONJUNCT_SOURCE,
        "compose_hiring_eligibility": compose_hiring_eligibility,
        "neutral_conjuncts": neutral_conjuncts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    for path in (CONTRACT, ARCH_DOC, PARENT, BRIEF, RESOLVER, GUARD, STAGE):
        if not path.is_file():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    contract = _load_contract()
    if contract["CONTRACT_ID"] != "hiring_eligibility_composition.v1":
        print("contract id must be hiring_eligibility_composition.v1", file=sys.stderr)
        return 1
    if contract["PARENT_CONTRACT_ID"] != "hiring_acceptance.v1":
        print("parent must remain hiring_acceptance.v1", file=sys.stderr)
        return 1
    if contract["REQUIREMENT_CONJUNCT_SOURCE"] != "rpm_result":
        print("requirement conjunct must be rpm_result", file=sys.stderr)
        return 1
    if contract["REQUIREMENT_CONJUNCT_API"] != "r5_required_set":
        print("requirement conjunct API must be r5_required_set", file=sys.stderr)
        return 1
    if contract["ENGINE_SPLIT"] != "v1_and_v2_not_eligibility_authorities":
        print("v1/v2 must stay non-authorities", file=sys.stderr)
        return 1
    expected = (
        "transfer_policy_composer",
        "workforce_packs",
        "package_readiness",
        "field_requirements",
        "requirement_rules_v1",
        "requirement_rules_v2",
        "operational_requirements",
        "handoff_routing",
        "pipeline_gates",
        "legacy_doc_type_blockers",
    )
    if contract["CLASSIFIED_ANSWERER_CODES"] != expected:
        print(f"classified answerers drifted: {contract['CLASSIFIED_ANSWERER_CODES']}", file=sys.stderr)
        return 1

    required_forbidden = (
        "new_hiring_policy_authority",
        "rs7_execution",
        "min_hr_handoff",
        "he2_stage_authority_change",
        "evidence_disposition_reopen",
        "inherited_dr1_mapping_red_fix",
        "li2_lifecycle_cutover",
    )
    missing_forbidden = [
        item for item in required_forbidden if item not in contract["FORBIDDEN_IMPLEMENTATION"]
    ]
    if missing_forbidden:
        print("forbidden list missing: " + ", ".join(missing_forbidden), file=sys.stderr)
        return 1

    compose = contract["compose_hiring_eligibility"]
    neutral = contract["neutral_conjuncts"]()
    try:
        compose(
            rpm_required=frozenset({"passport"}),
            rpm_unmet=frozenset({"invented_hiring_type"}),
            conjuncts=neutral,
        )
    except ValueError:
        pass
    else:
        print("composer accepted a required type outside RPM", file=sys.stderr)
        return 1

    refused = compose(
        rpm_required=frozenset({"passport"}),
        rpm_unmet=frozenset({"passport"}),
        conjuncts=neutral,
    )
    if refused.allowed or refused.refusal_reason != "Required document is missing: passport":
        print("RPM unmet must be the single requirement refusal", file=sys.stderr)
        return 1

    v1_fail = dict(neutral)
    v1_fail["requirement_rules_v1"] = (False, "v1 says no")
    v1_fail["requirement_rules_v2"] = (False, "v2 says no")
    v1_fail["legacy_doc_type_blockers"] = (False, "legacy says no")
    ignored = compose(rpm_required=frozenset(), rpm_unmet=frozenset(), conjuncts=v1_fail)
    if not ignored.allowed:
        print("v1/v2/legacy must not answer eligibility", file=sys.stderr)
        return 1

    resolver = RESOLVER.read_text(encoding="utf-8")
    if "compose_hiring_eligibility" not in resolver or "rpm_unmet" not in resolver:
        print("transfer resolver must compose eligibility from the RPM intersection", file=sys.stderr)
        return 1
    if "evaluate_candidate_requirements_v2" in resolver:
        print("transfer resolver must not call requirement rules v2", file=sys.stderr)
        return 1

    guard = GUARD.read_text(encoding="utf-8")
    if "hiring_stage_exists" not in guard:
        print("HE-2 stage existence consumption must stay on the pipeline guard", file=sys.stderr)
        return 1
    if "compose_hiring_eligibility" not in guard or "r5_required_set" not in guard:
        print("legacy doc block must consume the RPM result", file=sys.stderr)
        return 1

    stage = STAGE.read_text(encoding="utf-8")
    if "forward_moves_guarded_jumps_rejected" not in stage:
        print("HE-2 transition rule must stay", file=sys.stderr)
        return 1
    if "is_stage_registered" not in stage:
        print("HE-2 existence API must stay", file=sys.stderr)
        return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    lowered = arch.lower()
    for item in (
        "hiring_eligibility_composition.v1",
        "r5_required_set",
        "rpm_result",
        "not a new hiring product",
        "v1_and_v2_not_eligibility_authorities",
    ):
        if item not in lowered and item not in arch:
            print(f"architecture SoT missing: {item}", file=sys.stderr)
            return 1
    if "Eligibility Composition Gate" not in arch:
        print("architecture SoT must name Eligibility Composition Gate", file=sys.stderr)
        return 1

    print("Hiring Eligibility Composition boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
