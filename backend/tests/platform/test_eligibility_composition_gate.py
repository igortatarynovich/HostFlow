"""Eligibility Composition Gate (HE-3).

One composed decision. Requirement conjunct is the RPM result.
v1 and v2 are not eligibility authorities. Not RS-7. Not min HR.
Not a HE-2 stage-authority change.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.reference.hiring_acceptance import (
    CONTRACT_ID as HE1_CONTRACT_ID,
    EVIDENCE_DISPOSITION,
    WALK_STEPS,
)
from backend.app.reference.hiring_eligibility_composition import (
    CLASSIFIED_ANSWERER_CODES,
    CONTRACT_ID,
    ENGINE_SPLIT,
    FORBIDDEN_IMPLEMENTATION,
    PARENT_CONTRACT_ID,
    REQUIREMENT_CONJUNCT_API,
    REQUIREMENT_CONJUNCT_SOURCE,
    compose_hiring_eligibility,
    neutral_conjuncts,
)
from backend.app.reference.hiring_stage_authority import (
    EXISTENCE_API,
    TRANSITION_RULE,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-eligibility-composition.md"
_PARENT = _REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_hiring_eligibility_composition_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_RESOLVER = _REPO_ROOT / "backend" / "app" / "services" / "transfer_policy_resolver.py"


def test_he3_gate_filename() -> None:
    assert Path(__file__).name == "test_eligibility_composition_gate.py"


def test_he3_contract_consumes_he1_and_rpm() -> None:
    assert CONTRACT_ID == "hiring_eligibility_composition.v1"
    assert PARENT_CONTRACT_ID == HE1_CONTRACT_ID == "hiring_acceptance.v1"
    assert REQUIREMENT_CONJUNCT_SOURCE == "rpm_result"
    assert REQUIREMENT_CONJUNCT_API == "r5_required_set"
    assert ENGINE_SPLIT == "v1_and_v2_not_eligibility_authorities"
    assert len(CLASSIFIED_ANSWERER_CODES) == 10
    assert "requirement_rules_v1" in CLASSIFIED_ANSWERER_CODES
    assert "requirement_rules_v2" in CLASSIFIED_ANSWERER_CODES
    assert "rs7_execution" in FORBIDDEN_IMPLEMENTATION
    assert "min_hr_handoff" in FORBIDDEN_IMPLEMENTATION
    assert "new_hiring_policy_authority" in FORBIDDEN_IMPLEMENTATION
    assert "he2_stage_authority_change" in FORBIDDEN_IMPLEMENTATION
    assert "evidence_disposition_reopen" in FORBIDDEN_IMPLEMENTATION
    assert "inherited_dr1_mapping_red_fix" in FORBIDDEN_IMPLEMENTATION
    step = {row.code: row for row in WALK_STEPS}["eligibility_decision"]
    assert step.authority_role == "consume"
    assert step.later_slice == "none"
    assert step.authority == "hiring_eligibility_composition_v1"
    assert EVIDENCE_DISPOSITION == "candidate_evidence_binds_document_link"
    assert EXISTENCE_API == "is_stage_registered"
    assert TRANSITION_RULE == "forward_moves_guarded_jumps_rejected"


def test_he3_one_refusal_and_rpm_only_requirement() -> None:
    neutral = neutral_conjuncts()
    ok = compose_hiring_eligibility(
        rpm_required=frozenset({"passport"}),
        rpm_unmet=frozenset(),
        conjuncts=neutral,
    )
    assert ok.allowed is True
    assert ok.refusal_reason is None

    missing = compose_hiring_eligibility(
        rpm_required=frozenset({"passport", "visa"}),
        rpm_unmet=frozenset({"visa", "passport"}),
        conjuncts=neutral,
    )
    assert missing.allowed is False
    assert missing.refusal_reason == "Required documents are missing: passport, visa"
    assert missing.requirement_source == "rpm_result"

    both = dict(neutral)
    both["workforce_packs"] = (False, "Workforce eligibility blocks transfer")
    requirement_wins = compose_hiring_eligibility(
        rpm_required=frozenset({"passport"}),
        rpm_unmet=frozenset({"passport"}),
        conjuncts=both,
    )
    assert requirement_wins.refusal_reason == "Required document is missing: passport"

    with pytest.raises(ValueError, match="outside RPM"):
        compose_hiring_eligibility(
            rpm_required=frozenset({"passport"}),
            rpm_unmet=frozenset({"hiring_local_type"}),
            conjuncts=neutral,
        )

    ignored = dict(neutral)
    ignored["requirement_rules_v1"] = (False, "v1 blocks")
    ignored["requirement_rules_v2"] = (False, "v2 blocks")
    ignored["legacy_doc_type_blockers"] = (False, "legacy blocks")
    assert compose_hiring_eligibility(
        rpm_required=frozenset(),
        rpm_unmet=frozenset(),
        conjuncts=ignored,
    ).allowed is True


def test_he3_resolver_consumes_composer() -> None:
    text = _RESOLVER.read_text(encoding="utf-8")
    assert "compose_hiring_eligibility" in text
    assert "rpm_unmet" in text
    assert "r5_required_set" in text
    assert "evaluate_candidate_requirements_v2" not in text
    assert "refusal_reason" in text


def test_he3_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert "Eligibility Composition Gate" in text
    assert CONTRACT_ID in text
    assert "r5_required_set" in text
    assert "not a new hiring product" in text.lower()
    assert "candidate_evidence_binds_document_link" in text
    parent = _PARENT.read_text(encoding="utf-8")
    assert "hiring-eligibility-composition.md" in parent


def test_he3_brief_and_queue() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "Eligibility Composition Gate" in current
    assert "**PASS**" in current
    assert "hiring-eligibility-composition.md" in current
    assert "feat locked" in current.lower()
    assert "min HR" in current or "minimal" in current.lower()
    assert "not a new hiring product" in current.lower()
    queue = _QUEUE.read_text(encoding="utf-8")
    header = queue.split("## 8. History", 1)[0]
    assert "**Active Product** | **[HE-3](hiring-workflow-e2e.md)**" in header
    assert "Eligibility Composition Gate **PASS**" in header
    assert "Stage Authority Consumption Gate **PASS**" in header
    assert "Hiring Acceptance Contract Gate **PASS**" in header
    assert "RS-7" in header
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "HE-3" in agents
    assert "hiring_eligibility_composition" in agents or "Eligibility Composition" in agents


def test_he3_leaves_hr_queued() -> None:
    text = _HR.read_text(encoding="utf-8")
    header = text.split("## History", 1)[0] if "## History" in text else text
    assert "**QUEUED**" in header
    assert "not scheduled" in header.lower()


def test_he3_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_he3_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Eligibility Composition Gate" in ci
    assert "test_eligibility_composition_gate.py" in ci
    assert "docs/specs/architecture/hiring-eligibility-composition.md" in ci
