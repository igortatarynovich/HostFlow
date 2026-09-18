"""PMI-D gate: Documents ISOLATED — foreign modules only via public evidence contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_documents_isolation.py"
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
CARD = REPO / "docs" / "modules" / "documents" / "module_isolation_card.md"
ALLOWLIST = REPO / "scripts" / "architecture" / "documents_isolation_allowlist.txt"

PMI_E_DEBT_COUNT = 1705


def _run(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_d_documents_isolation_green() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0
    assert summary["violation_count"] == 0


def test_pmi_d_debt_below_pmi_e_baseline() -> None:
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert len(debt["edges"]) < PMI_E_DEBT_COUNT
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["debt_edge_count"] < PMI_E_DEBT_COUNT


def test_pmi_d_isolation_card_closed() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text
    assert "evidence" in text.lower()
    assert "Ready" in text and "Admit" in text
    assert ALLOWLIST.is_file()


def test_pmi_d_closed_exc_pmi_b_doc() -> None:
    """Boundary must not import Documents internals after PMI-D."""
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["violation_count"] == 0
