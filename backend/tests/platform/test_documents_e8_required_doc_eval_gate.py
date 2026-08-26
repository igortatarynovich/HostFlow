"""Documents Platform E8 Required-Doc Evaluation Gate.

D4 Documents surface evaluates required / optional / blocked from R5
``merge(pack, tenant_delta)`` using canonical registry types only.
Overlay is an existing CL7 input (``document_types``), not rewritten.
D4 + D8 stay bound. D3 / D5–D7 / D9 stay unbound.
Not OCR. Not a packages Hub table. Not CL8. Not Engine v2.
Not mass D3–D9 bind. No Hub request / reminder table.
Same adapter; no new public-contract id. No Catalog ``document.requested``.
Does not rewrite CL7 evaluate / Overlay / DR1-runtime / E8-bind identity.
Shell nav ≠ D2 slot. G4 unchanged. Documents Foundation stays 🔄.
No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.document_types.registry import is_canonical_code
from backend.app.services.document_hub_delivery_contract import (
    APPLICABILITY_BLOCKED,
    APPLICABILITY_OPTIONAL,
    APPLICABILITY_REQUIRED,
    ERROR_OCR_PRODUCT,
    ERROR_PACKAGES_TABLE,
    ERROR_SCREENING_AS_REQUIRED,
    evaluate_required_doc_applicability_via_contract,
    persist_canonical_type_identity_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e8-eval.md"
)
_BIND_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e8-bind.md"
)
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "documents-public-contract.md"
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


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\](?:\s*as const)?",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def _by_state(result: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {
        APPLICABILITY_REQUIRED: set(),
        APPLICABILITY_OPTIONAL: set(),
        APPLICABILITY_BLOCKED: set(),
    }
    for row in result.get("applicability") or []:
        out[str(row["applicability"])].add(str(row["doc_type"]))
    return out


def test_e8_eval_brief_locks_required_optional_blocked() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Documents Platform E8-eval" in text
    assert "Required-Doc Evaluation" in text
    assert "required" in text.lower()
    assert "optional" in text.lower()
    assert "blocked" in text.lower()
    assert "merge(pack, tenant_delta)" in text
    assert "Documents Platform E8 Required-Doc Evaluation Gate" in text
    assert "OCR" in text
    assert "CL8" in text
    assert "document.requested" in text
    assert "packages" in text.lower()


def test_e8_eval_d4_and_d8_stay_bound_others_omit() -> None:
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


def test_e8_eval_r5_merge_emits_canonical_required_optional_blocked() -> None:
    defaults = evaluate_required_doc_applicability_via_contract()
    assert defaults["ok"] is True
    by_state = _by_state(defaults)
    assert "passport" in by_state[APPLICABILITY_REQUIRED]
    assert "driver_license" in by_state[APPLICABILITY_REQUIRED]
    assert "medical_certificate" in by_state[APPLICABILITY_OPTIONAL]
    assert all(is_canonical_code(code) for rows in by_state.values() for code in rows)
    assert persist_canonical_type_identity_via_contract("code95") == (
        "driver_qualification_card"
    )

    eu = evaluate_required_doc_applicability_via_contract(
        {"residency_status": "eu_citizen"}
    )
    eu_state = _by_state(eu)
    assert "national_identity_card" in eu_state[APPLICABILITY_REQUIRED]
    assert "passport" in eu_state[APPLICABILITY_BLOCKED]
    assert "visa" in eu_state[APPLICABILITY_BLOCKED]
    assert "passport" not in eu_state[APPLICABILITY_REQUIRED]
    assert all(is_canonical_code(code) for rows in eu_state.values() for code in rows)


def test_e8_eval_overlay_input_adds_canonical_required() -> None:
    result = evaluate_required_doc_applicability_via_contract(
        overlay={"ok": True, "document_types": ["code95", "driver_attestation"]}
    )
    by_state = _by_state(result)
    assert "driver_qualification_card" in by_state[APPLICABILITY_REQUIRED]
    assert "driver_attestation" in by_state[APPLICABILITY_REQUIRED]
    assert "code95" not in by_state[APPLICABILITY_REQUIRED]
    tenant = evaluate_required_doc_applicability_via_contract(
        tenant_delta={
            "vacancy": {
                "additions": [{"when": {}, "require": ["adr_certificate"]}],
            }
        }
    )
    tenant_state = _by_state(tenant)
    assert "adr_certificate" in tenant_state[APPLICABILITY_REQUIRED]


def test_e8_eval_rejects_screening_ocr_packages() -> None:
    screening = evaluate_required_doc_applicability_via_contract(
        {"screening_as_required": True}
    )
    assert screening["ok"] is False
    assert screening["error"] == ERROR_SCREENING_AS_REQUIRED
    ocr = evaluate_required_doc_applicability_via_contract({"ocr_product": True})
    assert ocr["ok"] is False
    assert ocr["error"] == ERROR_OCR_PRODUCT
    packages = evaluate_required_doc_applicability_via_contract(
        {"hub_packages_table": True}
    )
    assert packages["ok"] is False
    assert packages["error"] == ERROR_PACKAGES_TABLE


def test_e8_eval_proof_surface_shows_applicability_vs_hub() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    owner = _OWNER.read_text(encoding="utf-8")
    delivery = _DELIVERY.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    assert "CandidateEntityWorkspacePanel" in page
    assert "EntityWorkspaceCapabilityHost" in panel
    assert "applicability" in owner
    assert "data-applicability=" in capability
    assert "data-hub-linked=" in capability
    assert 'data-e8-eval="true"' in capability
    assert 'data-e8-bind="true"' in capability
    assert 'data-ocr="false"' in capability
    assert 'data-packages-table="false"' in capability
    assert 'data-cl8="false"' in capability
    assert "evaluate_required_doc_applicability_via_contract" in delivery
    assert "project_required_doc_applicability_via_contract" in delivery
    assert "merge_resolved_policy" in delivery
    assert "ApplicabilityOut" in api
    assert "applicability" in api
    assert "hub_adapter_v2" not in delivery
    assert "documents.public_contract.v2" not in delivery
    assert "documents.public_contract.v2" not in api
    assert "from backend.app.entity_profile.engine_eval_runtime" not in delivery
    assert "from backend.app.entity_profile.vacancy_overlay_runtime" not in delivery


def test_e8_eval_no_request_table_no_ocr_product() -> None:
    delivery = _DELIVERY.read_text(encoding="utf-8")
    api = _PUBLIC_API.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "pe_document_requirements" not in api
    assert "hr_document_requests" not in api
    assert "ocr_requirement_matching" not in capability
    models_dir = _REPO_ROOT / "backend" / "app" / "models"
    hub_models = "\n".join(
        path.read_text(encoding="utf-8")
        for path in models_dir.glob("document*.py")
    )
    assert "class DocumentRequest" not in hub_models
    assert "class HubRequest" not in hub_models
    assert "class DocumentReminder" not in hub_models
    assert "class DocumentPackage" not in hub_models
    assert "document.requested" in contract
    assert "hub_adapter_v1" in delivery


def test_e8_eval_shell_documents_nav_is_not_d2_slot() -> None:
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


def test_e8_eval_g4_recruitment_application_unchanged() -> None:
    proof = _PROOF.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    contrib = _CONTRIB.read_text(encoding="utf-8")
    assert "ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace'" in contrib
    assert "ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate'" in contrib
    assert "recruitment_application" not in contrib


def test_e8_eval_maturity_documents_foundation_not_complete() -> None:
    text = _MATURITY.read_text(encoding="utf-8")
    row = next(
        line for line in text.splitlines() if line.startswith("| **Documents**")
    )
    foundation_cell = row.split("|")[2]
    assert "🔄" in foundation_cell
    assert "✅" not in foundation_cell


def test_e8_eval_catalog_shape_unchanged_no_ocr_product() -> None:
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


def test_e8_eval_prior_gates_present() -> None:
    bind = _BIND_BRIEF.read_text(encoding="utf-8")
    assert "**PASS**" in bind or "#321" in bind
    ci = _CI.read_text(encoding="utf-8")
    assert "Documents Platform E7 Document Requests Gate" in ci
    assert "Documents Platform E8 Canonical Type Bind Gate" in ci
    assert "Documents Platform E8 Required-Doc Evaluation Gate" in ci
    assert "test_documents_e8_canonical_type_bind_gate.py" in ci
    assert "test_documents_e8_required_doc_eval_gate.py" in ci
    assert "Entity Workspace D4 Cutover Gate" in ci
    assert "Entity Workspace D8 Cutover Gate" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert _HUB_SCOPE.is_file()
    hub = _HUB_SCOPE.read_text(encoding="utf-8")
    assert "documents-platform-e8-eval.md" in hub


def test_e8_eval_product_track_points_at_e8_eval() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "documents-platform-e8-eval.md" in queue
    assert "documents-platform-e8-eval.md" in agents
    assert "E8-eval" in agents


def test_e8_eval_gate_filename() -> None:
    assert Path(__file__).name == "test_documents_e8_required_doc_eval_gate.py"
