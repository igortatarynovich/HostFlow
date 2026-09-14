"""RSO-2D — HR host read-model cutover (live + Why Ready).

Named gate: rso2-read-model-gate
Does not open RSO-2E / Slice 4 / Full Spine.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from backend.app.services.hr_handoff_read_model import (
    build_why_ready_from_manifest,
    display_name_from_live_person,
    live_person_flat,
)
from backend.app.services import hr_inbox, hr_handoff_profile_context, hr_documents_queue

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2d-read-model.md"
_CUTOVER = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2-cutover.md"
_READ_MODEL = _REPO_ROOT / "backend" / "app" / "services" / "hr_handoff_read_model.py"
_INBOX = _REPO_ROOT / "backend" / "app" / "services" / "hr_inbox.py"
_PROFILE = _REPO_ROOT / "backend" / "app" / "services" / "hr_handoff_profile_context.py"
_DOCS_Q = _REPO_ROOT / "backend" / "app" / "services" / "hr_documents_queue.py"
_COMPAT = _REPO_ROOT / "backend" / "app" / "services" / "handoff_manifest_compat.py"
_CONTEXT_FE = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "components" / "hr" / "HrHandoffContextSummary.tsx"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_EMIT = _REPO_ROOT / "backend" / "app" / "services" / "ready_for_employment_emit.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_accept_orchestrator.py"


def test_rso2_read_model_gate_filename() -> None:
    assert Path(__file__).name == "test_rso2_read_model_gate.py"


def test_brief_and_ci_wire() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "rso2-read-model-gate" in brief
    assert "Why Ready" in brief or "why_ready" in brief
    assert "lock 6" in brief.lower() or "Lock 6" in brief
    assert "RSO-2E" in brief
    assert "Slice 4" in brief
    cutover = _CUTOVER.read_text(encoding="utf-8")
    assert "RSO-2D" in cutover
    assert "rso2d-read-model" in cutover or "rso2-read-model" in cutover
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_read_model_gate.py" in ci
    assert "rso2-read-model-gate" in ci or "rso2d" in ci


def test_operational_paths_do_not_coerce_for_currents() -> None:
    for path in (_INBOX, _PROFILE, _DOCS_Q):
        src = path.read_text(encoding="utf-8")
        assert "coerce_snapshot_payload_for_legacy_readers" not in src, path.name
    inbox_src = inspect.getsource(hr_inbox)
    profile_src = inspect.getsource(hr_handoff_profile_context)
    docs_src = inspect.getsource(hr_documents_queue)
    assert "coerce_snapshot_payload_for_legacy_readers" not in inbox_src
    assert "coerce_snapshot_payload_for_legacy_readers" not in profile_src
    assert "coerce_snapshot_payload_for_legacy_readers" not in docs_src
    assert "build_why_ready_from_manifest" in inbox_src or "why_ready" in inbox_src
    assert "live_person" in inbox_src or "live_person_flat" in inbox_src or "display_name_from_live" in inbox_src


def test_why_ready_is_backend_read_model_not_fe_aggregate() -> None:
    rm = _READ_MODEL.read_text(encoding="utf-8")
    assert "def build_why_ready_from_manifest" in rm
    assert "fits_decision" in rm
    assert "requirement_verdicts_as_of" in rm
    assert "evidence_refs" in rm or "document_refs" in rm
    fe = _CONTEXT_FE.read_text(encoding="utf-8")
    assert "why_ready" in fe
    # FE must display backend why_ready — not dig snapshot for fits/verdicts reconstruction.
    assert "row.why_ready" in fe or "why_ready" in fe
    assert "snap.fits_decision" not in fe
    assert "snapshot.fits" not in fe
    # Guard: no aggregating SoT from raw snapshot keys for Why Ready.
    assert "pickString(snap" not in fe


def test_why_ready_from_manifest_unit() -> None:
    manifest = {
        "contract_id": "ready_for_employment.v1",
        "tenant_id": "t1",
        "person": {
            "candidate_id": "c1",
            "identity_facts": {"first_name": "Ann", "last_name": "Lee", "citizenship": "UA"},
            "contacts": {"email": "a@example.com"},
        },
        "target_work": {"vacancy_id": "v1", "vacancy_title_as_of": "Driver"},
        "recruitment_facts": {
            "requirement_verdicts_as_of": [{"requirement_code": "passport", "status": "pass"}],
            "candidate_stage_as_of": "ready_for_handoff",
        },
        "evidence": {
            "document_refs": [{"document_id": "d1", "doc_type": "passport", "status": "approved"}]
        },
        "fits_decision": {"decision": "fits", "reason": "transfer_ready_for_handoff"},
        "context_refs": {"handoff_id": "h1", "emitted_at": "2026-09-13T12:00:00Z"},
    }
    why = build_why_ready_from_manifest(manifest)
    assert why is not None
    assert why["fits_decision"]["decision"] == "fits"
    assert why["requirement_verdicts_as_of"][0]["requirement_code"] == "passport"
    assert why["evidence_refs"][0]["document_id"] == "d1"
    assert why["as_of"]["identity"]["citizenship"] == "UA"
    assert build_why_ready_from_manifest({"candidate": {"first_name": "x"}}) is None


def test_display_name_from_live_person_unit() -> None:
    assert display_name_from_live_person({"full_name": "Ann Lee"}) == "Ann Lee"
    assert display_name_from_live_person({"first_name": "Ann", "last_name": "Lee"}) == "Ann Lee"
    assert display_name_from_live_person({"email": "a@x.com"}) == "a@x.com"
    assert display_name_from_live_person({}) is None
    assert live_person_flat is not None


def test_shim_remains_until_rso2e() -> None:
    assert _COMPAT.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "RSO-2E" in brief
    assert "handoff_manifest_compat" in brief or "shim" in brief.lower()


def test_emit_and_init_not_retouched_in_intent() -> None:
    # 2B/2C artifacts still present; this gate does not delete emit/orch.
    assert _EMIT.is_file()
    assert _ORCH.is_file()
    orch = _ORCH.read_text(encoding="utf-8")
    assert "apply_employment_accept_after_transfer" in orch
    emit = _EMIT.read_text(encoding="utf-8")
    assert "ready_for_employment" in emit


def test_out_of_slice_not_opened() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Does not open" in brief or "does not open" in brief.lower()
    assert "RSO-2E" in brief
    assert "Slice 4" in brief
    assert "Full Spine" in brief or "Full spine" in brief
