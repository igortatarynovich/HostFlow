"""P1.14 — day_surface_candidate_audit_v1 builder/validator tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from backend.app.services.day_surface_candidate_audit_v1 import (
    AUDIT_RECORD_KEYS,
    DaySurfaceCandidateAuditValidationError,
    SurfaceCandidateLlmTrace,
    SurfaceCandidateRenderTrace,
    SurfaceCandidateSelectionV1,
    assert_valid_day_surface_candidate_audit_v1,
    build_day_surface_candidate_audit_v1,
    hash_display_text,
    validate_surface_candidate_selection_v1,
)

_CANDIDATE_ID = "a3e44748-1111-4222-8333-444455556666"
_FIXED_AUDIT_ID = "b4f55859-2222-4333-9444-555566667777"
_FIXED_CREATED_AT = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)


def _base_selection(**overrides: object) -> SurfaceCandidateSelectionV1:
    payload = {
        "surface": "candidate_card.next_action",
        "candidate_id": _CANDIDATE_ID,
        "selected_source": "deterministic",
        "selection_reason": "top_ranked_by_rules",
        "display_text": "Upload missing passport scan",
        "dataset_candidate": True,
        "quality_score": 0.91,
        "confidence": 0.88,
        "degraded": False,
        "render_trace": SurfaceCandidateRenderTrace(
            package_ref="pkg-001",
            evaluation_ref="eval-001",
            render_ref="render-001",
        ),
        "created_at": _FIXED_CREATED_AT,
        "audit_id": _FIXED_AUDIT_ID,
    }
    payload.update(overrides)
    return SurfaceCandidateSelectionV1(**payload)  # type: ignore[arg-type]


def test_deterministic_candidate_builds_audit_record() -> None:
    record = build_day_surface_candidate_audit_v1(_base_selection())
    assert record["record_version"] == "day_surface_candidate_audit_v1"
    assert record["audit_id"] == _FIXED_AUDIT_ID
    assert record["candidate_id"] == _CANDIDATE_ID
    assert record["selected_source"] == "deterministic"
    assert record["used_llm"] is False
    assert record["display_text_hash"] == hash_display_text("Upload missing passport scan")


def test_llm_refined_candidate_includes_llm_trace() -> None:
    record = build_day_surface_candidate_audit_v1(
        _base_selection(
            selected_source="llm_refined",
            selection_reason="llm_ranked_after_tie_break",
            llm_trace=SurfaceCandidateLlmTrace(
                generation_ref="gen-001",
                prompt_ref="prompt-001",
                response_ref="resp-001",
            ),
        )
    )
    assert record["used_llm"] is True
    assert record["llm_trace"] == {
        "generation_ref": "gen-001",
        "prompt_ref": "prompt-001",
        "response_ref": "resp-001",
    }


def test_blocked_candidate_has_no_display_text_hash() -> None:
    record = build_day_surface_candidate_audit_v1(
        _base_selection(
            selected_source="blocked",
            selection_reason="policy_blocked_missing_consent",
            display_text="Should not be hashed",
            display_text_snapshot="Should not be stored",
        )
    )
    assert record["display_text_hash"] is None
    assert record["display_text_snapshot"] is None


def test_default_statuses_are_set() -> None:
    record = build_day_surface_candidate_audit_v1(_base_selection())
    assert record["ui_exposure_status"] == "not_exposed"
    assert record["reaction_status"] == "pending"
    assert record["learning_status"] == "not_processed"


def test_selected_source_and_used_llm_cannot_contradict() -> None:
    record = build_day_surface_candidate_audit_v1(_base_selection())
    record["used_llm"] = True
    with pytest.raises(DaySurfaceCandidateAuditValidationError, match="used_llm"):
        assert_valid_day_surface_candidate_audit_v1(record)


def test_trace_ids_are_preserved() -> None:
    record = build_day_surface_candidate_audit_v1(_base_selection())
    assert record["render_trace"] == {
        "package_ref": "pkg-001",
        "evaluation_ref": "eval-001",
        "render_ref": "render-001",
    }


def test_display_text_hash_is_stable() -> None:
    text = "  Line one\r\nLine two  "
    assert hash_display_text(text) == hash_display_text("Line one\nLine two")
    record_a = build_day_surface_candidate_audit_v1(_base_selection(display_text=text))
    record_b = build_day_surface_candidate_audit_v1(_base_selection(display_text="Line one\nLine two"))
    assert record_a["display_text_hash"] == record_b["display_text_hash"]


def test_missing_candidate_id_is_invalid() -> None:
    selection = _base_selection(candidate_id="")
    errors = validate_surface_candidate_selection_v1(selection)
    assert any("candidate_id" in err for err in errors)
    with pytest.raises(DaySurfaceCandidateAuditValidationError):
        build_day_surface_candidate_audit_v1(selection)


def test_raw_profile_keys_do_not_enter_audit_record() -> None:
    errors = validate_surface_candidate_selection_v1(
        SurfaceCandidateSelectionV1(
            surface="candidate_card.next_action",
            candidate_id=_CANDIDATE_ID,
            selected_source="deterministic",
            selection_reason="ok",
            render_trace={
                "package_ref": "pkg",
                "evaluation_ref": "eval",
                "render_ref": "render",
                "phone": "+48123",
            },  # type: ignore[arg-type]
        )
    )
    assert any("profile key" in err for err in errors)
    with pytest.raises(DaySurfaceCandidateAuditValidationError):
        build_day_surface_candidate_audit_v1(
            SurfaceCandidateSelectionV1(
                surface="candidate_card.next_action",
                candidate_id=_CANDIDATE_ID,
                selected_source="deterministic",
                selection_reason="ok",
                render_trace={
                    "package_ref": "pkg",
                    "evaluation_ref": "eval",
                    "render_ref": "render",
                    "email": "secret@example.com",
                },  # type: ignore[arg-type]
            )
        )


def test_output_shape_is_stable() -> None:
    record = build_day_surface_candidate_audit_v1(_base_selection())
    assert tuple(record.keys()) == AUDIT_RECORD_KEYS
    assert UUID(str(record["audit_id"]))
    assert record["created_at"] == "2026-05-29T12:00:00Z"
