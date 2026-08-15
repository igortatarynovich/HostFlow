"""Entity Workspace D2 — Composition Gate.

Slot catalog frozen. Reserved `documents` cannot be enabled.
No Catalog Passport. No consumer cutover UI. D1 gate remains.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d2-composition-contract.md"
)
_D1_BRIEF = (
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
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_SLOTS_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "compositionSlots.ts"
)
_TYPES_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "types.ts"
)
_PLATFORM_INDEX = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "index.ts"
)
_FRONTEND_SRC = _REPO_ROOT / "hostflow-frontend" / "src"

_EXPECTED_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "documents",
    "context-rail",
)
_ENABLED_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "context-rail",
)
_RESERVED_SLOTS = ("documents",)

_SLOT_IMPORT_MARKERS = (
    "compositionSlots",
    "ENTITY_WORKSPACE_SLOT_CATALOG",
    "ENTITY_WORKSPACE_ENABLED_SLOT_IDS",
    "ENTITY_WORKSPACE_RESERVED_SLOT_IDS",
    "isEntityWorkspaceSlotEnabled",
    "EntityWorkspaceSlotId",
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def _brief_slot_ids(text: str) -> tuple[str, ...]:
    table = text.split("## Slot catalog (normative for D2)", 1)[1]
    table = table.split("**Rules:**", 1)[0]
    return tuple(re.findall(r"\|\s+`([^`]+)`\s+\|", table))


def test_d2_brief_locks_slot_catalog_and_no_passport() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Composition Contract" in text
    assert "Catalog Passport" in text
    assert "documents" in text
    assert "Phase E" in text
    assert "Entity Workspace D2 Composition Gate" in text
    assert "**COMPLETE**" in text
    assert _brief_slot_ids(text) == _EXPECTED_SLOTS
    assert "Empty / unavailable" in text
    assert "consumer cutover" in text.lower() or "Consumer cutover" in text


def test_d2_frontend_slot_allowlist_matches_catalog() -> None:
    src = _SLOTS_TS.read_text(encoding="utf-8")
    assert _ts_string_array(src, "ENTITY_WORKSPACE_SLOT_CATALOG") == _EXPECTED_SLOTS
    assert _ts_string_array(src, "ENTITY_WORKSPACE_ENABLED_SLOT_IDS") == _ENABLED_SLOTS
    assert _ts_string_array(src, "ENTITY_WORKSPACE_RESERVED_SLOT_IDS") == _RESERVED_SLOTS
    index = _PLATFORM_INDEX.read_text(encoding="utf-8")
    assert "ENTITY_WORKSPACE_SLOT_CATALOG" in index
    assert "isEntityWorkspaceSlotEnabled" in index
    assert "from './compositionSlots'" in index or 'from "./compositionSlots"' in index


def test_d2_documents_slot_cannot_be_enabled() -> None:
    src = _SLOTS_TS.read_text(encoding="utf-8")
    enabled = _ts_string_array(src, "ENTITY_WORKSPACE_ENABLED_SLOT_IDS")
    reserved = _ts_string_array(src, "ENTITY_WORKSPACE_RESERVED_SLOT_IDS")
    catalog = _ts_string_array(src, "ENTITY_WORKSPACE_SLOT_CATALOG")
    assert "documents" in catalog
    assert "documents" in reserved
    assert "documents" not in enabled
    assert "isEntityWorkspaceSlotEnabled" in src
    assert set(enabled).isdisjoint(reserved)
    assert tuple(slot for slot in catalog if slot not in reserved) == enabled


def test_d2_slot_catalog_is_not_shell_section_order() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    assert sections != _EXPECTED_SLOTS
    assert "compositionSlots.ts" in types_src or "composition slot" in types_src.lower()


_D3_D4_CONSUMER_PATHS = (
    "platform/application-workspace/ApplicationSalesDetailPanel.tsx",
    "platform/entity-workspace/salesInquiryConsumer.ts",
    "platform/entity-workspace/compositionHost.tsx",
    "components/sales/SalesInquiryCommunicationSlot.tsx",
    "pages/CandidateEntityWorkspacePage.tsx",
    "components/candidate/CandidateCommunicationSlot.tsx",
    "components/candidate/CandidateFormsSlot.tsx",
)


def test_d2_no_consumer_cutover_screens() -> None:
    leaked: list[str] = []
    allowed = set(_D3_D4_CONSUMER_PATHS)
    for path in sorted(_FRONTEND_SRC.rglob("*.ts")) + sorted(_FRONTEND_SRC.rglob("*.tsx")):
        rel = path.relative_to(_FRONTEND_SRC)
        rel_posix = rel.as_posix()
        if rel_posix.startswith("platform/entity-workspace/"):
            continue
        if rel_posix in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in _SLOT_IMPORT_MARKERS):
            leaked.append(rel_posix)
    assert not leaked, f"D2 must not cut over consumers onto slot catalog: {leaked}"


def test_d2_no_entity_catalog_passport_mint() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "entity_workspace.manifest" not in catalog


def test_d2_maturity_entity_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_d2_d1_gate_still_present() -> None:
    d1_test = (
        _REPO_ROOT
        / "backend"
        / "tests"
        / "platform"
        / "test_entity_workspace_d1_contract_seal.py"
    )
    assert d1_test.is_file()
    assert "**COMPLETE**" in _D1_BRIEF.read_text(encoding="utf-8")
    ci = _CI.read_text(encoding="utf-8")
    assert "Entity Workspace D1 Contract Seal Gate" in ci
    assert "test_entity_workspace_d1_contract_seal.py" in ci
    assert "Entity Workspace D2 Composition Gate" in ci
    assert "test_entity_workspace_d2_composition_gate.py" in ci


def test_d2_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "entity-workspace-d2-composition-contract.md" in queue
    assert "entity-workspace-d2-composition-contract.md" in agents
    assert "D3" in queue
    assert "locked" in queue.lower()


def test_d2_gate_filename() -> None:
    assert Path(__file__).name == "test_entity_workspace_d2_composition_gate.py"
