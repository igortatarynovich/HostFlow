"""Entity Field Composition CL1 — inventory gate.

Observed Candidate composition for driver_ce path; no identity canonization.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCANNER = _REPO_ROOT / "scripts" / "entity_field_composition" / "cl1_candidate_inventory.py"
_INVENTORY = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl1-inventory.tsv"
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl1-candidate-inventory.md"


def test_cl1_inventory_artifact_exists() -> None:
    assert _INVENTORY.is_file()
    text = _INVENTORY.read_text(encoding="utf-8")
    assert "candidate_profile.config.field_configs" in text
    assert "candidate_profile.config.document_configs" in text
    assert "entity_profile.manifest" in text
    assert "screening_as_required_observed" in text


def test_cl1_inventory_scanner_check() -> None:
    result = subprocess.run(
        [sys.executable, str(_SCANNER), "--check"],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl1_brief_exists() -> None:
    assert _BRIEF.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "observe" in brief.lower()
    assert "does not canonize" in brief.lower()
