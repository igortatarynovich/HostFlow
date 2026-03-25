"""Hiring pipeline gates — document forward block vs terminal stages."""

from backend.app.constants.stages import is_pipeline_completed_stage
from backend.app.services.hiring_pipeline_gates import (
    default_hiring_pipeline_gates,
    docs_pipeline_blocks_forward_resolved,
)


def test_is_pipeline_completed_stage() -> None:
    assert is_pipeline_completed_stage("rejected")
    assert is_pipeline_completed_stage("EMPLOYED")
    assert not is_pipeline_completed_stage("docs_wait")
    assert not is_pipeline_completed_stage("")
    assert not is_pipeline_completed_stage(None)


def test_docs_forward_not_blocked_for_pipeline_completed_despite_missing_docs() -> None:
    g = default_hiring_pipeline_gates()
    for stage in ("rejected", "declined", "employed", "probation_ok"):
        hard, soft = docs_pipeline_blocks_forward_resolved(
            stage,
            ["passport_scan"],
            ["license"],
            ["medical"],
            g,
        )
        assert hard is False, stage
        assert soft is False, stage


def test_docs_forward_still_blocks_active_stage_with_missing() -> None:
    g = default_hiring_pipeline_gates()
    hard, soft = docs_pipeline_blocks_forward_resolved(
        "docs_wait",
        ["passport_scan"],
        [],
        [],
        g,
    )
    assert hard is True
    assert soft is False
