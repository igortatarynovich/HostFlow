"""PMI-1 gate: enforcement freeze ratchet over PMI-0 authority (PMI-R shrink-aware)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
FREEZE_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py"
MAP_SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_map.py"
FREEZE = REPO / "scripts" / "architecture" / "module_isolation_pmi1_freeze.json"
DEBT = REPO / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
AUTHORITY = REPO / "scripts" / "architecture" / "module_isolation_pmi0_baseline.json"
OWNERS_PMI1 = REPO / "scripts" / "architecture" / "module_isolation_owners_pmi1.json"

PMI1_DEBT_COUNT = 2006


def _run(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi1_freeze_lock_pins_844900d6_authority() -> None:
    lock = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert lock["schema"] == "pmi1.v1"
    assert lock["authority_commit"] == "844900d6"
    assert lock["authority_edge_count"] == PMI1_DEBT_COUNT
    actual = hashlib.sha256(AUTHORITY.read_bytes()).hexdigest()
    assert actual == lock["authority_sha256"]
    assert OWNERS_PMI1.is_file()
    debt = json.loads(DEBT.read_text(encoding="utf-8"))
    assert debt["schema"] == "pmi1.debt.v1"
    assert len(debt["edges"]) < PMI1_DEBT_COUNT
    assert debt.get("ownership_reveal_admitted") is True


def test_pmi1_freeze_gate_green() -> None:
    proc = _run(FREEZE_SCRIPT, ["--json"])
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_leak_count"] == 0
    assert summary["debt_growth_count"] == 0
    assert summary["hidden_count"] == 0
    assert summary["pending_ownership_reveal_count"] == 0
    assert summary["authority_edge_count"] == PMI1_DEBT_COUNT
    assert summary["debt_edge_count"] < PMI1_DEBT_COUNT


def test_pmi0_write_forbidden_after_freeze() -> None:
    proc = _run(MAP_SCRIPT, ["--write"])
    assert proc.returncode != 0
    assert "FORBIDDEN" in proc.stderr


def test_pmi1_invented_debt_growth_fails() -> None:
    original = DEBT.read_text(encoding="utf-8")
    try:
        debt = json.loads(original)
        debt["edges"].append(
            {
                "from_file": "backend/app/modules/recruitment/__init__.py",
                "import": "backend.app.modules.documents.bogus_pmi1_probe",
                "to_file": "backend/app/modules/documents/__init__.py",
            }
        )
        DEBT.write_text(json.dumps(debt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        proc = _run(FREEZE_SCRIPT, [])
        assert proc.returncode != 0
        assert "debt growth" in proc.stderr or "invented" in proc.stderr
    finally:
        DEBT.write_text(original, encoding="utf-8")
