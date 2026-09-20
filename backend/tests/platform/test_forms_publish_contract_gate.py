"""Forms Publish Contract Gate (FP-1).

One operator question. One write. Twelve classified answerers.
Feat `feat/forms-publish-fp2-publish-action` is open. Publish Action Gate
not PASS. Not FP-2 runtime. Not Hiring E2E.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.reference.forms_publish_contract import (
    ADAPTER_ID,
    ANSWERERS,
    CONTRACT_ID,
    LEFTOVER_SERVE_DEFINITION,
    OPERATOR_QUESTION,
    OPERATOR_STATES,
    PUBLIC_CONTRACT_ID,
    SURVIVING_SERVE_DEFINITION,
    WRITE_API,
    WRITE_AUTHORITY,
    WRITE_PRODUCER_REL,
    classified_codes,
    write_authority_answerers,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "forms-publish-contract.md"
_ADR022 = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "ADR-022-intake-form-purpose-and-submission-policy-model.md"
)
_CHECKLIST = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "ADR-022-review-checklist.md"
)
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_forms_publish_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PRODUCER = _REPO_ROOT / WRITE_PRODUCER_REL
_PUBLIC = _REPO_ROOT / "docs" / "specs" / "architecture" / "forms-public-contract.md"
_EPIC = _REPO_ROOT / "docs" / "specs" / "tasks" / "forms-product-layer-epic.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"


def test_fp1_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_publish_contract_gate.py"


def test_fp1_contract_id_and_write() -> None:
    assert CONTRACT_ID == "forms_publish.v1"
    assert WRITE_AUTHORITY == "commit_publish_ledger"
    assert WRITE_API == "commit_publish"
    assert PUBLIC_CONTRACT_ID == "forms.public_contract.v1"
    assert ADAPTER_ID == "forms.endpoint_adapter_v1"
    assert "what is published" in OPERATOR_QUESTION
    assert SURVIVING_SERVE_DEFINITION == "frozen_publication_snapshot"
    assert LEFTOVER_SERVE_DEFINITION == "form_presentation_runtime_v1"
    writers = write_authority_answerers()
    assert len(writers) == 1
    assert writers[0].code == "commit_publish_ledger"
    assert classified_codes() == (
        "commit_publish_ledger",
        "tenant_lead_form_published_pointer",
        "intake_form_write_service_version_bump",
        "form_definition_published_version_write",
        "builder_draft_save",
        "entity_profile_presentation_public_serve",
        "publication_bridge_resolve",
        "form_runtime_serve",
        "public_submit_bridge",
        "activate_deactivate_lifecycle",
        "communications_automation_published_version",
        "public_intake_unbound_no_ledger",
    )
    assert len(ANSWERERS) == 12
    assert OPERATOR_STATES == (
        "draft",
        "published",
        "live",
        "inactive",
        "never_published",
    )
    assert f"async def {WRITE_API}(" in _PRODUCER.read_text(encoding="utf-8")


def test_fp1_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert CONTRACT_ID in text
    assert "## Forms Publish Contract Gate" in text
    assert "**Write authority**" in text
    assert "commit_publish" in text
    assert "form_publication_versions" in text
    assert "out-of-band" in text.lower() or "outside the ledger" in text.lower()
    assert "Draft" in text and "Live" in text
    assert "form_presentation_runtime_v1" in text
    assert "thirteenth write" in text.lower()
    assert "FP-2" in text
    assert "P4" in text and "P5" in text
    assert "TenantLeadForm" in text


def test_fp1_brief_contract_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    current = text.split("## History", 1)[0]
    assert "Forms Publish Contract Gate" in current
    assert "forms-publish-contract.md" in current
    assert CONTRACT_ID in current or "forms_publish.v1" in current
    assert "**PASS**" in current
    assert "feat/forms-publish-fp2-publish-action" in current
    assert "Publish Action Gate" in current
    assert "FP-2" in current
    assert "commit_publish" in current
    assert "ADR-022" in current
    assert "Hiring E2E" in current or "Hiring" in current


def test_fp1_queue_names_successor_not_runtime() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    current = text.split("## 8. History", 1)[0]
    history = text.split("## 8. History", 1)[1]
    assert "Forms Publish Contract Gate" in current
    assert "forms-publish-contract.md" in current
    assert "feat/forms-publish-fp2-publish-action" in text
    assert "**Active Product** | **[FP-3](external-intake-forms-publish.md)" in current
    assert "Active (Product):** **[FP-3](external-intake-forms-publish.md)" in current
    assert "Publish Action Gate **PASS**" in current
    assert "This stamp does not ship runtime" in history
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "external-intake-forms-publish.md" in agents
    assert "forms-publish-contract.md" in agents or "forms_publish" in agents.lower()
    assert "CL8" in current


def test_fp1_leaves_hiring_hr_queued() -> None:
    for path in (_HIRING, _HR):
        text = path.read_text(encoding="utf-8")
        header = text.split("## History", 1)[0] if "## History" in text else text
        assert "**QUEUED**" in header
        assert "not scheduled" in header.lower()


def test_fp1_adr022_accepted_without_expansion() -> None:
    adr = _ADR022.read_text(encoding="utf-8")
    assert adr.splitlines()[2].startswith("**Status:** Accepted")
    assert "forms-publish-contract.md" in adr
    assert "forms_publish.v1" in adr or "FP-1" in adr
    lowered = adr.lower()
    assert "purpose" in lowered and "submission policy" in lowered
    checklist = _CHECKLIST.read_text(encoding="utf-8")
    assert "**Status:** Accepted" in checklist
    assert "FP-1" in checklist


def test_fp1_p3_unlocked_p4_p5_locked() -> None:
    epic = _EPIC.read_text(encoding="utf-8")
    epic_current = epic.split("## History", 1)[0]
    assert "v1 blocker" in epic_current
    assert "P4" in epic_current and "LOCKED" in epic_current
    public = _PUBLIC.read_text(encoding="utf-8")
    assert "forms-publish-contract.md" in public
    assert "commit_publish" in public
    assert "P4" in public and "LOCKED" in public


def test_fp1_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fp1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Forms Publish Contract Gate" in ci
    assert "test_forms_publish_contract_gate.py" in ci
    assert "docs/specs/tasks/external-intake-forms-publish.md" in ci
    assert "docs/specs/architecture/forms-publish-contract.md" in ci
