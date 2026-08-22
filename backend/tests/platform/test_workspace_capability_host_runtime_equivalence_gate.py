"""Workspace Capability Host Runtime Equivalence Gate.

Second constitution host at runtime + Notes/Consent owner facades.
Not a new proof-screen. Not Documents E2. G4 stays Recruitment Application.
No Postgres required.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "workspace-capability-host-runtime-equivalence.md"
)
_PARENT = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "workspace-capability-platform-completion.md"
)
_CLOSEOUT = (
    _REPO_ROOT / "docs" / "specs" / "gates" / "workspace-capability-platform-g1-g5-closeout.md"
)
_E2 = _REPO_ROOT / "docs" / "specs" / "tasks" / "documents-platform-e2-public-contract.md"
_COMPLETE = (
    _REPO_ROOT / "docs" / "specs" / "gates" / "workspace-capability-platform-complete.md"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PROOF_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "proof.ts"
)
_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "application-workspace"
    / "ApplicationRecruitmentDetailPanel.tsx"
)
_APPLICATION_HOST = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "ApplicationWorkspaceCapabilityHost.tsx"
)
_ENTITY_HOST = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "EntityWorkspaceCapabilityHost.tsx"
)
_PLACEMENT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "placement.tsx"
)
_NOTES_UI = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "notes"
    / "NotesCapability.tsx"
)
_CONSENT_UI = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "consent"
    / "ConsentCapability.tsx"
)
_NOTES_OWNER = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "notes"
    / "notesOwner.ts"
)
_CONSENT_OWNER = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "consent"
    / "consentOwner.ts"
)
_SLOTS_TS = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "compositionSlots.ts"
)
_CANDIDATE_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "CandidateEntityWorkspacePage.tsx"
)
_CANDIDATE_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEntityWorkspacePanel.tsx"
)
_CANDIDATE_ENTITY = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "workspace-capability"
    / "candidateEntity.ts"
)
_COMMUNICATION_UI = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "communication"
    / "CommunicationCapability.tsx"
)
_FORMS_UI = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "forms"
    / "FormsCapability.tsx"
)

_LEAD_TRANSPORT = (
    "getLead",
    "sendLeadRodoCompliance",
    "markLeadRodoSourceProvided",
)
_HOST_FORBIDDEN = (
    "NotesCapability",
    "ConsentCapability",
    "CandidateRodoSection",
    "SalesInquiryRodoSection",
    "SalesInquiryCallNotesSection",
    "ApplicationRodoSection",
    "getLead",
    "sendLeadRodoCompliance",
    "markLeadRodoSourceProvided",
    "/candidates/",
)


def test_gate_filename() -> None:
    assert Path(__file__).name == "test_workspace_capability_host_runtime_equivalence_gate.py"


def test_both_host_runtimes_exist_and_share_placement_protocol() -> None:
    assert _APPLICATION_HOST.is_file()
    assert _ENTITY_HOST.is_file()
    assert _PLACEMENT.is_file()
    application = _APPLICATION_HOST.read_text(encoding="utf-8")
    entity = _ENTITY_HOST.read_text(encoding="utf-8")
    placement = _PLACEMENT.read_text(encoding="utf-8")
    assert "data-workspace-capability-host" in application
    assert "application_workspace" in application
    assert "data-workspace-capability-host" in entity
    assert "entity_workspace" in entity
    assert "data-proof-consumer" not in entity
    assert "recruitment_application" not in entity
    assert "groupContributionsByRegion" in placement
    assert "groupContributionsByRegion" in application
    assert "groupContributionsByRegion" in entity
    assert "data-host-region" in entity
    assert "Notes/Consent/Recruitment/HR" in entity or "Must not import Notes" in entity


def test_hosts_and_g4_panel_do_not_own_transport() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert "ApplicationWorkspaceCapabilityHost" in panel
    assert "RECRUITMENT_APPLICATION_PROOF_CONTRIBUTIONS" in panel
    for path in (_APPLICATION_HOST, _ENTITY_HOST, _PANEL, _PLACEMENT):
        src = path.read_text(encoding="utf-8")
        for marker in _HOST_FORBIDDEN:
            assert marker not in src, f"{path.name} must not contain {marker}"


def test_capability_ui_does_not_import_lead_or_candidate_notes_transport() -> None:
    notes = _NOTES_UI.read_text(encoding="utf-8")
    consent = _CONSENT_UI.read_text(encoding="utf-8")
    assert "from './notesOwner'" in notes
    assert "from './consentOwner'" in consent
    assert "/candidates/" not in notes
    assert "api/client" not in notes
    assert "api/client" not in consent
    for marker in _LEAD_TRANSPORT:
        assert marker not in notes, f"NotesCapability must not mention {marker}"
        assert marker not in consent, f"ConsentCapability must not mention {marker}"


def test_owner_facades_hide_transport() -> None:
    notes_owner = _NOTES_OWNER.read_text(encoding="utf-8")
    consent_owner = _CONSENT_OWNER.read_text(encoding="utf-8")
    assert "/candidates/" in notes_owner
    assert "listNotes" in notes_owner
    assert "addNote" in notes_owner
    assert "getLead" in consent_owner
    assert "sendLeadRodoCompliance" in consent_owner
    assert "markLeadRodoSourceProvided" in consent_owner
    assert "lead_rodo_v1" in consent_owner or "consent" in consent_owner


def test_g4_proof_consumer_unchanged() -> None:
    proof = _PROOF_TS.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID = 'recruitment_application'" in proof
    assert "PROOF_HOST_ID = 'application_workspace'" in proof
    parent = _PARENT.read_text(encoding="utf-8")
    assert "Candidate Entity Workspace is **not** the proof" in parent or "Candidate is **not** the proof" in parent
    candidate_entity = _CANDIDATE_ENTITY.read_text(encoding="utf-8")
    assert "PROOF_CONSUMER_ID" not in candidate_entity
    assert "recruitment_application" not in candidate_entity
    assert "Not G4" in candidate_entity or "Not G4" in _CANDIDATE_PANEL.read_text(encoding="utf-8")


def test_candidate_entity_is_real_host_consumer_not_g4() -> None:
    """Runtime equivalence proof: a real Entity screen enters through the host."""
    page = _CANDIDATE_PAGE.read_text(encoding="utf-8")
    panel = _CANDIDATE_PANEL.read_text(encoding="utf-8")
    contrib = _CANDIDATE_ENTITY.read_text(encoding="utf-8")
    host = _ENTITY_HOST.read_text(encoding="utf-8")
    placement = _PLACEMENT.read_text(encoding="utf-8")
    assert "CandidateEntityWorkspacePanel" in page
    assert "EntityWorkspaceCapabilityHost" in panel
    assert "CANDIDATE_ENTITY_HOST_CONTRIBUTIONS" in panel
    assert "EntityWorkspaceShell" in panel
    assert "EntityWorkspaceCompositionHost" not in page
    assert "EntityWorkspaceCompositionHost" not in panel
    assert "CandidateCommunicationSlot" not in page
    assert "CandidateFormsSlot" not in page
    assert "data-proof-consumer" not in host
    assert "groupContributionsByRegion" in placement
    assert "slot_id" in placement
    assert "ENTITY_EQUIVALENCE_CONSUMER_ID = 'candidate'" in contrib
    assert "ENTITY_EQUIVALENCE_HOST_ID = 'entity_workspace'" in contrib
    assert "capability_id: 'communication'" in contrib
    assert "capability_id: 'forms'" in contrib
    assert "host: 'entity_workspace'" in contrib
    assert "consumer: 'candidate'" in contrib
    assert "documents" not in contrib.split("CANDIDATE_ENTITY_HOST_CONTRIBUTIONS", 1)[1]
    communication = _COMMUNICATION_UI.read_text(encoding="utf-8")
    forms = _FORMS_UI.read_text(encoding="utf-8")
    assert "listCommunicationThreads" in communication
    assert "listFormsPlatformHandlers" in forms
    assert "getLead" not in communication
    assert "getLead" not in forms
    assert "/candidates/" not in communication
    for marker in (
        "ApplicationRodoSection",
        "ApplicationCommentsSection",
        "CandidateRodoSection",
        "NotesCapability",
        "ConsentCapability",
    ):
        assert marker not in page
        assert marker not in panel
        assert marker not in contrib


def test_not_a_new_proof_screen_or_e2() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Not a new proof-screen" in brief
    assert "EntityWorkspaceCapabilityHost" in brief
    assert "Documents E2" in brief
    assert "ApplicationRodoSection" in brief
    assert "ListWorkspace" in brief
    e2 = _E2.read_text(encoding="utf-8")
    assert "**COMPLETE**" in e2 or "#276" in e2
    assert "named Public Contract Gate" in e2
    assert "unlocked" in e2.lower()
    assert "does not start e2" in brief.lower()
    closeout = _CLOSEOUT.read_text(encoding="utf-8")
    assert "PASS_WITH_CONSTRAINTS" in closeout
    assert "not COMPLETE" in closeout
    complete = _COMPLETE.read_text(encoding="utf-8")
    assert "**COMPLETE**" in complete
    assert "Outcome: **PASS**" in complete
    assert "recruitment_application" in complete.lower() or "Recruitment Application" in complete
    slots = _SLOTS_TS.read_text(encoding="utf-8")
    assert "documents" in slots


def test_goal_completion_filled_program_complete() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "## Original Goal → Completion Proof" in brief
    assert "G1 Original problem:" in brief
    assert "G2 Now forbidden" in brief
    assert "G3 Next consumer" in brief
    assert "G4 End-to-end proof" in brief
    assert "G5 Remaining allowed workarounds" in brief
    status_line = next(line for line in brief.splitlines() if line.startswith("**Status:**"))
    assert "COMPLETE" in status_line
    assert "IN PROGRESS" not in status_line
    complete = _COMPLETE.read_text(encoding="utf-8")
    assert "WCP_G1_G5_PASS" in complete
    assert "program **COMPLETE**" in complete
    assert "Documents E2" in complete


def test_ci_named_gate_and_parent_gate_remain() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Workspace Capability Platform Completion Gate" in ci
    assert "test_workspace_capability_platform_completion_gate.py" in ci
    assert "Workspace Capability Host Runtime Equivalence Gate" in ci
    assert "test_workspace_capability_host_runtime_equivalence_gate.py" in ci
    agents = (_REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "workspace-capability-host-runtime-equivalence.md" in agents
