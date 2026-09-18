"""PMI-R gate: Recruitment ISOLATED — foreign modules only via public/; debt shrunk."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_recruitment_isolation.py"
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
CARD = REPO / "docs" / "modules" / "recruitment" / "module_isolation_card.md"
ALLOWLIST = REPO / "scripts" / "architecture" / "recruitment_isolation_boundary_allowlist.txt"

PMI1_DEBT_COUNT = 2006


def _run(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_r_recruitment_isolation_green() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0


def test_pmi_r_debt_below_pmi1_baseline() -> None:
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert len(debt["edges"]) < PMI1_DEBT_COUNT
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["debt_edge_count"] < PMI1_DEBT_COUNT


def test_pmi_r_isolation_card_closed() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text or "Decision\n\n`ISOLATED`" in text or "Decision: ISOLATED" in text
    assert "ISOLATED" in text
    for row in range(1, 9):
        # eight rows closed
        assert f"| {row} |" in text
    assert "CLOSED" in text
    assert ALLOWLIST.is_file()
