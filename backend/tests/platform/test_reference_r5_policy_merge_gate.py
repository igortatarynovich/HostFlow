"""Reference R5 — Policy Merge Gate.

Platform pack + tenant overlay delta resolves required documents. Proof: Q5.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from backend.app.document_types.registry import normalize_input_doc_type
from backend.app.modules.documents.pack_definitions import DOCUMENT_PACK_DEFINITIONS
from backend.app.reference.document_policy_merge import (
    candidate_requires_document,
    merge_resolved_policy,
    validate_tenant_overlay_delta,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PACK_DEFINITIONS = _REPO_ROOT / "backend" / "app" / "modules" / "documents" / "pack_definitions.py"
_RULESET = _REPO_ROOT / "backend" / "app" / "services" / "document_ruleset.py"
_MERGE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_merge.py"
_CHECK = _REPO_ROOT / "backend" / "scripts" / "check_document_policy_r5.py"
_PLATFORM_PACK = _REPO_ROOT / "docs" / "specs" / "platform" / "document-policy-platform-pack-v1.json"
_SOT = _REPO_ROOT / "docs" / "specs" / "tasks" / "platform-reference-identity-sot.md"


def test_r5_q5_residence_card_required_for_card_residency() -> None:
    ctx = {
        "residency_status": "card",
        "citizenship": "UA",
        "work_country": "PL",
        "position_category": "driver",
    }
    assert candidate_requires_document(ctx, "residence_card")
    assert candidate_requires_document(ctx, "residence_permit")
    assert normalize_input_doc_type("residence_permit") == "residence_card"


def test_r5_merge_rejects_tenant_fork_defaults() -> None:
    try:
        validate_tenant_overlay_delta({"candidate": {"defaults": {"requiredTypes": ["passport"]}}})
    except ValueError as exc:
        assert "defaults forbidden" in str(exc)
    else:
        raise AssertionError("expected tenant fork to be rejected")


def test_r5_pack_definitions_use_country_registry_not_local_eu_set() -> None:
    source = _PACK_DEFINITIONS.read_text(encoding="utf-8")
    assert "_DEFAULT_EU_COUNTRIES" not in source
    assert "eu_member_alpha2_lower" in source
    tree = ast.parse(source)
    assigns = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and "EU" in t.id for t in node.targets)
    ]
    assert assigns == []


def test_r5_document_ruleset_projects_resolved_policy() -> None:
    source = _RULESET.read_text(encoding="utf-8")
    assert "merge_resolved_policy" in source
    resolved = merge_resolved_policy()
    assert resolved["candidate"]["defaults"]["requiredTypes"]


def test_r5_policy_check_script() -> None:
    result = subprocess.run(
        [sys.executable, str(_CHECK)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_r5_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference R5 Policy Merge Gate" in ci
    assert "test_reference_r5_policy_merge_gate.py" in ci
    r4_at = ci.index("Reference R4 Alias Consolidation Gate")
    r5_at = ci.index("Reference R5 Policy Merge Gate")
    lint_at = ci.index("- name: Lint")
    assert r4_at < r5_at < lint_at


def test_r5_gate_filename_and_platform_pack() -> None:
    assert Path(__file__).name == "test_reference_r5_policy_merge_gate.py"
    assert _PLATFORM_PACK.exists()
    assert _MERGE.exists()
    sot = _SOT.read_text(encoding="utf-8")
    assert "Resolved policy" in sot or "tenant_delta" in sot
    assert all(pack.document_codes for pack in DOCUMENT_PACK_DEFINITIONS)
