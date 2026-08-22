"""Documents Platform E2 — Public Contract Gate.

`documents.public_contract.v1` + `documents.hub_adapter_v1` bound.
D2 `documents` catalog enabled; reserved empty.
D3–D7 / D9 consumers still omit `documents` (D8 bind is E3).
Shell nav ≠ D2 slot. Documents Foundation stays 🔄.
No OCR / e-sign / packages product. No Catalog shape rewrite.
E1 and D1–D9 gates remain. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e2-public-contract.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
)
_E1_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e1-contract-seal.md"
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
_CAPABILITY_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "capability-contract.md"
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

_UNBOUND_CONSUMERS = (
    ("salesInquiryConsumer.ts", "SALES_INQUIRY_COMPOSITION_SLOTS"),
    ("candidateConsumer.ts", "CANDIDATE_COMPOSITION_SLOTS"),
    ("clientConsumer.ts", "CLIENT_COMPOSITION_SLOTS"),
    ("salesOrderConsumer.ts", "SALES_ORDER_COMPOSITION_SLOTS"),
    ("vacancyConsumer.ts", "VACANCY_COMPOSITION_SLOTS"),
    ("servicesOrderConsumer.ts", "SERVICES_ORDER_COMPOSITION_SLOTS"),
)

_ENABLED_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "documents",
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


def test_e2_brief_names_contract_and_adapter_ids() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E2" in text
    assert "documents.public_contract.v1" in text
    assert "documents.hub_adapter_v1" in text
    assert "Documents Platform E2 Public Contract Gate" in text
    assert "catalog unlock" in text.lower() or "catalog enable" in text.lower()
    assert "OCR" in text
    assert "HrHandoffDetailPage" in text


def test_e2_public_contract_doc_exists_and_is_catalog_referenced() -> None:
    assert _CONTRACT.is_file()
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" in contract
    assert "documents.hub_adapter_v1" in contract
    assert "list" in contract and "resolve" in contract
    assert "set_resolution" in contract
    assert "owner_summary" in contract
    assert "verification_status" in contract
    assert "list_types" in contract
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert "documents-public-contract.md" in catalog
    assert "documents.public_contract.v1" in catalog
    assert "documents.hub_adapter_v1" in catalog
    assert _CAPABILITY_CONTRACT.is_file()
    cap = _CAPABILITY_CONTRACT.read_text(encoding="utf-8")
    assert "documents-public-contract.md" in cap


def test_e2_delivery_facade_binds_ids_and_is_not_link_sot() -> None:
    src = _DELIVERY.read_text(encoding="utf-8")
    assert 'PUBLIC_CONTRACT_ID = "documents.public_contract.v1"' in src
    assert 'ADAPTER_ID = "documents.hub_adapter_v1"' in src
    assert "list_candidate_documents_via_contract" in src
    assert "not" in src.lower() and "Document Link SoT" in src
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e2-public-contract.md" in hub
    assert "documents-public-contract.md" in hub or "public_contract.v1" in hub


def test_e2_d2_documents_catalog_enabled_reserved_empty() -> None:
    src = _SLOTS_TS.read_text(encoding="utf-8")
    enabled = _ts_string_array(src, "ENTITY_WORKSPACE_ENABLED_SLOT_IDS")
    reserved = _ts_string_array(src, "ENTITY_WORKSPACE_RESERVED_SLOT_IDS")
    catalog = _ts_string_array(src, "ENTITY_WORKSPACE_SLOT_CATALOG")
    assert "documents" in catalog
    assert "documents" in enabled
    assert reserved == ()
    assert enabled == _ENABLED_SLOTS
    assert "platform-reserved" not in src
    assert re.search(r"documents:\s*'platform'", src)


def test_e2_d3_d7_d9_consumers_still_omit_documents() -> None:
    consumer_dir = (
        _REPO_ROOT / "hostflow-frontend" / "src" / "platform" / "entity-workspace"
    )
    for filename, const_name in _UNBOUND_CONSUMERS:
        src = (consumer_dir / filename).read_text(encoding="utf-8")
        slots = _ts_string_array(src, const_name)
        assert "documents" not in slots, filename
        assert "not bind documents slot this slice" in src, filename


def test_e2_shell_documents_nav_is_not_d2_slot() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    slots = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"), "ENTITY_WORKSPACE_SLOT_CATALOG"
    )
    assert "documents" in sections
    assert sections != slots
    assert "compositionSlots.ts" in types_src or "composition slot" in types_src.lower()


def test_e2_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell
    assert "E2" in foundation_cell or "Phase E" in foundation_cell


def test_e2_catalog_shape_unchanged_no_entity_passport() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    assert "| **Owns** |" in catalog
    assert "| **Exposes** |" in catalog


def test_e2_no_ocr_esign_packages_product_unlock() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "OCR" in brief
    assert "e-sign" in brief.lower() or "e-sign" in contract.lower()
    assert "Not public v1" in contract or "Internal / deferred" in contract
    assert "OCR internals" in contract


def test_e2_e1_closed_and_prior_gates_present() -> None:
    e1 = _E1_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e1 or "#270" in e1
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Documents Platform E2 Public Contract Gate" in ci
    assert "test_documents_e2_public_contract_gate.py" in ci
    assert "Entity Workspace D9 Cutover Gate" in ci


def test_e2_product_track_points_at_feat() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e2-public-contract.md" in queue
    assert "documents-platform-e2-public-contract.md" in agents
    assert "named Public Contract Gate" in agents
    assert "E3" in queue


def test_e2_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e2_public_contract_gate.py"
