"""ADR-035 helpers: stage ∈ pipeline + forbidden pseudo-stages."""

import pytest
from fastapi import HTTPException

from backend.app.api.v1.candidates.helpers import _validate_stage_transition


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


def test_closed_lifecycle_blocks_board_move():
    with pytest.raises(HTTPException) as ei:
        _validate_stage_transition(
            "accepted",
            "contacted",
            funnel_stage_codes={"new", "contacted", "accepted"},
            lifecycle_status="closed",
        )
    assert ei.value.status_code == 409
