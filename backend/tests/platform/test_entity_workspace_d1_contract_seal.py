"""Entity Workspace D1 — Contract Seal Gate.

PX / adapter Shell ≠ Phase D Universal complete.
Public chrome SoT path = hostflow-frontend/src/components/ui/EntityWorkspace.
platform/entity-workspace Shell is adapter-only.
No module workspace promotion into the kit barrel.
No Entity Catalog Passport in D1. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d1-contract-seal.md"
)
_MATURITY = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "platform-capability-maturity.md"
)
_CATALOG = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "platform-capability-catalog.md"
)
_UI_DIR = _REPO_ROOT / "hostflow-frontend" / "src" / "components" / "ui"
_UI_INDEX = _UI_DIR / "index.ts"
_UI_ENTITY = _UI_DIR / "EntityWorkspace.tsx"
_PLATFORM_INDEX = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "index.ts"
)

_FORBIDDEN_KIT_EXPORTS = (
    "CandidateWorkspace",
    "RecruitmentWorkspace",
    "HRWorkspace",
    "VacancyWorkspace",
    "EmployeeWorkspace",
)


def _ui_kit_sources() -> str:
    chunks: list[str] = []
    if _UI_INDEX.is_file():
        chunks.append(_UI_INDEX.read_text(encoding="utf-8"))
    for path in sorted(_UI_DIR.glob("*.tsx")) + sorted(_UI_DIR.glob("*.ts")):
        if path.name.startswith("__"):
            continue
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_d1_brief_locks_boundary_and_no_passport() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Universal Entity Workspace" in text
    assert "Catalog Passport" in text
    assert "components/ui/EntityWorkspace" in text
    assert "EntityWorkspaceShell" in text or "passport adapter" in text.lower()
    assert "Ownership card" in text
    assert "**COMPLETE**" in text


def test_d1_maturity_entity_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_d1_platform_shell_adapter_exists() -> None:
    platform_index = _PLATFORM_INDEX.read_text(encoding="utf-8")
    assert "EntityWorkspaceShell" in platform_index
    assert (_PLATFORM_INDEX.parent / "EntityWorkspaceShell.tsx").is_file()


def test_d1_public_chrome_sot_path_is_components_ui() -> None:
    """SoT path is reserved under components/ui; Shell must not be the public chrome."""
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "components/ui/EntityWorkspace" in brief

    kit_src = _ui_kit_sources()
    assert "EntityWorkspaceShell" not in kit_src

    if _UI_ENTITY.is_file():
        entity_src = _UI_ENTITY.read_text(encoding="utf-8")
        assert 'data-entity-workspace="v1"' in entity_src
        assert "export function EntityWorkspace" in entity_src
        if _UI_INDEX.is_file():
            ui_index = _UI_INDEX.read_text(encoding="utf-8")
            assert "EntityWorkspace" in ui_index
            assert "./EntityWorkspace" in ui_index or "'./EntityWorkspace'" in ui_index


def test_d1_kit_barrel_excludes_module_workspaces() -> None:
    kit_src = _ui_kit_sources()
    assert kit_src, "expected components/ui sources on tip"
    for name in _FORBIDDEN_KIT_EXPORTS:
        assert name not in kit_src, f"kit must not export {name}"
        assert not (_UI_DIR / f"{name}.tsx").exists(), f"kit must not ship {name}.tsx"


def test_d1_no_entity_catalog_passport_mint() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "entity_workspace.manifest" not in catalog


def test_d1_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "entity-workspace-d1-contract-seal.md" in queue
    assert "entity-workspace-d1-contract-seal.md" in agents
