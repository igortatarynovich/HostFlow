"""PMI-E gate: Employment ISOLATED — foreign modules only via public/; debt shrunk."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_employment_isolation.py"
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
CARD = REPO / "docs" / "modules" / "employment" / "module_isolation_card.md"
ALLOWLIST = REPO / "scripts" / "architecture" / "employment_isolation_allowlist.txt"
RECRUIT_ALLOW = (
    REPO / "scripts" / "architecture" / "recruitment_isolation_boundary_allowlist.txt"
)

PMI_B_DEBT_COUNT = 1746


def _run(script: Path, args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_e_employment_isolation_green() -> None:
    proc = _run(ISO_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0
    assert summary["violation_count"] == 0


def test_pmi_e_debt_below_pmi_b_baseline() -> None:
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert len(debt["edges"]) < PMI_B_DEBT_COUNT
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["debt_edge_count"] < PMI_B_DEBT_COUNT


def test_pmi_e_isolation_card_closed() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text
    assert "employment_start_allowed" in text
    assert "ESO-5" in text or "employment_started" in text
    assert ALLOWLIST.is_file()


def test_pmi_e_closed_exc_pmi_r_funnel() -> None:
    body = [
        ln
        for ln in RECRUIT_ALLOW.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    employment_funnel = [
        ln
        for ln in body
        if ln.startswith("employment|")
        and ("hr_employee_funnel" in ln or "funnel_types" in ln or "models.funnel" in ln)
    ]
    assert employment_funnel == [], employment_funnel


def test_pmi_e_closed_exc_pmi_b_emp() -> None:
    proc = _run(
        REPO / "scripts" / "architecture" / "check_boundary_isolation.py",
        ["--json"],
    )
    assert proc.returncode == 0
    # Boundary must not import Employment internals (covered by employment checker = 0).
    emp = _run(ISO_SCRIPT, ["--json"])
    assert json.loads(emp.stdout)["violation_count"] == 0
