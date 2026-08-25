"""Documents Platform E8 Canonical Type Bind Gate.

D4 Documents surface display / select / persist uses canonical registry
codes only. R4 aliases are resolve-only, not stored identity.
D4 + D8 stay bound. D3 / D5–D7 / D9 stay unbound.
Not E8-eval. Not CL8. Not Engine v2. Not mass D3–D9 bind.
No Hub request / reminder table. Same adapter; no new public-contract id.
No Catalog `document.requested`. Shell nav ≠ D2 slot. G4 unchanged.
Documents Foundation stays 🔄. No OCR / e-sign / packages product.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from backend.app.document_types.registry import canonical_codes, is_canonical_code
from backend.app.services.document_hub_delivery_contract import (
    E4_LINKED_ENTITY_TYPE,
    _hub_document_view,
    list_canonical_document_type_codes_via_contract,
    list_canonical_types_for_select_via_contract,
    persist_canonical_type_identity_via_contract,
    persist_outstanding_asks_via_contract,
    project_outstanding_asks_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e8-bind.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
)
_E7_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e7-document-requests.md"
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

_ALIAS_IDENTITY = (
    "code95",
    "tacho_card",
    "residence_permit",
    "national_id",
    "psych_tests",
    "driver_certificate",
    "additional_document",
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_e8_bind_brief_locks_canonical_identity() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E8-bind" in text
    assert "Canonical Type Bind" in text
    assert "canonical" in text.lower()
    assert "document-type-legacy-aliases-v1.json" in text
    assert "Documents Platform E8 Canonical Type Bind Gate" in text
    assert "E8-eval" in text
    assert "CL8" in text
    assert "document.requested" in text
    assert "OCR" in text


def test_e8_bind_d4_and_d8_stay_bound_others_omit() -> None:
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


def test_e8_bind_persists_canonical_not_alias() -> None:
    assert persist_canonical_type_identity_via_contract("code95") == (
        "driver_qualification_card"
    )
    assert persist_canonical_type_identity_via_contract("tacho_card") == (
        "tachograph_card"
    )
    assert persist_canonical_type_identity_via_contract("residence_permit") == (
        "residence_card"
    )
    assert persist_canonical_type_identity_via_contract("passport") == "passport"
    assert persist_canonical_type_identity_via_contract("") == ""
    persisted = persist_outstanding_asks_via_contract(
        [
            {"doc_type": "code95", "state": "missing"},
            {"doc_type": "tacho_card", "state": "requested"},
        ],
        linked_entity_type=E4_LINKED_ENTITY_TYPE,
        linked_entity_id="cand-e8-alias",
    )
    assert persisted == [
        {"doc_type": "driver_qualification_card", "state": "missing"},
        {"doc_type": "tachograph_card", "state": "requested"},
    ]
    assert all(is_canonical_code(row["doc_type"]) for row in persisted)
    for alias in _ALIAS_IDENTITY:
        assert alias not in {row["doc_type"] for row in persisted}


def test_e8_bind_display_and_select_are_registry_codes() -> None:
    codes = list_canonical_document_type_codes_via_contract()
    assert codes == set(canonical_codes())
    selectable = list_canonical_types_for_select_via_contract()
    assert selectable == sorted(canonical_codes())
    for alias in _ALIAS_IDENTITY:
        assert alias not in codes
        assert alias not in selectable
    view = _hub_document_view(
        SimpleNamespace(
            id="doc-e8",
            custom_name="",
            doc_type="code95",
            status="approved",
            expires_at=None,
            expire_date=None,
        ),
        SimpleNamespace(
            id="link-e8",
            linked_entity_type=E4_LINKED_ENTITY_TYPE,
            linked_entity_id="cand-e8",
            relation_type="primary",
        ),
    )
    assert view["doc_type"] == "driver_qualification_card"
    asks = project_outstanding_asks_via_contract(
        [{"doc_type": "residence_permit", "status": "missing"}]
    )
    assert all(is_canonical_code(row["doc_type"]) for row in asks)
    assert all(row["doc_type"] != "residence_permit" for row in asks)


def test_e8_bind_proof_surface_uses_canonical_select() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    delivery = _DELIVERY.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    assert "CandidateEntityWorkspacePanel" in page
    assert "EntityWorkspaceCapabilityHost" in panel
    assert "persistCanonicalDocumentType" in owner
    assert "canonicalTypes" in owner
    assert "canonical_types" in owner
    assert 'data-canonical-type-select="true"' in capability
    assert 'data-canonical-type-bind="true"' in capability
    assert 'data-alias-stored-identity="false"' in capability
    assert 'data-e8-bind="true"' in capability
    assert 'data-e8-eval="false"' in capability
    assert 'data-cl8="false"' in capability
    assert "persist_canonical_type_identity_via_contract" in delivery
    assert "list_canonical_types_for_select_via_contract" in delivery
    assert "canonical_types" in api
    assert "hub_adapter_v2" not in delivery
    assert "documents.public_contract.v2" not in delivery
    assert "documents.public_contract.v2" not in api
    for alias in ("code95", "tacho_card", "residence_permit"):
        assert f'value="{alias}"' not in capability
        assert f"'{alias}'" not in capability


def test_e8_bind_no_request_table_no_eval_product() -> None:
    delivery = _DELIVERY.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "pe_document_requirements" not in api
    assert "hr_document_requests" not in api
    assert "applicability" not in delivery.lower() or "E8-eval" in delivery
    assert "ocr_requirement_matching" not in delivery
    assert "packages" not in capability.lower() or "Not" in capability
    models_dir = _REPO_ROOT / "backend" / "app" / "models"
    hub_models = "\n".join(
        path.read_text(encoding="utf-8")
        for path in models_dir.glob("document*.py")
    )
    assert "class DocumentRequest" not in hub_models
    assert "class HubRequest" not in hub_models
    assert "class DocumentReminder" not in hub_models
    assert "document.requested" in contract


def test_e8_bind_shell_documents_nav_is_not_d2_slot() -> None:
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


def test_e8_bind_g4_recruitment_application_unchanged() -> None:
    proof = _PROOF.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    contrib = _CONTRIB.read_text(encoding="utf-8")
    assert "ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace'" in contrib
    assert "ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate'" in contrib
    assert "recruitment_application" not in contrib


def test_e8_bind_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_e8_bind_catalog_shape_unchanged_no_ocr_product() -> None:
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert re.search(r"(?im)^###\s+Documents\b", catalog)
    events_line = next(
        line for line in catalog.splitlines() if "Publishes:" in line and "document." in line
    )
    assert "document.requested" not in events_line
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)
    assert "entity.workspace.public_contract" not in catalog
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" in contract
    assert "OCR internals" in contract
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "e-sign" in brief.lower() or "OCR" in brief
    assert "packages" in brief.lower()


def test_e8_bind_prior_gates_present() -> None:
    e7 = _E7_BRIEF.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e7 or "#287" in e7
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Documents Platform E2 Public Contract Gate" in ci
    assert "Documents Platform E3 First Consumer Bind Gate" in ci
    assert "Documents Platform E4 Candidate Document Link Gate" in ci
    assert "Documents Platform E5 Candidate Storage Bridge Gate" in ci
    assert "Documents Platform E6 Document Expiry Gate" in ci
    assert "Documents Platform E7 Document Requests Gate" in ci
    assert "Documents Platform E8 Canonical Type Bind Gate" in ci
    assert "test_documents_e8_canonical_type_bind_gate.py" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e8-bind.md" in hub


def test_e8_bind_product_track_points_at_e8_bind() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e8-bind.md" in queue
    assert "documents-platform-e8-bind.md" in agents
    assert "canonical" in agents.lower()


def test_e8_bind_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e8_canonical_type_bind_gate.py"
