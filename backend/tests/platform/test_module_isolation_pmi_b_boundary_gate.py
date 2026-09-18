"""PMI-B gate: Boundary ISOLATED — foreign modules only via public/; debt shrunk."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_boundary_isolation.py"
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
CARD = REPO / "docs" / "modules" / "boundary" / "module_isolation_card.md"
ALLOWLIST = REPO / "scripts" / "architecture" / "boundary_isolation_allowlist.txt"
RECRUIT_ALLOW = (
    REPO / "scripts" / "architecture" / "recruitment_isolation_boundary_allowlist.txt"
)

PMI_R_DEBT_COUNT = 1799


def _run(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_b_boundary_isolation_green() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0
    assert summary["violation_count"] == 0


def test_pmi_b_debt_below_pmi_r_baseline() -> None:
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert len(debt["edges"]) < PMI_R_DEBT_COUNT
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["debt_edge_count"] < PMI_R_DEBT_COUNT


def test_pmi_b_isolation_card_closed() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text
    assert "ISOLATED" in text
    assert "Recruitment Ready" in text
    assert ALLOWLIST.is_file()


def test_pmi_b_preserves_exc_pmi_r_funnel_allowlist_until_pmi_e() -> None:
    """Historical note: PMI-B required FUNNEL exceptions to remain; PMI-E closes them.

    This PMI-B gate only asserts the Recruitment allowlist file still exists and
    is shrink-only (non-empty or empty both OK after PMI-E).
    """
    assert RECRUIT_ALLOW.is_file()
    assert "shrink-only" in RECRUIT_ALLOW.read_text(encoding="utf-8")
