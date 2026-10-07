"""RSO-2E — Delete compat shim + Manifest Cutover Gate.

Named gate: rso2-cutover-gate
Does not open Slice 4 / Full Spine.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    is_ready_for_employment_manifest,
)
from backend.app.services.hr_handoff_read_model import build_why_ready_from_manifest
from backend.app.services import hr_handoff_profile_context

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2e-shim-delete.md"
_CUTOVER = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2-cutover.md"
_COMPAT = _REPO_ROOT / "backend" / "app" / "services" / "handoff_manifest_compat.py"
_APP = _REPO_ROOT / "backend" / "app"
_SNAPSHOT = _REPO_ROOT / "backend" / "app" / "services" / "handoff_snapshot.py"
_PROFILE = _REPO_ROOT / "backend" / "app" / "services" / "hr_handoff_profile_context.py"
_INBOX = _REPO_ROOT / "backend" / "app" / "services" / "hr_inbox.py"
_DOCS_Q = _REPO_ROOT / "backend" / "app" / "services" / "hr_documents_queue.py"
_READ_MODEL = _REPO_ROOT / "backend" / "app" / "services" / "hr_handoff_read_model.py"
_CONTEXT_FE = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "components" / "hr" / "HrHandoffContextSummary.tsx"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_rso2_cutover_gate_filename() -> None:
    assert Path(__file__).name == "test_rso2_cutover_gate.py"


def test_brief_and_ci_wire() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "rso2-cutover-gate" in brief
    assert "handoff_manifest_compat" in brief
    assert "Slice 4" in brief
    cutover = _CUTOVER.read_text(encoding="utf-8")
    assert "RSO-2E" in cutover
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_cutover_gate.py" in ci
    assert "rso2-cutover-gate" in ci or "rso2e" in ci


def test_compat_shim_module_deleted() -> None:
    assert not _COMPAT.exists()


def test_no_legacy_projection_runtime_in_app() -> None:
    forbidden = (
        "handoff_manifest_compat",
        "coerce_snapshot_payload_for_legacy_readers",
        "project_manifest_to_legacy_snapshot_shape",
        "_rso2_compat_projection",
    )
    hits: list[str] = []
    for path in _APP.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                hits.append(f"{path.relative_to(_REPO_ROOT)}:{token}")
    assert hits == []


def test_operational_hr_loaders_do_not_project_legacy_candidate() -> None:
    load_src = inspect.getsource(hr_handoff_profile_context.load_handoff_profile_namespace)
    assert "build_handoff_profile_namespace(" not in load_src
    assert "snapshot_payload=None" in load_src
    inbox = _INBOX.read_text(encoding="utf-8")
    assert "coerce_snapshot" not in inbox
    assert "live_person_flat" in inbox or "display_name_from_live_person" in inbox
    docs = _DOCS_Q.read_text(encoding="utf-8")
    assert "live_candidate_summary" in docs
    assert "def _snapshot_summary" not in docs


def test_internal_hr_persist_is_rfe_only() -> None:
    src = _SNAPSHOT.read_text(encoding="utf-8")
    assert 'if dest == "internal_hr"' in src
    assert "build_and_validate_ready_for_employment_package_v1" in src
    tree = ast.parse(src)
    persist = next(
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "persist_handoff_create_snapshot"
    )
    persist_src = ast.get_source_segment(src, persist) or ""
    assert "ready_for_employment" in persist_src
    # internal_hr branch must not call legacy builder.
    assert persist_src.index("internal_hr") < persist_src.index("build_handoff_snapshot_payload_v1")


def test_discriminator_and_why_ready_are_not_a_shim() -> None:
    assert CONTRACT_ID == "ready_for_employment.v1"
    assert is_ready_for_employment_manifest({"contract_id": CONTRACT_ID}) is True
    assert is_ready_for_employment_manifest({"candidate": {"first_name": "x"}}) is False
    why = build_why_ready_from_manifest(
        {
            "contract_id": CONTRACT_ID,
            "person": {"identity_facts": {"citizenship": "UA"}, "contacts": {}},
            "target_work": {},
            "recruitment_facts": {"requirement_verdicts_as_of": []},
            "evidence": {"document_refs": []},
            "fits_decision": {"decision": "fits"},
            "context_refs": {},
        }
    )
    assert why is not None
    assert why["fits_decision"]["decision"] == "fits"
    rm = _READ_MODEL.read_text(encoding="utf-8")
    assert "live Person" in rm or "live_person" in rm


def test_fe_displays_backend_why_ready() -> None:
    fe = _CONTEXT_FE.read_text(encoding="utf-8")
    assert "why_ready" in fe
    assert "pickString(snap" not in fe


def test_prior_rso2_gates_still_wired() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_emit_manifest_gate.py" in ci
    assert "test_rso2_auto_init_gate.py" in ci
    assert "test_rso2_read_model_gate.py" in ci


def test_out_of_slice_not_opened() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Does not open" in brief or "does not open" in brief.lower()
    assert "Slice 4" in brief
    profile = _PROFILE.read_text(encoding="utf-8")
    assert "start_allowed" not in profile.lower()
