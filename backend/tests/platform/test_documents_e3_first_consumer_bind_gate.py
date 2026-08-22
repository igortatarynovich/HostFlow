"""Documents Platform E3 — First Consumer Bind Gate.

D8 binds `documents` through Capability Host + `documents.hub_adapter_v1`.
Consume path = Document Link (`document_entity_links`).
D3–D7 / D9 stay unbound. `candidate_id` remains a legacy bridge.
Shell nav ≠ D2 slot. G4 unchanged. Documents Foundation stays 🔄.
No OCR / e-sign / packages product. No Catalog shape rewrite.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e3-first-consumer-bind.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
)
_E2_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e2-public-contract.md"
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
    / "hrEmployeeConsumer.ts"
)
_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "hr"
    / "HrEmployeeDetailPage.tsx"
)
_CONTRIB = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "hrEmployeeEntity.ts"
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
_CANDIDATE_ENTITY = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "candidateEntity.ts"
)
_LOCAL_DOCS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "hr"
    / "HrEmployeeDocumentsSection.tsx"
)

_UNBOUND_CONSUMERS = (
    ("salesInquiryConsumer.ts", "SALES_INQUIRY_COMPOSITION_SLOTS"),
    ("candidateConsumer.ts", "CANDIDATE_COMPOSITION_SLOTS"),
    ("clientConsumer.ts", "CLIENT_COMPOSITION_SLOTS"),
    ("salesOrderConsumer.ts", "SALES_ORDER_COMPOSITION_SLOTS"),
    ("vacancyConsumer.ts", "VACANCY_COMPOSITION_SLOTS"),
    ("servicesOrderConsumer.ts", "SERVICES_ORDER_COMPOSITION_SLOTS"),
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


def test_e3_brief_locks_hr_employee_and_link_sot() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E3" in text
    assert "HR employee" in text
    assert "document_entity_links" in text
    assert "workforce_employee" in text
    assert "reused_for_hr" in text
    assert "Documents Platform E3 First Consumer Bind Gate" in text
    assert "HrHandoffDetailPage" in text
    assert "OCR" in text
    assert "candidate_id" in text


def test_e3_d8_consumer_binds_documents_others_omit() -> None:
    src = _CONSUMER_TS.read_text(encoding="utf-8")
    slots = _ts_string_array(src, "HR_EMPLOYEE_COMPOSITION_SLOTS")
    assert slots == _D8_SLOTS
    assert "documents" in slots
    consumer_dir = (
        _REPO_ROOT / "hostflow-frontend" / "src" / "platform" / "entity-workspace"
    )
    for filename, const_name in _UNBOUND_CONSUMERS:
        other = (consumer_dir / filename).read_text(encoding="utf-8")
        other_slots = _ts_string_array(other, const_name)
        assert "documents" not in other_slots, filename
        assert "not bind documents slot this slice" in other, filename


def test_e3_proof_surface_uses_capability_host_and_hub_adapter() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    contrib = _CONTRIB.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    renderers = _RENDERERS.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "EntityWorkspaceCapabilityHost" in page
    assert "HR_EMPLOYEE_ENTITY_HOST_CONTRIBUTIONS" in page
    assert "HrEmployeeDocumentsSection" not in page
    assert "listWorkforceEmployeeDocuments" not in page
    assert "capability_id: 'documents'" in contrib
    assert "consumer: 'hr-employee'" in contrib
    assert "workspace.surface.documents" in contrib
    assert "DocumentsCapability" in renderers
    assert "listLinkedDocuments" in capability
    assert "from '../HrEmployeeDocumentsSection'" not in capability
    assert "listWorkforceEmployeeDocuments" not in owner
    assert "/platform/documents/resolve" in owner
    assert "documents.public_contract.v1" in owner
    assert "documents.hub_adapter_v1" in owner
    assert "workforce_employee" in owner
    assert "reused_for_hr" in owner
    assert 'PUBLIC_CONTRACT_ID = "documents.public_contract.v1"' in delivery
    assert 'ADAPTER_ID = "documents.hub_adapter_v1"' in delivery
    assert "list_entity_link_documents_via_contract" in delivery
    assert "list_entity_link_documents_via_contract" in api
    assert "document_entity_links" in delivery or "DocumentEntityLink" in delivery
    assert 'E3_LINKED_ENTITY_TYPE = "workforce_employee"' in delivery
    assert 'E3_RELATION_TYPE = "reused_for_hr"' in delivery
    assert "hub_adapter_v2" not in delivery
    assert "documents.public_contract.v2" not in delivery
    assert "documents.public_contract.v2" not in _CONTRACT.read_text(encoding="utf-8")


def test_e3_candidate_id_remains_legacy_bridge() -> None:
    model = _DOCUMENT_MODEL.read_text(encoding="utf-8")
    assert "candidate_id" in model
    assert "nullable=False" in model
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "legacy" in delivery.lower()
    assert "bridge" in delivery.lower()
    local = _LOCAL_DOCS.read_text(encoding="utf-8")
    assert "Not the D2" in local or "not the D2" in local


def test_e3_shell_documents_nav_is_not_d2_slot() -> None:
    types_src = _TYPES_TS.read_text(encoding="utf-8")
    sections = _ts_string_array(types_src, "ENTITY_WORKSPACE_SECTION_ORDER")
    slots = _ts_string_array(
        _SLOTS_TS.read_text(encoding="utf-8"), "ENTITY_WORKSPACE_SLOT_CATALOG"
    )
    consumer = _ts_string_array(
        _CONSUMER_TS.read_text(encoding="utf-8"), "HR_EMPLOYEE_COMPOSITION_SLOTS"
    )
    assert "documents" in sections
    assert "documents" in slots
    assert "documents" in consumer
    assert sections != slots
    assert "contacts" in sections
    assert "contacts" not in consumer


def test_e3_g4_recruitment_application_unchanged() -> None:
    proof = _PROOF.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    candidate = _CANDIDATE_ENTITY.read_text(encoding="utf-8")
    assert "documents" not in candidate.split("CANDIDATE_ENTITY_HOST_CONTRIBUTIONS", 1)[1]


def test_e3_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell
    assert "E3" in foundation_cell or "Phase E" in foundation_cell


def test_e3_catalog_shape_unchanged_no_ocr_product() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" in contract
    assert "list_entity_link_documents_via_contract" in contract
    assert "OCR internals" in contract
    assert "workforce_employee" in contract
    assert "reused_for_hr" in contract
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "e-sign" in brief.lower()
    assert "packages" in brief.lower()


def test_e3_e2_closed_and_prior_gates_present() -> None:
    e2 = _E2_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e2 or "#276" in e2
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Documents Platform E2 Public Contract Gate" in ci
    assert "Documents Platform E3 First Consumer Bind Gate" in ci
    assert "test_documents_e3_first_consumer_bind_gate.py" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e3-first-consumer-bind.md" in hub


def test_e3_product_track_points_at_feat() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e3-first-consumer-bind.md" in queue
    assert "documents-platform-e3-first-consumer-bind.md" in agents
    assert "named First Consumer Bind Gate" in agents or "First Consumer Bind" in agents
    assert "E4" in queue


def test_e3_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e3_first_consumer_bind_gate.py"
