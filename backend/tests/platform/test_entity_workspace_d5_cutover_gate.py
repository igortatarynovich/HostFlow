"""Entity Workspace D5 — Cutover Gate.

Consumer = Client. D2 catalog unchanged.
Reserved `documents` cannot be enabled. Shell nav ≠ composition slots.
No Catalog Passport. No HR / Vacancy / Order cutover.
D1 + D2 + D3 + D4 gates remain. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d5-client-cutover.md"
)
_D4_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d4-candidate-cutover.md"
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
_CONSUMER_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "clientConsumer.ts"
)
_HOST_TSX = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "compositionHost.tsx"
)
_PAGE = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "Companies.tsx"
)
_TYPES_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "types.ts"
)
_SLOTS_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "compositionSlots.ts"
)
_COMM_SLOT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "components"
    / "clients"
    / "ClientCommunicationSlot.tsx"
)
_FORMS_SLOT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "components"
    / "clients"
    / "ClientFormsSlot.tsx"
)
_FRONTEND_SRC = _REPO_ROOT / "hostflow-frontend" / "src"

_EXPECTED_CONSUMER_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "context-rail",
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_d5_brief_locks_client_consumer() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Client Cutover" in text
    assert "Entity Workspace D5 Cutover Gate" in text
    assert "Catalog Passport" in text
    assert "documents" in text
    assert "HR" in text
    assert "Companies" in text


def test_d5_client_binding_matches_enabled_catalog() -> None:
    src = _CONSUMER_TS.read_text(encoding="utf-8")
    slots = _ts_string_array(src, "CLIENT_COMPOSITION_SLOTS")
    assert slots == _EXPECTED_CONSUMER_SLOTS
    assert "documents" not in slots
    assert "CLIENT_COMPOSITION_CONSUMER_ID" in src
    assert "client" in src
    assert "assertClientCompositionSlots" in src
    enabled = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"),
        "ENTITY_WORKSPACE_ENABLED_SLOT_IDS",
    )
    assert "documents" not in enabled
    assert set(slots).issubset(enabled)


def test_d5_page_composes_d2_slots() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    host = _HOST_TSX.read_text(encoding="utf-8")
    assert "EntityWorkspaceCompositionHost" in page
    assert "CLIENT_COMPOSITION_SLOTS" in page
    assert "ClientCommunicationSlot" in page
    assert "ClientFormsSlot" in page
    assert 'data-entity-workspace-slot="overview"' in page
    assert 'data-entity-workspace-slot="timeline"' in page
    assert 'data-entity-workspace-slot="context-rail"' in page
    comm = _COMM_SLOT.read_text(encoding="utf-8")
    assert "listCommunicationThreads" in comm
    assert "entityType: 'company'" in comm
    forms = _FORMS_SLOT.read_text(encoding="utf-8")
    assert "listFormsPlatformHandlers" in forms
    assert "/platform/forms/handlers" in (
        _REPO_ROOT / "hostflow-frontend" / "src" / "api" / "formsPlatform.ts"
    ).read_text(encoding="utf-8")
    assert "data-entity-workspace-slot" in host
    assert "documents" not in _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"),
        "CLIENT_COMPOSITION_SLOTS",
    )


def test_d5_shell_sections_not_collapsed() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    consumer = _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"),
        "CLIENT_COMPOSITION_SLOTS",
    )
    assert "contacts" in sections
    assert "contacts" not in consumer
    assert "documents" in sections
    assert "documents" not in consumer
    assert sections != consumer


def test_d5_hr_vacancy_order_not_cut_over() -> None:
    leaked: list[str] = []
    needles = (
        "CLIENT_COMPOSITION_SLOTS",
        "clientConsumer",
        "assertClientCompositionSlots",
    )
    for path in sorted(_FRONTEND_SRC.rglob("*.ts")) + sorted(_FRONTEND_SRC.rglob("*.tsx")):
        rel = path.relative_to(_FRONTEND_SRC).as_posix()
        lowered = rel.lower()
        if not any(token in lowered for token in ("hr", "vacancy", "order")):
            continue
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in needles):
            leaked.append(rel)
    assert not leaked, f"D5 must not cut over HR/Vacancy/Order: {leaked}"


def test_d5_no_entity_catalog_passport_mint() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "entity_workspace.manifest" not in catalog


def test_d5_maturity_entity_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_d5_prior_gates_still_present() -> None:
    assert _D4_BRIEF.is_file()
    ci = _CI.read_text(encoding="utf-8")
    assert "Entity Workspace D1 Contract Seal Gate" in ci
    assert "Entity Workspace D2 Composition Gate" in ci
    assert "Entity Workspace D3 Cutover Gate" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D5 Cutover Gate" in ci
    assert "test_entity_workspace_d5_cutover_gate.py" in ci


def test_d5_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "entity-workspace-d5-client-cutover.md" in queue
    assert "entity-workspace-d5-client-cutover.md" in agents
    assert "entity-workspace-d1-contract-seal.md" in agents
    assert "entity-workspace-d2-composition-contract.md" in agents
    assert "entity-workspace-d4-candidate-cutover.md" in agents
    assert "D6" in queue
    assert "locked" in queue.lower()


def test_d5_gate_filename() -> None:
    assert Path(__file__).name == "test_entity_workspace_d5_cutover_gate.py"
