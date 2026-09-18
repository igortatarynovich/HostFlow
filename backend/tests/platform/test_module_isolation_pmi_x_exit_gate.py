"""PMI-X program exit gate — joint verification + three hard locks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path("/opt/HostFlow")
EXIT_SCRIPT = REPO / "scripts" / "architecture" / "check_pmi_x_program_exit.py"
GATE = REPO / "docs" / "specs" / "gates" / "platform-modularization-isolation-cutover-gate.md"
CUTOVER = REPO / "docs" / "specs" / "tasks" / "platform-modularization-isolation-cutover.md"
PREFLIGHT = REPO / "docs" / "specs" / "tasks" / "post-pmi-kernel-public-contract-preflight.md"

PMI1_AUTHORITY = 2006
BACKEND_DEBT = 1557
UI_DEBT = 8


@pytest.fixture(scope="module")
def pmi_x_summary() -> dict:
    proc = subprocess.run(
        [sys.executable, str(EXIT_SCRIPT), "--json"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)


def test_pmi_x_joint_exit_green(pmi_x_summary: dict) -> None:
    assert pmi_x_summary["ok"] is True, pmi_x_summary.get("failures")
    assert pmi_x_summary["nature"] == "verification_only"
    assert pmi_x_summary["head"] and pmi_x_summary["head"] != "UNKNOWN"
    assert pmi_x_summary["criteria"]["joint_checkers_green"] is True
    assert pmi_x_summary["criteria"]["five_isolated_cards"] is True
    assert pmi_x_summary["criteria"]["bedw_foreign_internals_zero"] is True
    assert pmi_x_summary["criteria"]["recruitment_spine_foreign_internals_zero"] is True
    assert pmi_x_summary["criteria"]["pass_is_head_simultaneous"] is True


def test_pmi_x_hard_locks(pmi_x_summary: dict) -> None:
    locks = pmi_x_summary["hard_locks"]
    assert locks["exit_fixes_nothing"] is True
    assert locks["pass_is_head_simultaneous"] is True
    assert locks["ready_not_auto_unfrozen"] is True
    assert pmi_x_summary["parked"]["ready_not_auto_unfrozen"] is True
    assert pmi_x_summary["parked"]["exit_fixes_nothing"] is True
    assert pmi_x_summary["parked"]["head_simultaneous_required"] is True
    assert "separate work item" in pmi_x_summary["stop_rule"]


def test_pmi_x_debt_ratchet_not_zero_required(pmi_x_summary: dict) -> None:
    assert pmi_x_summary["backend_debt"] == BACKEND_DEBT
    assert pmi_x_summary["pmi1_authority"] == PMI1_AUTHORITY
    assert pmi_x_summary["ui_debt"] == UI_DEBT
    assert pmi_x_summary["recruitment_non_spine_debt"] <= 63
    assert pmi_x_summary["criteria"]["debt_need_not_be_zero"] is True
    assert pmi_x_summary["backend_debt"] < PMI1_AUTHORITY
    assert PMI1_AUTHORITY - pmi_x_summary["backend_debt"] == 449


def test_pmi_x_post_pmi_preflight_brief_public_only(pmi_x_summary: dict) -> None:
    brief = pmi_x_summary["post_pmi_kernel_preflight"]
    assert brief["exists"] is True
    assert brief["public_only"] is True
    assert brief["forbids_internals"] is True
    text = PREFLIGHT.read_text(encoding="utf-8")
    assert "recruitment.public" in text
    assert "recruitment_package" in text
    assert "VERIFICATION_SLOT_DEFS" in text
    assert "requirement_engine" in text
    assert "OPEN" in text
    cutover = CUTOVER.read_text(encoding="utf-8")
    assert "Ready is not auto-unfrozen" in cutover
    gate = GATE.read_text(encoding="utf-8")
    assert "HEAD-simultaneous" in gate or "together on HEAD" in gate
    assert "fixes nothing" in gate.lower() or "Exit fixes nothing" in gate


def test_pmi_x_public_surfaces_exist(pmi_x_summary: dict) -> None:
    for name, ok in pmi_x_summary["public"].items():
        assert ok is True, name
