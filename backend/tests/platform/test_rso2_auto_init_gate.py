"""RSO-2C — Employment auto-init after Transfer (auto-init gate).

Named gate: rso2-auto-init-gate
Does not open RSO-2D / RSO-2E / Slice 4 / Full Spine.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from backend.app.services import handoff as handoff_service
from backend.app.services.employment_accept_orchestrator import (
    apply_employment_accept_after_transfer,
    apply_employment_accept_policy,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2c-auto-init.md"
_CUTOVER = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2-cutover.md"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_accept_orchestrator.py"
_HANDOFF = _REPO_ROOT / "backend" / "app" / "services" / "handoff.py"
_HANDOFFS_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_DETAIL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "hr"
    / "HrHandoffDetailPage.tsx"
)
_INBOX = _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "hr" / "HrInboxPage.tsx"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_RSO_ORCH = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "modules"
    / "recruitment"
    / "services"
    / "ready_for_employment_orchestrator.py"
)


def test_rso2_auto_init_gate_filename() -> None:
    assert Path(__file__).name == "test_rso2_auto_init_gate.py"


def test_brief_and_ci_wire() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "rso2-auto-init-gate" in brief
    assert "apply_employment_accept_policy" in brief
    assert "create_handoff" in brief
    assert "RSO-2D" in brief
    assert "Slice 4" in brief
    cutover = _CUTOVER.read_text(encoding="utf-8")
    assert "rso2c-auto-init" in cutover or "RSO-2C" in cutover
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_auto_init_gate.py" in ci
    assert "rso2-auto-init-gate" in ci or "rso2c" in ci


def test_create_handoff_does_not_inline_accept_or_policy() -> None:
    create_fn = inspect.getsource(handoff_service.create_handoff)
    assert "accept_handoff(" not in create_fn
    assert "apply_employment_accept_policy" not in create_fn
    assert "apply_employment_accept_after_transfer" not in create_fn
    handoff_src = _HANDOFF.read_text(encoding="utf-8")
    # Service module may define accept_handoff, but create_handoff body must not call policy.
    tree = ast.parse(handoff_src)
    create_node = next(
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "create_handoff"
    )
    create_src = ast.get_source_segment(handoff_src, create_node) or ""
    assert "apply_employment_accept" not in create_src
    assert "accept_handoff(" not in create_src


def test_post_transfer_composition_outside_create_handoff() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "def apply_employment_accept_after_transfer" in orch or "async def apply_employment_accept_after_transfer" in orch
    assert "RSO-2C" in orch or "post-Transfer" in orch or "post-Transfer" in orch.lower()
    assert "never from" in orch.lower() or "never call" in orch.lower() or "outside" in orch.lower()

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "apply_employment_accept_after_transfer" in api
    assert "create_handoff_route" in api or "async def create_handoff_route" in api
    # Composition sits in API after create — not inside create_handoff service.
    assert "apply_employment_accept_after_transfer" in api

    funcs = {
        n.name
        for n in ast.parse(orch).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "apply_employment_accept_after_transfer" in funcs
    assert "apply_employment_accept_policy" in funcs
    assert apply_employment_accept_after_transfer is not None
    assert apply_employment_accept_policy is not None


def test_recruitment_orchestrator_does_not_call_employment_accept() -> None:
    if not _RSO_ORCH.exists():
        return
    rso = _RSO_ORCH.read_text(encoding="utf-8")
    assert "apply_employment_accept_policy" not in rso
    assert "apply_employment_accept_after_transfer" not in rso
    assert "employment_accept_policy" not in rso


def test_ritual_accept_not_default_happy_path_ui() -> None:
    detail = _DETAIL.read_text(encoding="utf-8")
    inbox = _INBOX.read_text(encoding="utf-8")
    # Detail uses Employment policy apply, not ritual acceptHandoff as primary.
    assert "applyEmploymentAcceptPolicy" in detail
    assert "acceptHandoff" not in detail
    assert "Take into HR review" not in detail or "not the happy path" in detail.lower() or "not the default" in detail.lower()
    # Inbox must not offer ritual Accept pickup button.
    assert "acceptHandoff" not in inbox
    assert "handleAcceptPickup" not in inbox
    assert "accept_pickup" not in inbox


def test_out_of_slice_not_opened() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Does not open" in brief or "does not open" in brief.lower()
    assert "RSO-2D" in brief
    assert "RSO-2E" in brief
    assert "Slice 4" in brief
