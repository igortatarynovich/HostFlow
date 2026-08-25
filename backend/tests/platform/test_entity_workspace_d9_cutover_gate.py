"""Entity Workspace D9 — Cutover Gate.

Consumer = Services order (ServicesPage / /app/orders). D2 catalog unchanged.
Reserved `documents` cannot be enabled. Shell nav ≠ composition slots.
No Catalog Passport. No Sales Order re-bind or HrHandoffDetailPage cutover.
No HR employee re-bind. D1 + D2 + D3 + D4 + D5 + D6 + D7 + D8 gates remain.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d9-services-order-cutover.md"
)
_D8_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-workspace-d8-hr-employee-cutover.md"
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
    / "servicesOrderConsumer.ts"
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
    _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "ServicesPage.tsx"
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
    / "pages"
    / "ServicesOrderCommunicationSlot.tsx"
)
_FORMS_SLOT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "ServicesOrderFormsSlot.tsx"
)
_SALES_ORDER_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "sales"
    / "SalesOrderDetailPage.tsx"
)
_HANDOFF_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "hr"
    / "HrHandoffDetailPage.tsx"
)
_HR_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "hr"
    / "HrEmployeeDetailPage.tsx"
)
_CANDIDATE_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "CandidateEntityWorkspacePage.tsx"
)
_VACANCY_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "components"
    / "vacancies"
    / "VacancyDetail.tsx"
)
_FRONTEND_SRC = _REPO_ROOT / "hostflow-frontend" / "src"

_EXPECTED_CONSUMER_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "context-rail",
)

_THIS_CONSUMER_PATHS = {
    "pages/ServicesPage.tsx",
    "pages/ServicesOrderCommunicationSlot.tsx",
    "pages/ServicesOrderFormsSlot.tsx",
    "platform/entity-workspace/servicesOrderConsumer.ts",
    "platform/entity-workspace/index.ts",
}

_CONSUMER_NEEDLES = (
    "SERVICES_ORDER_COMPOSITION_SLOTS",
    "servicesOrderConsumer",
    "assertServicesOrderCompositionSlots",
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_d9_brief_locks_services_order_consumer() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Services Order Cutover" in text
    assert "Entity Workspace D9 Cutover Gate" in text
    assert "Catalog Passport" in text
    assert "documents" in text
    assert "ServicesPage" in text
    assert "/app/orders" in text
    assert "service_order" in text
    assert "HrHandoffDetailPage" in text
    assert "SalesOrderDetailPage" in text
    assert "named Cutover Gate" in text


def test_d9_services_order_binding_matches_enabled_catalog() -> None:
    src = _CONSUMER_TS.read_text(encoding="utf-8")
    slots = _ts_string_array(src, "SERVICES_ORDER_COMPOSITION_SLOTS")
    assert slots == _EXPECTED_CONSUMER_SLOTS
    assert "documents" not in slots
    assert "SERVICES_ORDER_COMPOSITION_CONSUMER_ID" in src
    assert "service-order" in src
    assert "assertServicesOrderCompositionSlots" in src
    enabled = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"),
        "ENTITY_WORKSPACE_ENABLED_SLOT_IDS",
    )
    assert "documents" in enabled
    assert "documents" not in slots
    assert set(slots).issubset(enabled)


def test_d9_page_composes_d2_slots() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    host = _HOST_TSX.read_text(encoding="utf-8")
    assert "EntityWorkspaceCompositionHost" in page
    assert "SERVICES_ORDER_COMPOSITION_SLOTS" in page
    assert "ServicesOrderCommunicationSlot" in page
    assert "ServicesOrderFormsSlot" in page
    assert "PageShell" in page
    assert 'data-entity-workspace-slot="overview"' in page
    assert 'data-entity-workspace-slot="timeline"' in page
    assert 'data-entity-workspace-slot="context-rail"' in page
    assert 'data-entity-workspace-slot="documents"' not in page
    comm = _COMM_SLOT.read_text(encoding="utf-8")
    assert "listCommunicationThreads" in comm
    assert "entityType: 'service_order'" in comm
    assert "entityType: 'sales_order'" not in comm
    assert "entityType: 'company'" not in comm
    assert "entityType: 'candidate'" not in comm
    forms = _FORMS_SLOT.read_text(encoding="utf-8")
    assert "listFormsPlatformHandlers" in forms
    assert "/platform/forms/handlers" in (
        _REPO_ROOT / "hostflow-frontend" / "src" / "api" / "formsPlatform.ts"
    ).read_text(encoding="utf-8")
    assert "data-entity-workspace-slot" in host
    assert "documents" not in _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"),
        "SERVICES_ORDER_COMPOSITION_SLOTS",
    )


def test_d9_sales_order_handoff_hr_not_cut_over() -> None:
    for path in (_SALES_ORDER_PAGE, _HANDOFF_PAGE, _HR_PAGE, _CANDIDATE_PAGE, _VACANCY_PAGE):
        text = path.read_text(encoding="utf-8")
        for needle in _CONSUMER_NEEDLES:
            assert needle not in text, f"{path.name} must not bind Services order consumer ({needle})"


def test_d9_shell_sections_and_module_tabs_not_collapsed() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    consumer = _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"),
        "SERVICES_ORDER_COMPOSITION_SLOTS",
    )
    assert "contacts" in sections
    assert "contacts" not in consumer
    assert "documents" in sections
    assert "documents" not in consumer
    assert sections != consumer
    page = _PAGE.read_text(encoding="utf-8")
    assert "['overview', 'orders', 'catalog', 'analytics', 'billing']" in page
    assert "tab === 'catalog'" in page
    assert "tab === 'analytics'" in page
    assert "tab === 'billing'" in page
    assert "ENTITY_WORKSPACE_ENABLED_SLOT_IDS" not in page


def test_d9_other_sales_hr_paths_not_cut_over() -> None:
    leaked: list[str] = []
    for path in sorted(_FRONTEND_SRC.rglob("*.ts")) + sorted(_FRONTEND_SRC.rglob("*.tsx")):
        rel = path.relative_to(_FRONTEND_SRC).as_posix()
        if rel in _THIS_CONSUMER_PATHS:
            continue
        lowered = rel.lower()
        if not any(token in lowered for token in ("sales", "hr", "candidate", "vacancy", "client")):
            continue
        text = path.read_text(encoding="utf-8")
        if any(needle in text for needle in _CONSUMER_NEEDLES):
            leaked.append(rel)
    assert not leaked, f"D9 must not cut over other Sales/HR surfaces: {leaked}"


def test_d9_no_entity_catalog_passport_mint() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "entity_workspace.manifest" not in catalog


def test_d9_maturity_entity_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line
        for line in text.splitlines()
        if line.startswith("| **Entity Workspace**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_d9_prior_gates_still_present() -> None:
    assert _D8_BRIEF.is_file()
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
    assert "test_entity_workspace_d9_cutover_gate.py" in ci


def test_d9_product_track_points_at_brief() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "entity-workspace-d9-services-order-cutover.md" in queue
    assert "entity-workspace-d9-services-order-cutover.md" in agents
    assert "entity-workspace-d1-contract-seal.md" in agents
    assert "entity-workspace-d2-composition-contract.md" in agents
    assert "entity-workspace-d8-hr-employee-cutover.md" in agents
    assert "named Cutover Gate" in agents
    assert "Phase E" in queue
    assert "locked" in queue.lower()


def test_d9_gate_filename() -> None:
    assert Path(__file__).name == "test_entity_workspace_d9_cutover_gate.py"
