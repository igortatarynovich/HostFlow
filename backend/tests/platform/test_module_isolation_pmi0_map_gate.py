"""PMI-0 gate: complete deterministic map + reproducible baseline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
SCRIPT = REPO / "scripts" / "architecture" / "check_module_isolation_map.py"
OWNERS = REPO / "scripts" / "architecture" / "module_isolation_owners.json"
BASELINE = REPO / "scripts" / "architecture" / "module_isolation_pmi0_baseline.json"
SPINE = ("recruitment", "boundary", "employment", "documents", "workforce")


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi0_owners_map_exists() -> None:
    assert OWNERS.is_file()
    raw = json.loads(OWNERS.read_text(encoding="utf-8"))
    for name in SPINE:
        spec = raw["owners"][name]
        assert spec.get("required_prefixes"), name
        assert spec.get("prefixes"), name


def test_pmi0_baseline_committed() -> None:
    assert BASELINE.is_file()
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert data["schema"] == "pmi0.v1"
    assert data["backend_file_count"] == sum(data["file_counts"].values())
    assert len(data["unassigned"]) == data["file_counts"].get("UNASSIGNED", 0)
    assert len(data["cross_owner_edges"]) >= 1
    for name in SPINE:
        assert data["file_counts"].get(name, 0) >= 1


def test_pmi0_scanner_check_matches_baseline() -> None:
    proc = _run(["--check", "--json"])
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout)
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert summary["backend_file_count"] == baseline["backend_file_count"]
    assert summary["cross_owner_edge_count"] == len(baseline["cross_owner_edges"])
    assert "ISOLATED" not in proc.stdout
    # No manual public-import whitelist in the leak set.
    assert "public_name_markers" not in json.loads(OWNERS.read_text(encoding="utf-8"))
