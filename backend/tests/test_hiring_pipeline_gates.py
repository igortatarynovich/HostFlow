"""Hiring pipeline gates — document forward block vs terminal stages."""

from backend.app.constants.stages import is_pipeline_completed_stage
from backend.app.services.hiring_pipeline_gates import (
    default_hiring_pipeline_gates,
    docs_pipeline_blocks_forward_resolved,
    merge_hiring_pipeline_gates,
    serialize_gates_public,
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
    g = merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": True})
    hard, soft = docs_pipeline_blocks_forward_resolved(
        "docs_wait",
        ["passport_scan"],
        [],
        [],
        g,
    )
    assert hard is True
    assert soft is False


def test_docs_forward_not_blocked_by_default_product_gates() -> None:
    g = default_hiring_pipeline_gates()
    hard, soft = docs_pipeline_blocks_forward_resolved(
        "docs_wait",
        ["passport_scan"],
        ["license"],
        ["medical"],
        g,
    )
    assert hard is False
    assert soft is False
    assert g.enforce_requirement_stage_blocks is False


def test_docs_forward_not_blocked_when_enforcement_disabled() -> None:
    g = merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": False})
    hard, soft = docs_pipeline_blocks_forward_resolved(
        "docs_wait",
        ["passport_scan"],
        ["license"],
        ["medical"],
        g,
    )
    assert hard is False
    assert soft is False
    assert g.enforce_requirement_stage_blocks is False


def test_serialize_gates_includes_enforce_flag() -> None:
    public = serialize_gates_public(default_hiring_pipeline_gates())
    assert public["enforce_requirement_stage_blocks"] is False
    on = serialize_gates_public(merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": True}))
    assert on["enforce_requirement_stage_blocks"] is True
