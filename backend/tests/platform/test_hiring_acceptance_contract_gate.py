"""Hiring Acceptance Contract Gate (HE-1).

Nine walk steps. Dual-evidence disposition sealed.
Admissible production evidence named. Forbidden implementation frozen.
HE-2 may consume stage steps. Not HE-3 collapse. Not RS-7. Not min HR.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.reference.hiring_acceptance import (
    ADMISSIBLE_EVIDENCE,
    CONTRACT_ID,
    ELIGIBILITY_ANSWERERS,
    EVIDENCE_DISPOSITION,
    FORBIDDEN_IMPLEMENTATION,
    INADMISSIBLE_EVIDENCE,
    OPERATOR_QUESTION,
    STAGE_EXISTENCE_LEFTOVERS,
    WALK_PHASES,
    WALK_STEPS,
    authority_steps,
    walk_step_codes,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
_ADR016 = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "ADR-016-requirement-evidence-document-separation.md"
)
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_hiring_acceptance_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"


def test_he1_gate_filename() -> None:
    assert Path(__file__).name == "test_hiring_acceptance_contract_gate.py"


def test_he1_contract_id_and_walk() -> None:
    assert CONTRACT_ID == "hiring_acceptance.v1"
    assert "which authority answers each step" in OPERATOR_QUESTION
    assert WALK_PHASES == ("stage", "requirements_docs", "eligibility", "transfer")
    assert walk_step_codes() == (
        "stage_existence",
        "stage_occupancy",
        "stage_transition",
        "requirement_policy",
        "document_request",
        "document_instance",
        "requirement_satisfaction",
        "eligibility_decision",
        "transfer_complete",
    )
    assert len(WALK_STEPS) == 9
    assert EVIDENCE_DISPOSITION == "candidate_evidence_binds_document_link"
    writers = authority_steps()
    assert {step.code for step in writers} >= {
        "stage_existence",
        "stage_occupancy",
        "requirement_policy",
        "document_request",
        "document_instance",
        "requirement_satisfaction",
        "transfer_complete",
    }
    assert len(STAGE_EXISTENCE_LEFTOVERS) == 3
    assert len(ELIGIBILITY_ANSWERERS) == 10
    assert "seed_documents_for_ready_for_handoff" in INADMISSIBLE_EVIDENCE
    assert "candidate_evidence_helpers" in INADMISSIBLE_EVIDENCE
    assert "rs1_operator_configured_tenant" in ADMISSIBLE_EVIDENCE
    assert "new_hiring_product" in FORBIDDEN_IMPLEMENTATION
    assert "rs7_execution" in FORBIDDEN_IMPLEMENTATION
    assert "min_hr_handoff" in FORBIDDEN_IMPLEMENTATION
    assert "he2_runtime_in_this_pr" in FORBIDDEN_IMPLEMENTATION
    assert "he3_collapse_in_this_pr" in FORBIDDEN_IMPLEMENTATION


def test_he1_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert CONTRACT_ID in text
    assert EVIDENCE_DISPOSITION in text
    assert "is_stage_registered" in text
    assert "Document Link" in text
    assert "candidate_evidence" in text.lower() or "Candidate Evidence" in text
    assert "seed_documents_for_ready_for_handoff" in text
    assert "not a new hiring product" in text.lower()
    assert "ready_for_employment.v1" in text
    assert "tenth walk step" in text.lower()
    assert "GET /transfer-readiness" in text or "transfer-readiness" in text
    assert "HE-2" in text
    assert "HE-3" in text
    assert "min HR" in text or "Minimal Recruitment" in text


def test_he1_brief_contract_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    current = text.split("## History", 1)[0]
    assert "Hiring Acceptance Contract Gate" in current
    assert "hiring-acceptance-contract.md" in current
    assert CONTRACT_ID in current or "hiring_acceptance.v1" in current
    assert "**PASS**" in current
    assert "Hiring Acceptance Contract Gate **not PASS**" not in current
    assert "Do not open HE-1 contract seal" not in current
    assert "feat locked" in current.lower()
    assert "HE-2" in current
    assert "hiring-stage-authority-consumption.md" in current or "Stage Authority Consumption" in current
    assert "not a new hiring product" in current.lower()
    assert "seed_documents_for_ready_for_handoff" in current
    assert "min HR" in current or "minimal" in current.lower()


def test_he1_queue_names_pass_not_he3_runtime() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    current = text.split("## 8. History", 1)[0]
    history = text.split("## 8. History", 1)[1]
    assert "Hiring Acceptance Contract Gate" in current
    assert "hiring-acceptance-contract.md" in current
    assert "Hiring Acceptance Contract Gate **PASS**" in current
    assert "Hiring Acceptance Contract Gate **not PASS**" not in current
    assert "Do not open HE-1 contract seal" not in current
    assert "HE-1" in current
    assert "HE-2" in current
    assert "Active Product stays **[HE-1]" in history or "Do not start HE-2" in history
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "hiring-workflow-e2e.md" in agents
    assert "hiring-acceptance-contract.md" in agents or "hiring_acceptance" in agents.lower()
    lowered = current.lower()
    assert "feat locked" in lowered
    assert "CL8" in current
    assert "min hr" in lowered or "minimal recruitment" in lowered


def test_he1_leaves_hr_queued() -> None:
    text = _HR.read_text(encoding="utf-8")
    header = text.split("## History", 1)[0] if "## History" in text else text
    assert "**QUEUED**" in header
    assert "not scheduled" in header.lower()
    assert "hiring-workflow-e2e.md" in header


def test_he1_adr016_points_at_disposition() -> None:
    text = _ADR016.read_text(encoding="utf-8")
    assert "hiring-acceptance-contract.md" in text
    assert "candidate_evidence_binds_document_link" in text or "Hiring Acceptance" in text


def test_he1_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_he1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Hiring Acceptance Contract Gate" in ci
    assert "test_hiring_acceptance_contract_gate.py" in ci
    assert "docs/specs/tasks/hiring-workflow-e2e.md" in ci
    assert "docs/specs/architecture/hiring-acceptance-contract.md" in ci
