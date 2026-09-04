"""Mapping Authority Contract Gate (MA-1).

One operator question. One write. Twelve classified answerers.
Feat locked. Not MA-2 runtime. Not External Intake. Not Hiring E2E.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.reference.mapping_authority import (
    ANSWERERS,
    BINDING_STATES,
    CONTRACT_ID,
    DESTINATION_VOCABULARY,
    FORBIDDEN_ON_UNCERTAINTY,
    HEALTH_STATES,
    OPERATOR_QUESTION,
    UNCERTAINTY_OUTCOMES,
    WRITE_API,
    WRITE_AUTHORITY,
    WRITE_PRODUCER_REL,
    classified_codes,
    write_authority_answerers,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "mapping-authority-contract.md"
_ADR021 = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "ADR-021-unified-intake-resolution-model.md"
)
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_mapping_authority_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PRODUCER = _REPO_ROOT / WRITE_PRODUCER_REL
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"


def test_ma1_gate_filename() -> None:
    assert Path(__file__).name == "test_mapping_authority_contract_gate.py"


def test_ma1_contract_id_and_write() -> None:
    assert CONTRACT_ID == "mapping_authority.v1"
    assert WRITE_AUTHORITY == "intake_source_profile_mapping_rules"
    assert WRITE_API == "validate_intake_mapping_rules_write"
    assert DESTINATION_VOCABULARY == "qualified_code"
    assert "which incoming answer writes which canonical entity field" in OPERATOR_QUESTION
    writers = write_authority_answerers()
    assert len(writers) == 1
    assert writers[0].code == "intake_source_profile_mapping_rules"
    assert classified_codes() == (
        "intake_source_profile_mapping_rules",
        "meta_lead_form_mappings",
        "meta_lead_settings_field_mapping",
        "silent_precedence_chain",
        "meta_leads_admin_ui",
        "c5_and_intake_form_editors",
        "mapping_applied_v1_diagnostics",
        "cl6_flight_map",
        "sales_convert_mapping_v1",
        "ocr_and_telegram_bootstrap",
        "dual_vocabulary_and_hardcoded_extractors",
        "lead_criteria_and_forms_answers",
    )
    assert len(ANSWERERS) == 12
    assert BINDING_STATES == ("mapped", "ignored", "unmapped")
    assert HEALTH_STATES == ("valid", "needs_review", "invalid")
    assert UNCERTAINTY_OUTCOMES == ("needs_info", "review_required")
    assert FORBIDDEN_ON_UNCERTAINTY == "no_fit"
    assert f"def {WRITE_API}(" in _PRODUCER.read_text(encoding="utf-8")


def test_ma1_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert CONTRACT_ID in text
    assert "**Write authority**" in text
    assert "intake_source_profiles" in text
    assert "option map" in text.lower()
    assert "Schema ≠ sample" in text or "schema ≠ sample" in text.lower()
    assert "Mapped" in text and "Ignored" in text and "Unmapped" in text
    assert "Needs review" in text
    assert "never** `no_fit`" in text.lower() or "Never** `no_fit`" in text or "**Never** `no_fit`" in text
    assert "thirteenth write" in text.lower()
    assert "Field Registry" in text
    assert "qualified_code" in text
    assert "CL6" in text
    assert "convert_mapping" in text or "Sales" in text
    assert "lead_criteria_v1" in text
    assert "Zapier" in text or "fourth store" in text.lower()


def test_ma1_brief_contract_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Mapping Authority Contract Gate" in text
    assert "mapping-authority-contract.md" in text
    assert CONTRACT_ID in text or "mapping_authority.v1" in text
    assert "**PASS**" in text
    assert "feat locked" in text.lower()
    assert "MA-2" in text
    assert "option map" in text.lower()
    assert "Field Registry" in text
    assert "no_fit" in text
    assert "External Intake" in text
    assert "Hiring E2E" in text


def test_ma1_queue_names_successor_not_runtime() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    assert "Mapping Authority Contract Gate" in text
    assert "mapping-authority-contract.md" in text
    assert "**Active Product** | **[MA-2](mapping-authority.md)**" in text
    assert "Active (Product):** **[MA-2](mapping-authority.md)**" in text
    assert "feat locked this PR" in text
    assert "Active (Product):** **[MA-1](mapping-authority.md)**" not in text
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "mapping-authority.md" in agents
    assert "MA-2" in agents
    assert "mapping-authority-contract.md" in agents or "mapping_authority" in agents.lower()
    lowered = text.lower()
    assert "not mapping feat" in lowered or "not** mapping feat" in lowered or "feat locked" in lowered
    assert "CL8" in text


def test_ma1_leaves_intake_hiring_hr_queued() -> None:
    for path in (_HIRING, _INTAKE, _HR):
        text = path.read_text(encoding="utf-8")
        assert "**QUEUED**" in text
        assert "not scheduled" in text.lower()
        assert "MA-2" in text


def test_ma1_adr021_points_at_authority() -> None:
    text = _ADR021.read_text(encoding="utf-8")
    assert "mapping-authority-contract.md" in text
    assert "mapping_authority.v1" in text or "MA-1" in text


def test_ma1_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_ma1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Mapping Authority Contract Gate" in ci
    assert "test_mapping_authority_contract_gate.py" in ci
    assert "docs/specs/tasks/mapping-authority.md" in ci
    assert "docs/specs/architecture/mapping-authority-contract.md" in ci
