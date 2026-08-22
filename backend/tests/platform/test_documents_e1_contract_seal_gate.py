"""Documents Platform E1 — Contract Seal Gate.

Hub ownership sealed. E1 itself did not enable D2 `documents`
(runtime catalog unlock is E2). Shell nav ≠ composition slots.
No Catalog rewrite. Documents Foundation stays 🔄.
D1–D9 gates remain. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e1-contract-seal.md"
)
_D9_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d9-services-order-cutover.md"
)
_HUB_SCOPE = _REPO_ROOT / "docs" / "document-hub" / "module-scope.md"
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
_DELIVERY = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "services"
    / "document_hub_delivery_contract.py"
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_e1_brief_locks_ownership_and_no_slot_enable() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E1" in text
    assert "Ownership card" in text
    assert "ADR-009" in text
    assert "document_hub_delivery_contract" in text
    assert "D2" in text and "documents" in text
    assert "reserved" in text.lower()
    assert "OCR" in text
    assert "HrHandoffDetailPage" in text
    assert "Documents Platform E1 Contract Seal Gate" in text


def test_e1_d9_closed() -> None:
    text = _D9_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in text
    assert "#268" in text
    assert "28978a1f" in text


def test_e1_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell
    assert "E1" in foundation_cell or "Phase E" in foundation_cell


def test_e1_entity_foundation_still_in_progress() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_e1_catalog_documents_passport_unchanged_shape() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    assert "ADR-009" in catalog
    assert "entity.workspace.public_contract" not in catalog
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)


def test_e1_delivery_facade_exists_and_is_not_link_sot() -> None:
    src = _DELIVERY.read_text(encoding="utf-8")
    assert "list_candidate_documents_via_contract" in src
    assert "not ADR-009 Document Link SoT" in src or "not the\nADR-009 Document Link SoT" in src or "Document Link SoT" in src
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "ADR-009" in hub
    assert "documents-platform-e1-contract-seal.md" in hub


def test_e1_did_not_treat_itself_as_d2_enable() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "does **not** enable D2" in text or "must keep reserved" in text or "still reserved" in text
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    slots = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"), "ENTITY_WORKSPACE_SLOT_CATALOG"
    )
    assert "documents" in sections
    assert sections != slots


def test_e1_shell_documents_nav_is_not_d2_slot() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    slots = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"), "ENTITY_WORKSPACE_SLOT_CATALOG"
    )
    assert "documents" in sections
    assert sections != slots
    assert "compositionSlots.ts" in types_src or "composition slot" in types_src.lower()


def test_e1_prior_gates_still_present() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Entity Workspace D1 Contract Seal Gate" in ci
    assert "Entity Workspace D2 Composition Gate" in ci
    assert "Entity Workspace D3 Cutover Gate" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D5 Cutover Gate" in ci
    assert "Entity Workspace D6 Cutover Gate" in ci
    assert "Entity Workspace D7 Cutover Gate" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Entity Workspace D9 Cutover Gate" in ci
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "test_documents_e1_contract_seal_gate.py" in ci


def test_e1_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e1-contract-seal.md" in queue
    assert "documents-platform-e1-contract-seal.md" in agents
    assert "entity-workspace-d9-services-order-cutover.md" in agents
    assert "named Contract Seal Gate" in agents
    assert "E2" in queue
    assert "locked" in queue.lower()


def test_e1_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e1_contract_seal_gate.py"
