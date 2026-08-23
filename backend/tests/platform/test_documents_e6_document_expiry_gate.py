"""Documents Platform E6 — Document Expiry Gate.

Validity SoT = Hub `expire_date` / public `expires_at` + engine evaluation
on `documents.hub_adapter_v1`. D4 + D8 stay bound. D3 / D5–D7 / D9 stay
unbound. No Candidate FK in expiry SoT. No Hub reminder / task table.
Same adapter; no new public-contract id. Shell nav ≠ D2 slot. G4 unchanged.
Documents Foundation stays 🔄. No OCR / e-sign / packages product.
No Catalog shape rewrite. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e6-document-expiry.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
)
_WORKFLOW = _REPO_ROOT / "docs" / "specs" / "workflows" / "document_expiry.md"
_E5_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e5-candidate-storage-bridge.md"
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
_ENGINE = (
    _REPO_ROOT / "backend" / "app" / "services" / "document_expiry_engine.py"
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
_PROOF = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "proof.ts"
)
_CONTRIB = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "candidateEntity.ts"
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


def test_e6_brief_locks_hub_expiry() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E6" in text
    assert "Document Expiry" in text or "expiry" in text.lower()
    assert "expires_at" in text
    assert "document.expired" in text
    assert "Documents Platform E6 Document Expiry Gate" in text
    assert "OCR" in text
    assert "reminder" in text.lower()
    assert "candidate_id" in text


def test_e6_d4_and_d8_stay_bound_others_omit() -> None:
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


def test_e6_public_consume_is_hub_expiry_not_candidate_fk() -> None:
    delivery = _DELIVERY.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    engine = _ENGINE.read_text(encoding="utf-8")
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "evaluate_expiry" in delivery
    assert "expiry_state" in delivery
    assert "expires_at" in delivery
    assert "expiry_state" in api
    assert "days_left" in api
    assert "expiry_state" in owner
    assert "expires_at" in capability
    assert "expiry_state" in capability
    assert "def evaluate_expiry" in engine
    assert "documents.candidate_id" in workflow
    assert "does not read Candidate FK" in workflow
    assert "No Document Hub reminder" in workflow
    assert "Ожидаем документы" not in workflow
    assert "expires_at" in contract
    assert "expiry_state" in contract
    assert "document_expiry_engine" in contract
    assert "hub_adapter_v2" not in delivery
    assert "documents.public_contract.v2" not in delivery
    assert "documents.public_contract.v2" not in contract
    models_dir = _REPO_ROOT / "backend" / "app" / "models"
    hub_models = "\n".join(
        path.read_text(encoding="utf-8")
        for path in models_dir.glob("document*.py")
    )
    assert "class DocumentReminder" not in hub_models
    assert "class HubReminder" not in hub_models


def test_e6_proof_surface_uses_capability_host_and_hub_adapter() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "CandidateEntityWorkspacePanel" in page
    assert "EntityWorkspaceCapabilityHost" in panel
    assert "DocumentsCapability" in capability or "documents" in capability
    assert "/platform/documents/resolve" in owner
    assert "documents.public_contract.v1" in owner
    assert "documents.hub_adapter_v1" in owner
    assert 'PUBLIC_CONTRACT_ID = "documents.public_contract.v1"' in delivery
    assert 'ADAPTER_ID = "documents.hub_adapter_v1"' in delivery
    assert "list_entity_link_documents_via_contract" in delivery


def test_e6_shell_documents_nav_is_not_d2_slot() -> None:
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


def test_e6_g4_recruitment_application_unchanged() -> None:
    proof = _PROOF.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    contrib = _CONTRIB.read_text(encoding="utf-8")
    assert "ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace'" in contrib
    assert "ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate'" in contrib
    assert "recruitment_application" not in contrib


def test_e6_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell
    assert "E6" in foundation_cell or "Phase E" in foundation_cell


def test_e6_catalog_shape_unchanged_no_ocr_product() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    assert "document.created" in catalog or "`expired`" in catalog or "expired" in catalog
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" in contract
    assert "OCR internals" in contract
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "e-sign" in brief.lower()
    assert "packages" in brief.lower()


def test_e6_e5_closed_and_prior_gates_present() -> None:
    e5 = _E5_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e5 or "#282" in e5
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Documents Platform E2 Public Contract Gate" in ci
    assert "Documents Platform E3 First Consumer Bind Gate" in ci
    assert "Documents Platform E4 Candidate Document Link Gate" in ci
    assert "Documents Platform E5 Candidate Storage Bridge Gate" in ci
    assert "Documents Platform E6 Document Expiry Gate" in ci
    assert "test_documents_e6_document_expiry_gate.py" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e6-document-expiry.md" in hub


def test_e6_product_track_points_at_e6() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e6-document-expiry.md" in queue
    assert "documents-platform-e6-document-expiry.md" in agents
    assert "expiry" in agents.lower() or "validity" in agents.lower()


def test_e6_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e6_document_expiry_gate.py"
