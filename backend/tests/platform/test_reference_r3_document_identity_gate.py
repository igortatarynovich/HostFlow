"""Reference R3 — Document Identity Gate.

Existence SoT is document-type-registry-v1.json only. Seed and
DOCUMENT_TYPES_CANONICAL are projections. definitions.py canonical_ref_code
subseteq registry. Q3.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from backend.app.document_types.registry import canonical_codes, registry_entries
from backend.app.reference.legal_document_catalogs import DOCUMENT_TYPES_CANONICAL
from backend.app.services.document_reference_sync import SYSTEM_CODES

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_CHECK = _REPO_ROOT / "backend" / "scripts" / "check_document_type_registry.py"


def test_r3_seed_equals_registry() -> None:
    codes = canonical_codes()
    assert SYSTEM_CODES == set(codes)
    assert "id_card" not in SYSTEM_CODES
    assert "national_identity_card" in SYSTEM_CODES
    assert {item.code for item in DOCUMENT_TYPES_CANONICAL} == codes
    assert len(registry_entries()) == len(codes)


def test_r3_definitions_canonical_ref_subseteq_registry() -> None:
    codes = canonical_codes()
    for definition in DOCUMENT_TYPE_DEFINITIONS:
        assert definition.canonical_ref_code in codes, definition.code


def test_r3_registry_check_script() -> None:
    result = subprocess.run(
        [sys.executable, str(_CHECK)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_r3_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference R3 Document Identity Gate" in ci
    assert "test_reference_r3_document_identity_gate.py" in ci
    lint_at = ci.index("- name: Lint")
    r3_at = ci.index("Reference R3 Document Identity Gate")
    assert r3_at < lint_at


def test_r3_gate_filename() -> None:
    assert Path(__file__).name == "test_reference_r3_document_identity_gate.py"
