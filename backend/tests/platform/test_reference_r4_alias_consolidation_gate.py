"""Reference R4 — Alias Consolidation Gate.

Scanner, UI equivalence, and legacy normalization paths use
document-type-legacy-aliases-v1.json only. Proof: Q4.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

from backend.app.document_types.registry import normalize_input_doc_type
from backend.app.services.document_type_canonical_bridge import normalize_legacy_doc_type
from backend.app.services.scanner_presets import get_preset_for_doc_type

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_ALIASES_JSON = _REPO_ROOT / "docs" / "specs" / "platform" / "document-type-legacy-aliases-v1.json"
_BRIDGE = _REPO_ROOT / "backend" / "app" / "services" / "document_type_canonical_bridge.py"
_SCANNER_PRESETS = _REPO_ROOT / "backend" / "app" / "services" / "scanner_presets.py"
_CONSTANTS = _REPO_ROOT / "hostflow-frontend" / "src" / "modules" / "documents" / "constants.ts"
_ALIASES_TS = _REPO_ROOT / "hostflow-frontend" / "src" / "data" / "documentTypeAliases.ts"
_CODEGEN = _REPO_ROOT / "scripts" / "codegen" / "generate_document_type_aliases.py"
_SOT = _REPO_ROOT / "docs" / "specs" / "tasks" / "platform-reference-identity-sot.md"


def test_r4_q4_residence_permit_equals_residence_card() -> None:
    assert normalize_input_doc_type("residence_permit") == "residence_card"
    assert normalize_legacy_doc_type("residence_permit") == "residence_card"
    preset = get_preset_for_doc_type("residence_permit")
    assert preset.code in {"residence_card", "residence_permit"}


def test_r4_bridge_delegates_to_alias_registry() -> None:
    source = _BRIDGE.read_text(encoding="utf-8")
    assert "SUPPLEMENTAL_LEGACY_TO_REF" not in source
    assert "normalize_input_doc_type" in source
    assert normalize_legacy_doc_type("tacho_card") == "tachograph_card"
    assert normalize_legacy_doc_type("code95") == "driver_qualification_card"


def test_r4_scanner_presets_no_local_alias_map() -> None:
    source = _SCANNER_PRESETS.read_text(encoding="utf-8")
    assert "normalize_input_doc_type" in source
    assert "mapping = {" not in source
    tree = ast.parse(source)
    func = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "get_preset_for_doc_type"
    )
    assigns = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "mapping" for t in node.targets)
    ]
    assert assigns == []


def test_r4_frontend_aliases_generated_from_json() -> None:
    constants = _CONSTANTS.read_text(encoding="utf-8")
    aliases_ts = _ALIASES_TS.read_text(encoding="utf-8")
    assert "documentTypeAliases" in constants
    assert "document-type-legacy-aliases-v1.json" in aliases_ts
    assert '"residence_permit": "residence_card"' in aliases_ts
    assert "residence_card: \"residence_permit\"" not in constants
    assert '["passport", "national_id", "eu_driver_license_code95"]' not in constants


def test_r4_alias_codegen_script() -> None:
    result = subprocess.run(
        [sys.executable, str(_CODEGEN), "--check"],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_r4_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference R4 Alias Consolidation Gate" in ci
    assert "test_reference_r4_alias_consolidation_gate.py" in ci
    r3_at = ci.index("Reference R3 Document Identity Gate")
    r4_at = ci.index("Reference R4 Alias Consolidation Gate")
    lint_at = ci.index("- name: Lint")
    assert r3_at < r4_at < lint_at


def test_r4_gate_filename_and_sot_reference() -> None:
    assert Path(__file__).name == "test_reference_r4_alias_consolidation_gate.py"
    sot = _SOT.read_text(encoding="utf-8")
    assert "document-type-legacy-aliases-v1.json" in sot
    assert _ALIASES_JSON.exists()
