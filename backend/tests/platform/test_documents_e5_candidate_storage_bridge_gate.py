"""Documents Platform E5 — Candidate Storage Bridge Gate.

D4 + D8 stay bound through Capability Host + `documents.hub_adapter_v1`.
Consume path = Document Link (`document_entity_links`, `candidate` / `primary`
and `workforce_employee` / `reused_for_hr`). `documents.candidate_id` column
is dropped. Writers persist Hub links. D3 / D5–D7 / D9 stay unbound.
Shell nav ≠ D2 slot. G4 unchanged. Documents Foundation stays 🔄.
No OCR / e-sign / packages product. No Catalog shape rewrite.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e5-candidate-storage-bridge.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
)
_E4_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e4-candidate-document-link.md"
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
_DOCUMENT_MODEL = _REPO_ROOT / "backend" / "app" / "models" / "document.py"
_ALEMBIC = (
    _REPO_ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "202608250001_drop_documents_candidate_id.py"
)
_PUBLIC_API = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "api"
    / "v1"
    / "platform"
    / "documents_public.py"
)
_CONSUMER_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "candidateConsumer.ts"
)
_D8_CONSUMER_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "hrEmployeeConsumer.ts"
)
_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "CandidateEntityWorkspacePage.tsx"
)
_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEntityWorkspacePanel.tsx"
)
_CONTRIB = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "candidateEntity.ts"
)
_CAPABILITY = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "documents"
    / "DocumentsCapability.tsx"
)
_OWNER = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "documents"
    / "documentsOwner.ts"
)
_RENDERERS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "renderers.ts"
)
_PROOF = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "proof.ts"
)

_UNBOUND_CONSUMERS = (
    ("salesInquiryConsumer.ts", "SALES_INQUIRY_COMPOSITION_SLOTS"),
    ("clientConsumer.ts", "CLIENT_COMPOSITION_SLOTS"),
    ("salesOrderConsumer.ts", "SALES_ORDER_COMPOSITION_SLOTS"),
    ("vacancyConsumer.ts", "VACANCY_COMPOSITION_SLOTS"),
    ("servicesOrderConsumer.ts", "SERVICES_ORDER_COMPOSITION_SLOTS"),
)

_D4_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "documents",
    "context-rail",
)

_D8_SLOTS = (
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


def test_e5_brief_locks_storage_bridge_retirement() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E5" in text
    assert "candidate_id" in text
    assert "document_entity_links" in text
    assert "Documents Platform E5 Candidate Storage Bridge Gate" in text
    assert "OCR" in text
    assert "nullable leftover" in text.lower() or "Dropped" in text or "drop" in text.lower()


def test_e5_d4_and_d8_stay_bound_others_omit() -> None:
    src = _CONSUMER_TS.read_text(encoding="utf-8")
    slots = _ts_string_array(src, "CANDIDATE_COMPOSITION_SLOTS")
    assert slots == _D4_SLOTS
    assert "documents" in slots
    d8 = _D8_CONSUMER_TS.read_text(encoding="utf-8")
    d8_slots = _ts_string_array(d8, "HR_EMPLOYEE_COMPOSITION_SLOTS")
    assert d8_slots == _D8_SLOTS
    assert "documents" in d8_slots
    consumer_dir = (
        _REPO_ROOT / "hostflow-frontend" / "src" / "platform" / "entity-workspace"
    )
    for filename, const_name in _UNBOUND_CONSUMERS:
        other = (consumer_dir / filename).read_text(encoding="utf-8")
        other_slots = _ts_string_array(other, const_name)
        assert "documents" not in other_slots, filename
        assert "not bind documents slot this slice" in other, filename


def test_e5_candidate_id_column_dropped_writers_mint_hub_links() -> None:
    model = _DOCUMENT_MODEL.read_text(encoding="utf-8")
    assert not re.search(r"candidate_id:\s*Mapped\[str\]\s*=\s*mapped_column", model)
    assert "column_property" in model
    assert "_pending_candidate_id" in model
    assert "after_insert" in model or "_mint_candidate_primary_link" in model
    assert _ALEMBIC.is_file()
    alembic = _ALEMBIC.read_text(encoding="utf-8")
    assert "drop_column" in alembic
    assert "candidate_id" in alembic
    assert "document_entity_links" in alembic
    assert "'candidate'" in alembic or '"candidate"' in alembic
    assert "'primary'" in alembic or '"primary"' in alembic
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "ensure_candidate_primary_document_links" not in delivery
    assert "list_entity_link_documents_via_contract" in delivery
    assert "list_candidate_documents_via_contract" in delivery
    owner = _OWNER.read_text(encoding="utf-8")
    assert "list_candidate_documents_via_contract" not in owner
    assert "/platform/documents/resolve" in owner


def test_e5_proof_surface_uses_capability_host_and_hub_adapter() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    contrib = _CONTRIB.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    renderers = _RENDERERS.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "CandidateEntityWorkspacePanel" in page
    assert "EntityWorkspaceCapabilityHost" in panel
    assert "CANDIDATE_ENTITY_HOST_CONTRIBUTIONS" in panel
    assert "CandidateDocsWorkspacePanel" not in panel
    assert "capability_id: 'documents'" in contrib
    assert "consumer: 'candidate'" in contrib
    assert "workspace.surface.documents" in contrib
    assert "DocumentsCapability" in renderers
    assert "listLinkedDocuments" in capability
    assert "/platform/documents/resolve" in owner
    assert "documents.public_contract.v1" in owner
    assert "documents.hub_adapter_v1" in owner
    assert 'PUBLIC_CONTRACT_ID = "documents.public_contract.v1"' in delivery
    assert 'ADAPTER_ID = "documents.hub_adapter_v1"' in delivery
    assert "list_entity_link_documents_via_contract" in delivery
    assert "list_entity_link_documents_via_contract" in api
    assert 'E4_LINKED_ENTITY_TYPE = "candidate"' in delivery
    assert 'E4_RELATION_TYPE = "primary"' in delivery
    assert 'E3_LINKED_ENTITY_TYPE = "workforce_employee"' in delivery
    assert "ALLOWED_ENTITY_LINK_RESOLVE" in delivery
    assert "hub_adapter_v2" not in delivery
    assert "documents.public_contract.v2" not in delivery
    assert "documents.public_contract.v2" not in _CONTRACT.read_text(encoding="utf-8")


def test_e5_shell_documents_nav_is_not_d2_slot() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    slots = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"), "ENTITY_WORKSPACE_SLOT_CATALOG"
    )
    consumer = _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"), "CANDIDATE_COMPOSITION_SLOTS"
    )
    assert "documents" in sections
    assert "documents" in slots
    assert "documents" in consumer
    assert sections != slots
    assert sections != consumer
    assert "contacts" in sections
    assert "contacts" not in consumer


def test_e5_g4_recruitment_application_unchanged() -> None:
    proof = _PROOF.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    contrib = _CONTRIB.read_text(encoding="utf-8")
    assert "ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace'" in contrib
    assert "ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate'" in contrib
    assert "recruitment_application" not in contrib


def test_e5_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell
    assert "E5" in foundation_cell or "Phase E" in foundation_cell


def test_e5_catalog_shape_unchanged_no_ocr_product() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" in contract
    assert "list_entity_link_documents_via_contract" in contract
    assert "OCR internals" in contract
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "e-sign" in brief.lower()
    assert "packages" in brief.lower()


def test_e5_e4_closed_and_prior_gates_present() -> None:
    e4 = _E4_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e4 or "#280" in e4
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Documents Platform E2 Public Contract Gate" in ci
    assert "Documents Platform E3 First Consumer Bind Gate" in ci
    assert "Documents Platform E4 Candidate Document Link Gate" in ci
    assert "Documents Platform E5 Candidate Storage Bridge Gate" in ci
    assert "test_documents_e5_candidate_storage_bridge_gate.py" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e5-candidate-storage-bridge.md" in hub


def test_e5_product_track_points_at_e5() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e5-candidate-storage-bridge.md" in queue
    assert "documents-platform-e5-candidate-storage-bridge.md" in agents
    assert "storage-bridge" in agents.lower() or "candidate_id" in agents


def test_e5_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e5_candidate_storage_bridge_gate.py"
