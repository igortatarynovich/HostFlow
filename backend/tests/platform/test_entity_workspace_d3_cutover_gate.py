"""Entity Workspace D3 — Cutover Gate.

First consumer = Sales Inquiry. D2 catalog unchanged.
Reserved `documents` cannot be enabled. No Catalog Passport.
No Candidate/HR cutover. Shell sections not collapsed into D2 slots.
D1 + D2 gates remain. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d3-consumer-cutover.md"
)
_D2_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d2-composition-contract.md"
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
    / "salesInquiryConsumer.ts"
)
_HOST_TSX = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "compositionHost.tsx"
)
_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "application-workspace"
    / "ApplicationSalesDetailPanel.tsx"
)
_TYPES_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "types.ts"
)
_CANDIDATE_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "CandidateEntityWorkspacePage.tsx"
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


def test_d3_brief_locks_first_consumer() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Consumer Cutover" in text
    assert "Sales Inquiry" in text
    assert "Entity Workspace D3 Cutover Gate" in text
    assert "Catalog Passport" in text
    assert "documents" in text
    assert "Candidate" in text
    assert "**COMPLETE**" in text


def test_d3_sales_inquiry_binding_matches_enabled_catalog() -> None:
    src = _CONSUMER_TS.read_text(encoding="utf-8")
    slots = _ts_string_array(src, "SALES_INQUIRY_COMPOSITION_SLOTS")
    assert slots == _EXPECTED_CONSUMER_SLOTS
    assert "documents" not in slots
    assert "SALES_INQUIRY_COMPOSITION_CONSUMER_ID" in src
    assert "sales-inquiry" in src
    assert "assertSalesInquiryCompositionSlots" in src


def test_d3_panel_composes_d2_slots() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    host = _HOST_TSX.read_text(encoding="utf-8")
    assert "EntityWorkspaceCompositionHost" in panel
    assert "SALES_INQUIRY_COMPOSITION_SLOTS" in panel
    assert "SalesInquiryCommunicationSlot" in panel
    assert 'data-entity-workspace-slot="context-rail"' in panel
    assert 'data-entity-workspace-slot="timeline"' in panel
    assert "listCommunicationThreads" in (
        _REPO_ROOT
        / "hostflow-frontend"
        / "src"
        / "components"
        / "sales"
        / "SalesInquiryCommunicationSlot.tsx"
    ).read_text(encoding="utf-8")
    assert "entityType: 'sales_inquiry'" in (
        _REPO_ROOT
        / "hostflow-frontend"
        / "src"
        / "components"
        / "sales"
        / "SalesInquiryCommunicationSlot.tsx"
    ).read_text(encoding="utf-8")
    assert "data-entity-workspace-slot" in host
    assert "documents" not in _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"),
        "SALES_INQUIRY_COMPOSITION_SLOTS",
    )


def test_d3_candidate_not_cut_over() -> None:
    page = _CANDIDATE_PAGE.read_text(encoding="utf-8")
    assert "SALES_INQUIRY_COMPOSITION_SLOTS" not in page
    assert "EntityWorkspaceCompositionHost" not in page
    assert "salesInquiryConsumer" not in page
    leaked: list[str] = []
    for path in sorted(_FRONTEND_SRC.rglob("*.ts")) + sorted(_FRONTEND_SRC.rglob("*.tsx")):
        rel = path.relative_to(_FRONTEND_SRC).as_posix()
        if "candidate" not in rel.lower() and "hr" not in rel.lower():
            continue
        text = path.read_text(encoding="utf-8")
        if "salesInquiryConsumer" in text or "SALES_INQUIRY_COMPOSITION_SLOTS" in text:
            leaked.append(rel)
    assert not leaked, f"D3 must not cut over Candidate/HR: {leaked}"


def test_d3_shell_sections_not_collapsed() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    assert sections != _EXPECTED_CONSUMER_SLOTS
    assert "contacts" in sections
    consumer = _CONSUMER_TS.read_text(encoding="utf-8")
    assert "contacts" not in _ts_string_array(consumer, "SALES_INQUIRY_COMPOSITION_SLOTS")


def test_d3_no_entity_catalog_passport_mint() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "entity_workspace.manifest" not in catalog


def test_d3_maturity_entity_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_d3_prior_gates_still_present() -> None:
    assert _D2_BRIEF.is_file()
    ci = _CI.read_text(encoding="utf-8")
    assert "Entity Workspace D1 Contract Seal Gate" in ci
    assert "Entity Workspace D2 Composition Gate" in ci
    assert "Entity Workspace D3 Cutover Gate" in ci
    assert "test_entity_workspace_d3_cutover_gate.py" in ci


def test_d3_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "entity-workspace-d3-consumer-cutover.md" in queue
    assert "entity-workspace-d3-consumer-cutover.md" in agents
    assert "D4" in queue
    assert "locked" in queue.lower()


def test_d3_gate_filename() -> None:
    assert Path(__file__).name == "test_entity_workspace_d3_cutover_gate.py"
