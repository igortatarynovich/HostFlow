"""Lifecycle Identity LI-1 — existence guard gate.

Single producer for stage registration; no funnel/UI cutover.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.constants import stages as stages_constants
from backend.app.platform.module_stage_registry.existence import (
    CATALOG_VERSION,
    REGISTRY_PATH,
    is_stage_registered,
    is_stage_registered_qualified,
    list_registered_stage_keys,
    qualified_stage_id,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "lifecycle-identity-li1-existence-guard.md"
_MANIFEST = REGISTRY_PATH
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_stage_existence_boundary.py"
_META = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "meta.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_li1_brief_and_manifest_exist() -> None:
    assert _BRIEF.is_file()
    assert _MANIFEST.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "LI-1 Existence Guard Gate" in brief
    assert "does not cut over" in brief.lower() or "no runtime cutover" in brief.lower()


def test_li1_recruitment_candidate_existence_producer() -> None:
    assert CATALOG_VERSION == "lifecycle-identity-li1-recruitment-candidate-v0"
    keys = list_registered_stage_keys("recruitment", "candidate")
    assert keys
    assert is_stage_registered("recruitment", "candidate", "new")
    assert is_stage_registered_qualified("recruitment.candidate.new")
    assert not is_stage_registered("recruitment", "candidate", "not_a_registered_stage")
    assert not is_stage_registered("hr", "employee", "active")
    assert keys == frozenset(stages_constants.LABELS)


def test_li1_qualified_id_helper() -> None:
    assert qualified_stage_id("recruitment", "candidate", "docs_wait") == "recruitment.candidate.docs_wait"


def test_li1_does_not_cut_over_runtime_stranglers() -> None:
    meta = _META.read_text(encoding="utf-8")
    assert "module_stage_registry" not in meta
    assert hasattr(stages_constants, "is_stage_code")
    assert "new" in stages_constants.LABELS


def test_li1_stage_existence_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_li1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Lifecycle Identity LI-1 Existence Guard Gate" in ci
    assert "test_lifecycle_identity_li1_existence_guard_gate.py" in ci


def test_li1_gate_filename() -> None:
    assert Path(__file__).name == "test_lifecycle_identity_li1_existence_guard_gate.py"
