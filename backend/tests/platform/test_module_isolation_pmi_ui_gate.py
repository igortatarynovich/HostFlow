"""PMI-UI gate: design-system authority + forbid parallel/cross-spine/new reconstructors."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/HostFlow")
ISO_SCRIPT = REPO / "scripts" / "architecture" / "check_ui_isolation.py"
AUTH = REPO / "scripts" / "architecture" / "ui_primitive_authority.json"
ALLOWLIST = REPO / "scripts" / "architecture" / "ui_isolation_allowlist.txt"
CARD = REPO / "docs" / "modules" / "ui" / "module_isolation_card.md"
DS_INDEX = REPO / "hostflow-frontend" / "src" / "platform" / "design-system" / "index.ts"
NEXT_ACTION = REPO / "hostflow-frontend" / "src" / "platform" / "design-system" / "NextActionBadge.tsx"
HEADER = REPO / "hostflow-frontend" / "src" / "components" / "hr" / "EmployeeReadinessHeader.tsx"

# PMI-UI must not grow UI debt above the freeze allowlist written at PASS.
UI_DEBT_CEILING = 8


def _run(args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ISO_SCRIPT), *(args or [])],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )


def test_pmi_ui_isolation_green() -> None:
    proc = _run(["--json"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summary = json.loads(proc.stdout)
    assert summary["ok"] is True
    assert summary["new_violation_count"] == 0
    assert summary["violation_count"] <= UI_DEBT_CEILING


def test_pmi_ui_authority_and_public_surface() -> None:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    assert "categories" in auth
    assert "forms_fields" in auth["categories"]
    assert DS_INDEX.is_file()
    assert NEXT_ACTION.is_file()
    text = DS_INDEX.read_text(encoding="utf-8")
    assert "StatusBadge" in text
    assert "NextActionBadge" in text
    assert "Button" in text


def test_pmi_ui_card_four_dod() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert "Status: ISOLATED" in text
    assert "Platform primitives" in text
    assert "Decision ownership" in text
    assert "Enforcement" in text
    assert ALLOWLIST.is_file()
    assert len([ln for ln in ALLOWLIST.read_text().splitlines() if ln.strip() and not ln.startswith("#")]) <= UI_DEBT_CEILING


def test_pmi_ui_decision_ownership_prefers_backend() -> None:
    header = HEADER.read_text(encoding="utf-8")
    assert "decision_readiness" in header
    assert "applyBackendVerdict" in header
    # documents must not import candidate NextActionBadge shim
    doc_card = (
        REPO
        / "hostflow-frontend"
        / "src"
        / "modules"
        / "documents"
        / "components"
        / "DocumentCard.tsx"
    ).read_text(encoding="utf-8")
    assert "platform/design-system" in doc_card
    assert "components/candidate/NextActionBadge" not in doc_card
