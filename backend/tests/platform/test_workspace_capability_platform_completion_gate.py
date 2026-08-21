"""Workspace Capability Platform Completion Gate.

Typed host / capability / contribution contracts plus the platform kit
(data types, fields, primitives, widgets, tables). Four classes stay
separate catalogs. Renderer registry is technical only. Not a RODO slice.
G4 bind: Recruitment Application via ApplicationWorkspaceCapabilityHost.
D2 `documents` stays reserved. No Postgres required.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.platform.workspace_capability.capability import (
    PLATFORM_SURFACE_CAPABILITIES,
    SHELL_PRIMITIVE_CAPABILITIES,
    all_capability_ids,
    assert_no_rodo_capability_id,
)
from backend.app.platform.workspace_capability.catalogs import (
    MODULE_CONTRIBUTION_IDS,
    PLATFORM_SURFACE_IDS,
    SHARED_CAPABILITY_IDS,
    SHELL_PRIMITIVE_IDS,
    WORKSPACE_CAPABILITY_CLASS_IDS,
)
from backend.app.platform.workspace_capability.contribution import (
    REFERENCE_FIELD_CANONS,
    WORKSPACE_CONTRIBUTION_FIELD_KEYS,
)
from backend.app.platform.workspace_capability.hosts import (
    APPLICATION_WORKSPACE_HOST,
    ENTITY_WORKSPACE_HOST,
    WORKSPACE_CAPABILITY_HOST_IDS,
    WORKSPACE_HOST_REGION_IDS,
)
from backend.app.platform.workspace_capability.kit import (
    KIT_CANDIDATE_FIELD_COUNT,
    KIT_DATA_TYPE_IDS,
    KIT_FIELD_SOT,
    KIT_HARDENING_PRIMITIVE_IDS,
    KIT_HOST_NAVIGATION_SOT,
    KIT_LAYER_ORDER,
    KIT_LIST_WORKSPACE_ZONE_IDS,
    KIT_PROOF_BLOCKER_PRIMITIVE_IDS,
    KIT_REGISTERED_FIELD_COUNT,
    KIT_SALES_UNCANONICAL_TYPE_COUNT,
    KIT_TABLE_FRAME_IDS,
    KIT_UI_PRIMITIVE_IDS,
    KIT_WIDGET_CLASS_IDS,
    KIT_WIDGET_GAP_IDS,
)
from backend.app.platform.workspace_capability.proof import (
    PROOF_CONSUMER_ID,
    PROOF_HOST_ID,
    RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS,
)
from backend.app.platform.workspace_capability.registry import (
    WORKSPACE_RENDERER_REGISTRY,
    WORKSPACE_RENDERER_REGISTRATION_KEYS,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "workspace-capability-platform-completion.md"
)
_INVENTORY = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "workspace-capability-legacy-inventory.md"
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
_CATALOGS_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "catalogs.ts"
)
_HOSTS_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "hosts.ts"
)
_CONTRIBUTION_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "contribution.ts"
)
_KIT_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "kit.ts"
)
_FIELD_REGISTRY_CANON = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "platform"
    / "field-registry-card-configuration.md"
)
_PRIMITIVES_V1 = _REPO_ROOT / "docs" / "specs" / "frontend" / "PRIMITIVES_V1.md"
_TABLE_V1 = _REPO_ROOT / "docs" / "specs" / "frontend" / "TABLE_V1.md"
_REGISTRY_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "registry.ts"
)
_CAPABILITY_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "capability.ts"
)
_PROOF_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "proof.ts"
)
_SHELL_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "EntityWorkspaceShell.tsx"
)
_APPLICATION_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "application-workspace"
    / "ApplicationWorkspace.tsx"
)
_RECRUITMENT_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "application-workspace"
    / "ApplicationRecruitmentDetailPanel.tsx"
)
_CHECKBOX_TS = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "components" / "ui" / "Checkbox.tsx"
)
_CHECKBOX_V1 = _REPO_ROOT / "docs" / "specs" / "frontend" / "CHECKBOX_V1.md"
_CONSENT_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "consent"
    / "ConsentCapability.tsx"
)
_NOTES_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "notes"
    / "NotesCapability.tsx"
)
_CAPABILITY_HOST_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "ApplicationWorkspaceCapabilityHost.tsx"
)
_ENTITY_CAPABILITY_HOST_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "EntityWorkspaceCapabilityHost.tsx"
)
_RECRUITMENT_CONTRIB_DIR = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "modules" / "recruitment" / "contributions"
)
_RECRUITMENT_WORKSPACE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "recruitment"
    / "RecruitmentApplicationWorkspace.tsx"
)
_CATALOG = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "platform-capability-catalog.md"
)

_ENABLED_SLOTS = (
    "overview",
    "timeline",
    "communication",
    "forms",
    "context-rail",
)
_RESERVED_SLOTS = ("documents",)

_HOST_FORBIDDEN_IMPORTS = (
    "CandidateRodoSection",
    "SalesInquiryRodoSection",
    "SalesInquiryCallNotesSection",
    "NotesCapability",
    "ConsentCapability",
)

_PROOF_SURFACE_LOCAL_BLOCKS = (
    "CandidateRodoSection",
    "SalesInquiryRodoSection",
    "SalesInquiryCallNotesSection",
    "ApplicationCommentsSection",
    "ApplicationRodoSection",
    "CandidateNotesSection",
)

_REGISTRY_FORBIDDEN_KEYS = (
    "owner",
    "state_owner",
    "host",
    "placement",
    "class",
    "capability_id",
    "permissions",
    "actions",
    "events",
    "license",
    "consumer",
)


def _ts_string_array(src: str, const_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"export const {const_name}(?:\s*:\s*[^=]+)?\s*=\s*\[(.*?)\]\s*as const",
        src,
        re.S,
    )
    assert match, f"missing {const_name}"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_gate_filename() -> None:
    assert Path(__file__).name == "test_workspace_capability_platform_completion_gate.py"


def test_hosts_are_two_constitution_types() -> None:
    assert WORKSPACE_CAPABILITY_HOST_IDS == (
        "entity_workspace",
        "application_workspace",
    )
    assert ENTITY_WORKSPACE_HOST["constitution"] == "§3.3"
    assert APPLICATION_WORKSPACE_HOST["constitution"] == "§3.2"
    assert ENTITY_WORKSPACE_HOST["host"] != APPLICATION_WORKSPACE_HOST["host"]
    hosts_ts = _HOSTS_TS.read_text(encoding="utf-8")
    assert _ts_string_array(hosts_ts, "WORKSPACE_CAPABILITY_HOST_IDS") == (
        "entity_workspace",
        "application_workspace",
    )
    assert _ts_string_array(hosts_ts, "WORKSPACE_HOST_REGION_IDS") == WORKSPACE_HOST_REGION_IDS
    assert "platform_slot" in WORKSPACE_HOST_REGION_IDS
    assert "Do not fold" in hosts_ts or "do not fold" in hosts_ts.lower()


def test_four_classes_are_separate_catalogs_not_flat_enum() -> None:
    assert WORKSPACE_CAPABILITY_CLASS_IDS == (
        "shell_primitive",
        "shared_capability",
        "platform_surface",
        "module_contribution",
    )
    catalogs = _CATALOGS_TS.read_text(encoding="utf-8")
    assert _ts_string_array(catalogs, "SHELL_PRIMITIVE_IDS") == SHELL_PRIMITIVE_IDS
    assert _ts_string_array(catalogs, "SHARED_CAPABILITY_IDS") == SHARED_CAPABILITY_IDS
    assert _ts_string_array(catalogs, "PLATFORM_SURFACE_IDS") == PLATFORM_SURFACE_IDS
    assert _ts_string_array(catalogs, "MODULE_CONTRIBUTION_IDS") == MODULE_CONTRIBUTION_IDS
    assert "export enum" not in catalogs
    assert "WORKSPACE_CAPABILITY_IDS" not in catalogs
    assert "not one flat enum" in catalogs
    capability_ts = _CAPABILITY_TS.read_text(encoding="utf-8")
    assert "ShellPrimitiveCapability" in capability_ts
    assert "SharedCapabilityDefinition" in capability_ts
    assert "PlatformSurfaceCapability" in capability_ts
    assert "ModuleCapabilityDefinition" in capability_ts
    assert "projection: 'owner_status'" in capability_ts
    assert SHELL_PRIMITIVE_CAPABILITIES["status"]["projection"] == "owner_status"


def _field_types_from_canon() -> tuple[str, ...]:
    text = _FIELD_REGISTRY_CANON.read_text(encoding="utf-8")
    section = text.split("## 4. Field types", 1)[1]
    table = section.split("**Reference-backed", 1)[0]
    return tuple(re.findall(r"\|\s+`([^`]+)`\s+\|", table))


def test_platform_kit_is_substrate_not_rodo_slice() -> None:
    assert KIT_LAYER_ORDER == (
        "data_types",
        "fields",
        "ui_primitives",
        "widgets",
        "tables",
        "hosts",
    )
    assert _field_types_from_canon() == KIT_DATA_TYPE_IDS
    kit_ts = _KIT_TS.read_text(encoding="utf-8")
    assert _ts_string_array(kit_ts, "KIT_DATA_TYPE_IDS") == KIT_DATA_TYPE_IDS
    assert _ts_string_array(kit_ts, "KIT_UI_PRIMITIVE_IDS") == KIT_UI_PRIMITIVE_IDS
    assert _ts_string_array(kit_ts, "KIT_TABLE_FRAME_IDS") == KIT_TABLE_FRAME_IDS
    assert _ts_string_array(kit_ts, "KIT_WIDGET_CLASS_IDS") == KIT_WIDGET_CLASS_IDS
    assert "notes" in KIT_WIDGET_CLASS_IDS
    assert "consent" in KIT_WIDGET_CLASS_IDS
    assert "data_table" in KIT_WIDGET_CLASS_IDS
    assert "field_row" in KIT_WIDGET_CLASS_IDS
    assert len(KIT_WIDGET_CLASS_IDS) == 16
    assert "filter_bar" not in KIT_WIDGET_GAP_IDS
    assert "tabs" not in KIT_WIDGET_GAP_IDS
    assert "tabs" not in KIT_WIDGET_CLASS_IDS
    assert _ts_string_array(kit_ts, "KIT_LIST_WORKSPACE_ZONE_IDS") == KIT_LIST_WORKSPACE_ZONE_IDS
    assert KIT_LIST_WORKSPACE_ZONE_IDS == (
        "search",
        "filters",
        "sort",
        "pagination",
        "bulk",
        "saved_views",
    )
    assert "checkbox" in KIT_UI_PRIMITIVE_IDS
    assert KIT_PROOF_BLOCKER_PRIMITIVE_IDS == ()
    assert _ts_string_array(kit_ts, "KIT_PROOF_BLOCKER_PRIMITIVE_IDS") == KIT_PROOF_BLOCKER_PRIMITIVE_IDS
    assert "input_runtime" in KIT_HARDENING_PRIMITIVE_IDS
    assert KIT_WIDGET_GAP_IDS == ("modal", "radio", "toggle")
    assert "EntityWorkspaceNavTabs" in KIT_HOST_NAVIGATION_SOT
    assert "ListWorkspaceStatusTabs" in KIT_HOST_NAVIGATION_SOT
    assert "not a kit widget" in kit_ts or "not a kit widget" in KIT_HOST_NAVIGATION_SOT.lower() + kit_ts
    assert KIT_FIELD_SOT.endswith("field-registry-card-configuration.md")
    assert "KIT_DATA_TYPE_IDS" in kit_ts
    assert "second dictionary" in kit_ts or "no second dictionary" in kit_ts
    primitives = _PRIMITIVES_V1.read_text(encoding="utf-8")
    assert "StatusBadge" in primitives
    assert "CHIP_V1" in primitives or "Chip" in primitives
    assert "BUTTON_V1" in primitives or "Button" in primitives
    assert "INPUT_V1" in primitives
    assert "SELECT_V1" in primitives or "Select" in primitives
    assert "SELECT_V1" in primitives or "Select" in primitives
    assert "CHECKBOX_V1" in primitives or "Checkbox" in primitives
    assert _TABLE_V1.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "KIT_DATA_TYPE_IDS" in brief or "Platform kit catalogs" in brief
    assert "PRIMITIVES_V1" in brief
    assert "TABLE_V1" in brief
    assert "Field Registry" in brief
    assert "Notes/Consent/RODO" in brief or "not a Notes/Consent" in brief
    assert "16 data types" in brief
    assert "78 fields" in brief
    assert "filter_bar is not a gap" in brief
    assert "tabs is not a kit id" in brief
    assert "checkbox" in brief
    assert "input_runtime" in brief


def test_registered_field_counts_match_manifests() -> None:
    from backend.app.field_registry.manifests.crm import crm_client_fields
    from backend.app.field_registry.manifests.fleet import fleet_vehicle_fields
    from backend.app.field_registry.manifests.hr import hr_employee_fields
    from backend.app.field_registry.manifests.platform import platform_identity_fields
    from backend.app.field_registry.manifests.recruitment import (
        recruitment_candidate_fields,
        recruitment_vacancy_fields,
    )
    from backend.app.field_registry.manifests.service_sales import (
        service_sales_targeted_advertising_fields,
    )

    identity = platform_identity_fields()
    candidate = recruitment_candidate_fields()
    vacancy = recruitment_vacancy_fields()
    client = crm_client_fields()
    hr = hr_employee_fields()
    fleet = fleet_vehicle_fields()
    sales = service_sales_targeted_advertising_fields()
    registered = identity + candidate + vacancy + client + hr + fleet + sales
    uncanonical = [
        row for row in sales if row["field_type"] in {"single_select", "multi_select"}
    ]
    assert len(candidate) == KIT_CANDIDATE_FIELD_COUNT == 18
    assert any(row["qualified_code"].endswith("operations.stage") for row in candidate)
    assert len(uncanonical) == KIT_SALES_UNCANONICAL_TYPE_COUNT == 18
    assert len(registered) == KIT_REGISTERED_FIELD_COUNT == 78
    kit_ts = _KIT_TS.read_text(encoding="utf-8")
    assert f"KIT_REGISTERED_FIELD_COUNT = {KIT_REGISTERED_FIELD_COUNT}" in kit_ts
    assert f"KIT_CANDIDATE_FIELD_COUNT = {KIT_CANDIDATE_FIELD_COUNT}" in kit_ts
    assert f"KIT_SALES_UNCANONICAL_TYPE_COUNT = {KIT_SALES_UNCANONICAL_TYPE_COUNT}" in kit_ts


def test_list_workspace_owns_filters_not_filter_bar_widget() -> None:
    toolbar = (
        _REPO_ROOT
        / "hostflow-frontend"
        / "src"
        / "platform"
        / "data-table"
        / "ListWorkspaceToolbar.tsx"
    )
    rail = (
        _REPO_ROOT
        / "hostflow-frontend"
        / "src"
        / "platform"
        / "data-table"
        / "DataTableWithDetailRail.tsx"
    )
    nav = (
        _REPO_ROOT
        / "hostflow-frontend"
        / "src"
        / "platform"
        / "entity-workspace"
        / "EntityWorkspaceZones.tsx"
    )
    assert toolbar.is_file()
    assert "ListWorkspaceToolbar" in toolbar.read_text(encoding="utf-8")
    assert "ListWorkspaceStatusTabs" in toolbar.read_text(encoding="utf-8")
    rail_src = rail.read_text(encoding="utf-8")
    assert "filterRow" in rail_src
    assert "statusTabs" in rail_src
    assert "bulkBar" in rail_src
    assert "export function EntityWorkspaceNavTabs" in nav.read_text(encoding="utf-8")
    assert "tabs" not in KIT_WIDGET_CLASS_IDS
    assert "filter_bar" not in KIT_WIDGET_GAP_IDS
    assert "filter_bar" not in KIT_WIDGET_CLASS_IDS


def test_g4_is_separation_not_catalog_rows() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "semantic owner remains Notes / Compliance" in brief
    assert "ApplicationCommentsSection" in brief
    assert "ApplicationRodoSection" in brief
    assert "input type=checkbox" in brief or "input type=\"checkbox\"" in brief
    proof_ts = _PROOF_TS.read_text(encoding="utf-8")
    assert "host only places" in proof_ts
    assert "checkbox primitive" in proof_ts
    inventory = _INVENTORY.read_text(encoding="utf-8")
    assert "G4 bind rules" in inventory
    assert "checkbox" in inventory
    assert "ListWorkspace zones" in inventory


def test_no_rodo_capability_and_no_global_status_enum() -> None:
    assert_no_rodo_capability_id()
    assert "rodo" not in all_capability_ids()
    catalogs = _CATALOGS_TS.read_text(encoding="utf-8")
    assert "'rodo'" not in catalogs
    assert '"rodo"' not in catalogs
    capability_ts = _CAPABILITY_TS.read_text(encoding="utf-8")
    assert "enum Status" not in capability_ts
    assert "GLOBAL_STATUS" not in capability_ts
    assert "projection" in capability_ts


def test_contribution_fields_include_host_and_class_as_references() -> None:
    assert "host" in WORKSPACE_CONTRIBUTION_FIELD_KEYS
    assert "class" in WORKSPACE_CONTRIBUTION_FIELD_KEYS
    for key in ("permissions", "actions", "events", "license"):
        assert key in WORKSPACE_CONTRIBUTION_FIELD_KEYS
        assert key in REFERENCE_FIELD_CANONS
    src = _CONTRIBUTION_TS.read_text(encoding="utf-8")
    assert _ts_string_array(src, "WORKSPACE_CONTRIBUTION_FIELD_KEYS") == (
        WORKSPACE_CONTRIBUTION_FIELD_KEYS
    )
    assert "ADR-036" in src
    assert "ADR-004" in src
    assert "already-shipped named actions" in src
    assert "not local vocabularies" in src
    assert "ShellPrimitiveContribution" in src
    assert "SharedCapabilityContribution" in src


def test_registry_is_technical_lookup_only() -> None:
    src = _REGISTRY_TS.read_text(encoding="utf-8")
    assert "technical resolution only" in src.lower() or "Technical resolution only" in src
    assert "Not the platform" in src or "not the platform" in src
    assert _ts_string_array(src, "WORKSPACE_RENDERER_REGISTRATION_KEYS") == (
        WORKSPACE_RENDERER_REGISTRATION_KEYS
    )
    assert WORKSPACE_RENDERER_REGISTRATION_KEYS == ("component_id", "renderer_module")
    for entry in WORKSPACE_RENDERER_REGISTRY.values():
        assert set(entry) == {"component_id", "renderer_module"}
        for forbidden in _REGISTRY_FORBIDDEN_KEYS:
            assert forbidden not in entry
    assert "workspace.shared.notes" in WORKSPACE_RENDERER_REGISTRY
    assert "workspace.shared.consent" in WORKSPACE_RENDERER_REGISTRY
    assert "workspace.module.recruitment.stage" in WORKSPACE_RENDERER_REGISTRY


def test_proof_consumer_frozen_and_g4_bound() -> None:
    assert PROOF_CONSUMER_ID == "recruitment_application"
    assert PROOF_HOST_ID == "application_workspace"
    proof_ts = _PROOF_TS.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof_ts
    assert "PROOF_HOST_ID = 'application_workspace'" in proof_ts
    ids = {row["capability_id"] for row in RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS}
    assert ids >= {
        "identity",
        "status",
        "notes",
        "consent",
        "recruitment.stage",
        "recruitment.vacancy",
        "recruitment.assignee",
        "fixture.optional_addon",
    }
    licenses = {row["license"] for row in RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS}
    assert "optional" in licenses
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "cannot claim G4" in brief or "cannot claim PASS on G4" in brief
    assert "not COMPLETE" in brief or "never **COMPLETE**" in brief
    assert "PASS_WITH_CONSTRAINTS" in brief
    assert "workspace-capability-host-runtime-equivalence.md" in brief
    assert "workspace-capability-platform-g1-g5-closeout.md" in brief
    assert "Recruitment Application" in brief
    assert "Candidate is **not** the proof" in brief or "Candidate Entity Workspace is **not** the proof" in brief
    panel = _RECRUITMENT_PANEL.read_text(encoding="utf-8")
    assert "ApplicationWorkspaceCapabilityHost" in panel
    assert "RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS" in panel
    assert "workspace-capability" in panel
    assert "contextSlots" not in panel
    assert "vacancy:" not in panel
    assert "assignee:" not in panel
    for marker in (
        "SalesInquiryRodoSection",
        "CandidateRodoSection",
        "SalesInquiryCallNotesSection",
        "ApplicationCommentsSection",
        "ApplicationRodoSection",
    ):
        assert marker not in panel
    host = _CAPABILITY_HOST_TS.read_text(encoding="utf-8")
    assert "data-workspace-capability-host" in host
    assert "data-host-region" in host


def test_checkbox_primitive_locked() -> None:
    assert _CHECKBOX_TS.is_file()
    assert _CHECKBOX_V1.is_file()
    checkbox = _CHECKBOX_TS.read_text(encoding="utf-8")
    assert "export function Checkbox" in checkbox
    spec = _CHECKBOX_V1.read_text(encoding="utf-8")
    assert "CHECKBOX_V1" in spec or "Question Answered" in spec
    assert "boolean" in spec.lower()


def test_g4_notes_consent_separation() -> None:
    assert _CONSENT_TS.is_file()
    assert _NOTES_TS.is_file()
    consent = _CONSENT_TS.read_text(encoding="utf-8")
    notes = _NOTES_TS.read_text(encoding="utf-8")
    assert "from '../../../components/ui/Checkbox'" in consent
    assert 'type="checkbox"' not in consent
    assert "SalesInquiryRodoSection" not in consent
    assert "CandidateRodoSection" not in consent
    assert "capability_id=\"consent\"" in consent or "data-capability-id=\"consent\"" in consent
    assert "SalesInquiryCallNotesSection" not in notes
    assert "CandidateNotesSection" not in notes
    assert "data-capability-id=\"notes\"" in notes
    for path in _RECRUITMENT_CONTRIB_DIR.glob("*.tsx"):
        src = path.read_text(encoding="utf-8")
        assert "NotesCapability" not in src, f"{path.name} must not copy notes widget"
        assert "ConsentCapability" not in src, f"{path.name} must not copy consent widget"
        assert "SalesInquiryRodoSection" not in src
        assert "CandidateRodoSection" not in src
        assert "SalesInquiryCallNotesSection" not in src


def test_g2_g3_proof_surface_cannot_import_local_blocks() -> None:
    """G2/G3: Recruitment Application cannot silently import local Notes/Consent/rail."""
    assert _RECRUITMENT_WORKSPACE.is_file()
    workspace = _RECRUITMENT_WORKSPACE.read_text(encoding="utf-8")
    assert "ApplicationWorkspace" in workspace
    assert "ApplicationRecruitmentDetailPanel" in workspace
    for marker in _PROOF_SURFACE_LOCAL_BLOCKS + ("NotesCapability", "ConsentCapability"):
        assert marker not in workspace, f"RecruitmentApplicationWorkspace must not import {marker}"

    surfaces = [
        _RECRUITMENT_WORKSPACE,
        _RECRUITMENT_PANEL,
        _APPLICATION_TS,
        _SHELL_TS,
        *_RECRUITMENT_CONTRIB_DIR.glob("*.tsx"),
    ]
    for path in surfaces:
        src = path.read_text(encoding="utf-8")
        for marker in _PROOF_SURFACE_LOCAL_BLOCKS:
            assert marker not in src, f"{path.name} must not import {marker}"

    panel = _RECRUITMENT_PANEL.read_text(encoding="utf-8")
    assert "ApplicationWorkspaceCapabilityHost" in panel
    assert "RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS" in panel
    assert "contextSlots" not in panel


def test_hosts_do_not_import_notes_consent_widgets() -> None:
    assert _ENTITY_CAPABILITY_HOST_TS.is_file()
    for path in (_SHELL_TS, _APPLICATION_TS, _CAPABILITY_HOST_TS, _ENTITY_CAPABILITY_HOST_TS):
        src = path.read_text(encoding="utf-8")
        for marker in _HOST_FORBIDDEN_IMPORTS:
            assert marker not in src, f"{path.name} must not import {marker}"


def test_d2_documents_still_reserved_e2_feat_not_landed() -> None:
    src = _SLOTS_TS.read_text(encoding="utf-8")
    enabled = _ts_string_array(src, "ENTITY_WORKSPACE_ENABLED_SLOT_IDS")
    reserved = _ts_string_array(src, "ENTITY_WORKSPACE_RESERVED_SLOT_IDS")
    catalog = _ts_string_array(src, "ENTITY_WORKSPACE_SLOT_CATALOG")
    assert "documents" in reserved
    assert "documents" not in enabled
    assert enabled == _ENABLED_SLOTS
    assert reserved == _RESERVED_SLOTS
    contribution_ts = _CONTRIBUTION_TS.read_text(encoding="utf-8")
    assert _ts_string_array(contribution_ts, "WORKSPACE_PLATFORM_SLOT_IDS") == catalog
    assert "compositionSlots" not in contribution_ts
    assert PLATFORM_SURFACE_CAPABILITIES["documents"].get("reserved") is True
    catalog = _CATALOG.read_text(encoding="utf-8")
    assert "documents.public_contract.v1" not in catalog
    assert not re.search(r"(?im)^#{2,3}\s+Entity Workspace\b", catalog)


def test_inventory_lists_notes_consent_and_recruitment_rail() -> None:
    text = _INVENTORY.read_text(encoding="utf-8")
    assert "SalesInquiryCallNotesSection" in text
    assert "SalesInquiryRodoSection" in text
    assert "CandidateRodoSection" in text
    assert "recruitment.vacancy" in text
    assert "recruitment.assignee" in text
    assert "ApplicationRecruitmentDetailPanel" in text
    assert "widget `notes`" in text
    assert "widget `consent`" in text
    assert "Field Registry" in text
    assert "PRIMITIVES_V1" in text
    assert "TABLE_V1" in text
    assert "CandidateProfile.config" in text
    assert "table_candidates_main_v7" in text
    assert "Proof screen must not add a row" in text
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "workspace-capability-legacy-inventory.md" in brief


def test_prior_gates_still_present() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Entity Workspace D1 Contract Seal Gate" in ci
    assert "Entity Workspace D9 Cutover Gate" in ci
    assert "Documents Platform E1 Contract Seal Gate" in ci
    assert "Workspace Capability Platform Completion Gate" in ci
    assert "test_workspace_capability_platform_completion_gate.py" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert "test_workspace_capability_host_runtime_equivalence_gate.py" in ci


def test_product_track_points_at_brief_and_feat() -> None:
    queue = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "sales-to-comms-sequential-queue.md"
    ).read_text(encoding="utf-8")
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "workspace-capability-platform-completion.md" in queue
    assert "workspace-capability-platform-completion.md" in agents
    assert "feat/workspace-capability-platform-completion" in agents or "feat" in queue.lower()
    assert "named Cutover Gate" in agents
    assert "named Contract Seal Gate" in agents
    assert "entity-workspace-d1-contract-seal.md" in agents
    assert "documents-platform-e1-contract-seal.md" in agents
    assert "locked" in queue.lower()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Workspace Capability Platform Completion Gate" in brief
    status_line = next(line for line in brief.splitlines() if line.startswith("**Status:**"))
    assert "PASS_WITH_CONSTRAINTS" in status_line
    assert "not COMPLETE" in status_line
    assert "feat/workspace-capability-platform-completion" in brief
    assert "workspace-capability-legacy-inventory.md" in brief
    closeout = (
        _REPO_ROOT / "docs" / "specs" / "gates" / "workspace-capability-platform-g1-g5-closeout.md"
    ).read_text(encoding="utf-8")
    assert "PASS_WITH_CONSTRAINTS" in closeout
    assert "G4" in closeout
    assert "**PASS**" in closeout
    assert "EntityWorkspaceCapabilityHost" in closeout
    assert "not COMPLETE" in closeout
    next_brief = (
        _REPO_ROOT
        / "docs"
        / "specs"
        / "tasks"
        / "workspace-capability-host-runtime-equivalence.md"
    ).read_text(encoding="utf-8")
    assert "EntityWorkspaceCapabilityHost" in next_brief
    assert "not a new proof-screen" in next_brief.lower() or "Not a new proof-screen" in next_brief
    assert "Documents E2" in next_brief
