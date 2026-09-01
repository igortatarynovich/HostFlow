"""Recruitment intake lifecycle projection — single authority over IR."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.modules.leads.intake_lifecycle import (
    ensure_recruitment_intake_new,
    mark_recruitment_intake_in_progress,
    project_recruitment_intake_lifecycle,
    resolve_intake_lifecycle_filter,
    stamp_recruitment_intake_converted,
)


def _lead(**kwargs):
    defaults = dict(
        candidate_id=None,
        status="needs_routing",
        stage="new",
        lead_type="candidate",
        lead_target_type="candidate",
        note=None,
        normalized={},
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_new_when_unworked() -> None:
    lead = _lead(normalized={"intake_resolution_v1": {"status": "new"}})
    assert project_recruitment_intake_lifecycle(lead) == "new"


def test_call_result_is_in_progress_not_a_stage() -> None:
    lead = _lead(
        normalized={
            "intake_resolution_v1": {"status": "new"},
            "call_result_v1": {"result": "no_answer", "at": "2026-09-01T10:00:00Z"},
        }
    )
    assert project_recruitment_intake_lifecycle(lead) == "in_progress"


def test_rejected_and_converted_terminals() -> None:
    rejected = _lead(status="rejected", normalized={"intake_resolution_v1": {"status": "rejected"}})
    assert project_recruitment_intake_lifecycle(rejected) == "rejected"
    converted = _lead(candidate_id="c1", normalized={"intake_resolution_v1": {"status": "in_progress"}})
    assert project_recruitment_intake_lifecycle(converted) == "converted"


def test_mark_in_progress_does_not_overwrite_rejected() -> None:
    lead = _lead(normalized={"intake_resolution_v1": {"status": "rejected"}})
    assert mark_recruitment_intake_in_progress(lead, last_action="call_result") is False
    assert lead.normalized["intake_resolution_v1"]["status"] == "rejected"


def test_mark_in_progress_from_new() -> None:
    lead = _lead(normalized={"intake_resolution_v1": {"status": "new"}}, stage="new")
    assert mark_recruitment_intake_in_progress(lead, actor="u1", last_action="call_result") is True
    assert lead.normalized["intake_resolution_v1"]["status"] == "in_progress"
    assert lead.stage == "contacted"


def test_opening_card_is_not_modeled_here() -> None:
    """Projection stays new until a substantive stamp — viewing is not an action."""
    lead = _lead(normalized={"intake_resolution_v1": {"status": "new"}})
    assert project_recruitment_intake_lifecycle(lead) == "new"


def test_ensure_new_does_not_clobber() -> None:
    n = {"intake_resolution_v1": {"status": "in_progress"}}
    ensure_recruitment_intake_new(n)
    assert n["intake_resolution_v1"]["status"] == "in_progress"
    empty: dict = {}
    ensure_recruitment_intake_new(empty)
    assert empty["intake_resolution_v1"]["status"] == "new"


def test_converted_stamp() -> None:
    lead = _lead(normalized={"intake_resolution_v1": {"status": "in_progress"}})
    stamp_recruitment_intake_converted(lead)
    assert lead.normalized["intake_resolution_v1"]["status"] == "converted"
    assert lead.stage == "converted"
    assert project_recruitment_intake_lifecycle(lead) == "converted"


def test_legacy_lane_aliases() -> None:
    assert resolve_intake_lifecycle_filter("to_call") == "new"
    assert resolve_intake_lifecycle_filter("called") == "in_progress"
    assert resolve_intake_lifecycle_filter("needs_decision") == "needs_decision"
    assert resolve_intake_lifecycle_filter("duplicate") == "needs_decision"
    assert resolve_intake_lifecycle_filter("rejected") == "completed"


def test_pool_and_duplicate_are_not_in_progress() -> None:
    pooled = _lead(normalized={"intake_resolution_v1": {"status": "pooled"}})
    assert project_recruitment_intake_lifecycle(pooled) == "pool"
    dup = _lead(
        status="duplicate_review",
        normalized={"intake_resolution_v1": {"status": "duplicate_review_requested"}},
    )
    assert project_recruitment_intake_lifecycle(dup) == "duplicate_review"
