"""Pipeline blockers derived from requirement fulfillment (Phase 3b)."""

from __future__ import annotations

import pytest

from backend.app.services.candidate_evidence_service import map_requirements_checklist_to_pipeline_blockers


def _item(
    *,
    requirement_code: str,
    fulfilled: bool,
    evaluation_status: str,
    evidence_status: str | None = None,
    public_name: str | None = None,
) -> dict:
    evidence = None
    if evidence_status:
        evidence = {"status": evidence_status, "evidence_variant_code": "legal_stay_any"}
    return {
        "requirement_code": requirement_code,
        "public_name": public_name or "Legal stay confirmation",
        "fulfilled": fulfilled,
        "evaluation": {"status": evaluation_status},
        "candidate_evidence": evidence,
    }


def test_legal_stay_no_evidence_is_single_missing_blocker() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status="missing",
                evidence_status=None,
            )
        ]
    )
    assert blockers["missing_requirements"] == ["legal_stay_confirmation"]
    assert blockers["problematic_requirements"] == []
    assert blockers["pending_review_requirements"] == []
    assert len(blockers["unfulfilled_requirements"]) == 1
    assert blockers["unfulfilled_requirements"][0]["public_name"] == "Legal stay confirmation"


def test_legal_stay_fulfilled_produces_no_blockers() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=True,
                evaluation_status="satisfied",
                evidence_status="approved",
            )
        ]
    )
    assert blockers["all_fulfilled"] is True
    assert blockers["missing_requirements"] == []
    assert blockers["pending_review_requirements"] == []


def test_legal_stay_pending_review_blocks_as_in_progress() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status="pending_verification",
                evidence_status="pending_review",
            )
        ]
    )
    assert blockers["missing_requirements"] == []
    assert blockers["pending_review_requirements"] == ["legal_stay_confirmation"]


def test_legal_stay_rejected_is_problematic_not_fulfilled() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status="missing",
                evidence_status="rejected",
            )
        ]
    )
    assert blockers["problematic_requirements"] == ["legal_stay_confirmation"]
    assert "legal_stay_confirmation" not in blockers["missing_requirements"]


def test_not_applicable_requirements_are_ignored() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status="not_applicable",
                evidence_status=None,
            )
        ]
    )
    assert blockers["all_fulfilled"] is True
    assert blockers["unfulfilled_requirements"] == []


def test_superseded_evidence_counts_as_missing() -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status="missing",
                evidence_status="superseded",
            )
        ]
    )
    assert blockers["missing_requirements"] == ["legal_stay_confirmation"]


@pytest.mark.parametrize(
    "evaluation_status,evidence_status",
    [
        ("missing", "selected"),
        ("pending_evidence", "selected"),
    ],
)
def test_unfulfilled_evidence_without_approval_is_missing(
    evaluation_status: str,
    evidence_status: str,
) -> None:
    blockers = map_requirements_checklist_to_pipeline_blockers(
        [
            _item(
                requirement_code="legal_stay_confirmation",
                fulfilled=False,
                evaluation_status=evaluation_status,
                evidence_status=evidence_status,
            )
        ]
    )
    assert blockers["missing_requirements"] == ["legal_stay_confirmation"]
