"""Unit tests for HR review current_task priority engine."""

from __future__ import annotations

from backend.app.services.hr_review_current_task import (
    TASK_PRIORITY_V1,
    TASK_PRIORITY_V1_TOTAL,
    build_current_task,
    build_task_priority_ladder,
)


def _checklist_item(code: str, *, satisfied: bool) -> dict:
    return {
        "item_code": code,
        "label": code,
        "status": "satisfied" if satisfied else "blocked",
        "required": True,
        "blockers": [] if satisfied else [f"{code}_blocker"],
    }


def test_v1_catalog_has_eight_steps_in_order() -> None:
    assert TASK_PRIORITY_V1_TOTAL == 8
    codes = [c[0] for c in TASK_PRIORITY_V1]
    assert codes[0] == "take_into_review"
    assert codes[-1] == "ready_to_approve"


def test_priority_ladder_marks_current_step() -> None:
    ladder = build_task_priority_ladder("verify_documents")
    assert len(ladder) == 8
    current = [r for r in ladder if r["state"] == "current"]
    assert len(current) == 1
    assert current[0]["task_type"] == "verify_documents"
    assert current[0]["step"] == 2


def test_documents_win_over_eligibility_needs_data() -> None:
    """v1: step 2 beats step 3 even when journey also needs_data."""
    task = build_current_task(
        handoff_status="accepted",
        review_status="hr_review_in_progress",
        can_approve=False,
        blockers=["missing_documents"],
        failed_required=["documents_uploaded"],
        checklist=[_checklist_item("documents_uploaded", satisfied=False)],
        documents_for_approval=[{"document_key": "passport", "label": "Passport", "status": "missing"}],
        journey={"steps": [{"step_code": "citizenship", "status": "needs_data"}]},
    )
    assert task is not None
    assert task["task_type"] == "verify_documents"
    assert task["priority_step"] == 2


def test_take_into_review_when_handoff_pending() -> None:
    task = build_current_task(
        handoff_status="pending_review",
        review_status="hr_review_in_progress",
        can_approve=False,
        blockers=[],
        failed_required=[],
        checklist=[],
        documents_for_approval=[],
        journey=None,
    )
    assert task is not None
    assert task["task_type"] == "take_into_review"
    assert task["priority_step"] == 1
    assert task["blocks_approval"] is True


def test_verify_documents_priority_over_eligibility() -> None:
    task = build_current_task(
        handoff_status="accepted",
        review_status="waiting_documents",
        can_approve=False,
        blockers=["missing_documents"],
        failed_required=["documents_uploaded"],
        checklist=[_checklist_item("documents_uploaded", satisfied=False)],
        documents_for_approval=[
            {"document_key": "passport", "label": "Passport", "status": "missing"},
        ],
        journey={"steps": [{"step_code": "legal_stay", "status": "needs_data"}]},
    )
    assert task is not None
    assert task["task_type"] == "verify_documents"
    assert task["related_documents"]


def test_fill_missing_data_when_journey_needs_data() -> None:
    task = build_current_task(
        handoff_status="accepted",
        review_status="hr_review_in_progress",
        can_approve=False,
        blockers=[],
        failed_required=[],
        checklist=[_checklist_item("identity_verified", satisfied=True)],
        documents_for_approval=[],
        journey={"steps": [{"step_code": "citizenship", "status": "needs_data", "title": "Citizenship"}]},
    )
    assert task is not None
    assert task["task_type"] == "fill_missing_data"


def test_ready_to_approve_when_clear() -> None:
    codes = (
        "identity_verified",
        "legal_stay_verified",
        "work_permit_verified",
        "red_paper_verified",
        "required_payments_confirmed",
        "documents_uploaded",
        "zus_readiness_confirmed",
        "employment_data_complete",
    )
    task = build_current_task(
        handoff_status="accepted",
        review_status="hr_review_in_progress",
        can_approve=True,
        blockers=[],
        failed_required=[],
        checklist=[_checklist_item(c, satisfied=True) for c in codes],
        documents_for_approval=[],
        journey=None,
    )
    assert task is not None
    assert task["task_type"] == "ready_to_approve"
    assert task["blocks_approval"] is False


def test_no_task_when_approved() -> None:
    assert (
        build_current_task(
            handoff_status="accepted",
            review_status="approved_for_employment",
            can_approve=False,
            blockers=[],
            failed_required=[],
            checklist=[],
            documents_for_approval=[],
            journey=None,
        )
        is None
    )
