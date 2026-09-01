"""Prior-candidate snapshot stamped onto a duplicate lead."""

from __future__ import annotations

import json
from types import SimpleNamespace

from backend.app.modules.leads.duplicate_resolution import (
    LeadDuplicateMatch,
    build_duplicate_prior_summary,
    preserve_duplicate_prior_from_match,
    stamp_duplicate_review_normalized_v1,
)


def test_prior_summary_candidate_rejected_with_reason() -> None:
    cand = SimpleNamespace(
        id="c1",
        first_name="Jan",
        last_name="Kowalski",
        stage="rejected",
        status="closed",
        status_reason=["insufficient_experience"],
        extra=json.dumps(
            {
                "source_lead_id": "lead-old",
                "lead_continuity_v1": {
                    "source_lead_id": "lead-old",
                    "intake_resolution_v1": {"status": "rejected", "reason_code": "insufficient_experience"},
                },
            }
        ),
        origin={"lead_duplicate_intakes_v1": [{"lead_id": "x", "ingested_at": "2026-08-01T00:00:00Z"}]},
    )
    prior = build_duplicate_prior_summary(cand)
    assert prior is not None
    assert prior["candidate_created"] is True
    assert prior["candidate_id"] == "c1"
    assert prior["display_name"] == "Jan Kowalski"
    assert prior["stage"] == "rejected"
    assert prior["reason"] == "insufficient_experience"
    assert prior["outcome"] == "rejected"
    assert prior["source_lead_id"] == "lead-old"
    assert prior["previous_duplicate_intakes"] == 1


def test_stamp_writes_durable_prior() -> None:
    cand = SimpleNamespace(
        id="c2",
        first_name="Anna",
        last_name="Nowak",
        stage="contacted",
        status=None,
        status_reason=[],
        extra="{}",
        origin={},
    )
    n: dict = {}
    stamp_duplicate_review_normalized_v1(
        n,
        match=LeadDuplicateMatch(level="probable", candidate=cand, reasons=["email"], hr_blockers=[]),
        error_code="DUPLICATE_REVIEW_PENDING",
    )
    assert n["duplicate_match_v1"]["prior"]["candidate_id"] == "c2"
    assert n["duplicate_prior_v1"]["candidate_created"] is True
    assert n["duplicate_prior_v1"]["stage"] == "contacted"


def test_preserve_prior_when_match_cleared() -> None:
    n = {
        "duplicate_match_v1": {
            "prior": {"candidate_created": True, "candidate_id": "c3", "stage": "employed"},
        }
    }
    preserve_duplicate_prior_from_match(n, n["duplicate_match_v1"])
    n.pop("duplicate_match_v1")
    assert n["duplicate_prior_v1"]["candidate_id"] == "c3"
    assert n["duplicate_prior_v1"]["stage"] == "employed"
