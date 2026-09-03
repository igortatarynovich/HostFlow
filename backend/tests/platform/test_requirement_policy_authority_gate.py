"""Requirement Policy Authority Gate (RPM-1).

One operator question. One write. Nine classified answerers.
Feat locked. Not Overlay rewrite. Not Mapping. Not Hiring E2E.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.reference.document_policy_merge import merge_resolved_policy
from backend.app.reference.requirement_policy_authority import (
    ANSWERERS,
    CONTRACT_ID,
    OPERATOR_QUESTION,
    WRITE_AUTHORITY,
    WRITE_MERGE_API,
    WRITE_PRODUCER_REL,
    classified_codes,
    write_authority_answerers,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "requirement-policy-authority.md"
_ADR018 = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "ADR-018-requirement-policy-evaluation-model.md"
)
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = (
    _REPO_ROOT
    / "scripts"
    / "architecture"
    / "check_requirement_policy_authority_boundary.py"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PRODUCER = _REPO_ROOT / WRITE_PRODUCER_REL


def test_rpm1_contract_id_and_write() -> None:
    assert CONTRACT_ID == "requirement_policy_authority.v1"
    assert WRITE_AUTHORITY == "r5_merge_pack_tenant_delta"
    assert WRITE_MERGE_API == "merge_resolved_policy"
    assert "must this candidate provide document type X?" in OPERATOR_QUESTION
    writers = write_authority_answerers()
    assert len(writers) == 1
    assert writers[0].code == "r5_pack_tenant_delta"
    assert classified_codes() == (
        "r5_pack_tenant_delta",
        "vacancy_overlay_screening",
        "leftover_sample_ruleset",
        "hub_document_pack_definitions",
        "db_ref_packs_transfer",
        "adr018_engine_packs",
        "document_applicability_policy",
        "hiring_pipeline_gates",
        "document_policies_table",
    )
    assert len(ANSWERERS) == 9
    resolved = merge_resolved_policy()
    assert resolved["candidate"]["defaults"]["requiredTypes"]


def test_rpm1_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert CONTRACT_ID in text
    assert "**Write authority**" in text
    assert "r5_pack_tenant_delta" not in text or "R5 pack" in text
    assert "nine rows" in text.lower() or "Nine" in text
    assert "Vacancy Overlay" in text
    assert "tenth write" in text.lower()
    assert "Hub packages" in text
    assert "Documents Admin" in text
    assert "CL8" in text
    assert "Mapping" in text
    assert "Hiring E2E" in text
    assert "lead_criteria_v1" in text
    assert "tenth write" in text.lower()


def test_rpm1_brief_authority_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Requirement Policy Authority Gate" in text
    assert "requirement-policy-authority.md" in text
    assert CONTRACT_ID in text or "requirement_policy_authority.v1" in text
    assert "**PASS**" in text
    assert "feat locked" in text.lower() or "Feat locked" in text
    assert "RPM-2" in text
    assert "lead_criteria_v1" in text
    assert "tenth write" in text.lower()
    assert "Mapping Authority" in text or "mapping-authority.md" in text
    assert "operator action" in text
    assert "tenant_delta" in text
    assert "merge_resolved_policy" in text
    assert "D4" in text
    assert "Result / Why / Facts" in text or "Result / Why" in text


def test_rpm1_adr018_points_at_authority() -> None:
    text = _ADR018.read_text(encoding="utf-8")
    assert "requirement-policy-authority.md" in text
    assert "Admin UI for policy editing" in text
    assert "RPM" in text


def test_rpm1_queue_names_successor_not_mapping() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    assert "Requirement Policy Authority Gate" in text
    assert "requirement-policy-authority.md" in text
    assert "RPM-2" in text
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "requirement-policy-management.md" in agents
    lowered = text.lower()
    assert "not mapping" in lowered or "Mapping not auto-scheduled" in text
    assert "CL8" in text


def test_rpm1_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    source = _PRODUCER.read_text(encoding="utf-8")
    assert f"def {WRITE_MERGE_API}(" in source


def test_rpm1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Authority Gate" in ci
    assert "test_requirement_policy_authority_gate.py" in ci
    assert "docs/specs/tasks/requirement-policy-management.md" in ci
    assert "docs/specs/architecture/requirement-policy-authority.md" in ci


def test_rpm1_gate_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_authority_gate.py"
