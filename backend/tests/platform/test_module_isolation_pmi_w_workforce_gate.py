"""PMI-W gate: Workforce ISOLATED — foreign modules only via public/; Started Employee cut."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_workforce_isolation.py"
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
CARD = REPO / "docs" / "modules" / "workforce" / "module_isolation_card.md"
ALLOWLIST = REPO / "scripts" / "architecture" / "workforce_isolation_allowlist.txt"
STARTED = REPO / "backend" / "app" / "modules" / "workforce" / "public" / "started.py"

PMI_D_DEBT_COUNT = 1612


def _run(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_w_workforce_isolation_green() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0
    assert summary["violation_count"] == 0


def test_pmi_w_debt_below_pmi_d_baseline() -> None:
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert len(debt["edges"]) < PMI_D_DEBT_COUNT
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["debt_edge_count"] < PMI_D_DEBT_COUNT


def test_pmi_w_isolation_card_and_started_contract() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text
    assert "Started Employee" in text
    assert "Ready" in text and "Admit" in text
    assert ALLOWLIST.is_file()
    started = STARTED.read_text(encoding="utf-8")
    assert "Started Employee" in started
    assert "Ready" in started or "Admit" in started


def test_pmi_w_employment_does_not_import_workforce_internals() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["violation_count"] == 0
