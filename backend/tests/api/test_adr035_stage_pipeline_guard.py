"""ADR-035 helpers: stage ∈ pipeline + forbidden pseudo-stages + closed reopen."""

import pytest
from fastapi import HTTPException

from backend.app.api.v1.candidates.helpers import (
    _validate_stage_transition,
    should_reopen_closed_candidate_lifecycle,
)


def test_rejects_forbidden_ready_for_hr():
    with pytest.raises(HTTPException) as ei:
        _validate_stage_transition(None, "ready_for_hr")
    assert ei.value.status_code == 422
    assert "ADR-035" in str(ei.value.detail)


def test_rejects_stage_not_in_funnel():
    with pytest.raises(HTTPException) as ei:
        _validate_stage_transition(
            "new",
            "interview",
            funnel_stage_codes={"new", "contacted", "accepted"},
        )
    assert ei.value.status_code == 422
    assert "not in the candidate" in str(ei.value.detail)


def test_allows_stage_in_funnel():
    _validate_stage_transition(
        "new",
        "accepted",
        funnel_stage_codes={"new", "contacted", "accepted"},
    )


def test_closed_lifecycle_allows_reopen_to_active_stage():
    _validate_stage_transition(
        "declined",
        "contacted",
        funnel_stage_codes={"new", "contacted", "accepted", "declined"},
        lifecycle_status="closed",
    )


def test_closed_lifecycle_blocks_move_to_completed_stage():
    with pytest.raises(HTTPException) as ei:
        _validate_stage_transition(
            "declined",
            "rejected",
            funnel_stage_codes={"new", "contacted", "declined", "rejected"},
            lifecycle_status="closed",
        )
    assert ei.value.status_code == 409
    assert "reopen" in str(ei.value.detail).lower()


def test_archived_lifecycle_blocks_board_move():
    with pytest.raises(HTTPException) as ei:
        _validate_stage_transition(
            "accepted",
            "contacted",
            funnel_stage_codes={"new", "contacted", "accepted"},
            lifecycle_status="archived",
        )
    assert ei.value.status_code == 409
    assert "archived" in str(ei.value.detail).lower()


def test_should_reopen_closed_candidate_lifecycle():
    assert should_reopen_closed_candidate_lifecycle(
        lifecycle_status="closed",
        new_stage_code="contacted",
    )
    assert not should_reopen_closed_candidate_lifecycle(
        lifecycle_status="closed",
        new_stage_code="declined",
    )
    assert not should_reopen_closed_candidate_lifecycle(
        lifecycle_status="active",
        new_stage_code="contacted",
    )
    assert not should_reopen_closed_candidate_lifecycle(
        lifecycle_status="archived",
        new_stage_code="contacted",
    )
