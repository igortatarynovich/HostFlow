"""Pre-merge smoke: hybrid verification plan waiver + approve gate."""

from __future__ import annotations

from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.services.hr_document_verification import _append_waiver_to_decision_basis
from backend.app.services.hr_verification_plan import (
    TIER_HARD_BLOCKER,
    TIER_HR_REQUESTED,
    TIER_RECOMMENDED,
    TIER_REQUIRED,
    _classify_requirement_tier,
    _recompute_plan_blocking,
    is_document_requirement_waivable,
    plan_blocks_approve,
    VERIFICATION_SLOT_DEFS,
)
from backend.app.services.workforce_hr_review import finalize_hr_review_can_approve


def test_hard_blockers_not_waivable() -> None:
    journey = {
        "steps": [
            {"code": "legal_stay", "status": "pending", "required_documents": ["legal_stay"]},
        ]
    }
    assert is_document_requirement_waivable("Passport / ID", journey=journey) is False
    assert (
        is_document_requirement_waivable(
            "Driver license", journey=journey, position_category="driver"
        )
        is False
    )
    assert is_document_requirement_waivable("Legal stay", journey=journey) is False


def test_journey_legal_stay_tier_is_hard_blocker() -> None:
    slot = next(s for s in VERIFICATION_SLOT_DEFS if s.document_key == "Legal stay")
    tier = _classify_requirement_tier(
        slot,
        level="required",
        journey={"steps": [{"code": "legal_stay", "status": "pending", "required_documents": ["x"]}]},
        position_category="office",
    )
    assert tier == TIER_HARD_BLOCKER


def test_recommended_missing_does_not_block_plan_or_panel() -> None:
    plan = {
        "plan_mode": "hybrid",
        "can_approve": True,
        "can_complete_verification": True,
        "blocking_reasons": [],
        "documents": [
            {
                "document_key": "Medical",
                "requirement_tier": TIER_RECOMMENDED,
                "document_id": None,
                "verification_status": "pending",
            }
        ],
    }
    blocking, ok = _recompute_plan_blocking(plan["documents"])
    assert ok is True
    assert blocking == []
    plan["blocking_reasons"] = blocking
    plan["can_approve"] = ok
    plan["can_complete_verification"] = ok
    assert plan_blocks_approve(plan) is False
    panel = {
        "status": "hr_review_in_progress",
        "verification_plan": plan,
        "documents_for_approval": plan["documents"],
        "checklist": [],
        "blockers": [],
        "failed_required_items": [],
    }
    assert finalize_hr_review_can_approve(panel) is True


def test_hr_requested_open_blocks_approve() -> None:
    docs = [
        {
            "document_key": "Client certificate",
            "requirement_tier": TIER_HR_REQUESTED,
            "document_id": None,
            "verification_status": "pending",
        }
    ]
    blocking, ok = _recompute_plan_blocking(docs)
    assert ok is False
    assert any("missing_file:Client certificate" in b for b in blocking)


def test_waived_required_unblocks() -> None:
    docs = [
        {
            "document_key": "Medical",
            "requirement_tier": TIER_REQUIRED,
            "document_id": None,
            "reviewed_fields": {"_requirement_waiver": {"reason": "Client accepted"}},
        }
    ]
    blocking, ok = _recompute_plan_blocking(docs)
    assert ok is True


def test_waiver_recorded_in_decision_basis() -> None:
    review = WorkforceHrReview(tenant_id="t1", status="hr_review_in_progress")
    review.decision_basis_json = {"generated_at": "2026-01-01"}
    _append_waiver_to_decision_basis(
        review,
        document_key="Medical",
        reason="Client exception",
        actor_user_id="hr-1",
    )
    waivers = review.decision_basis_json.get("requirement_waivers") or []
    assert len(waivers) == 1
    assert waivers[0]["document_key"] == "Medical"
    assert waivers[0]["reason"] == "Client exception"
    assert waivers[0]["by_user_id"] == "hr-1"
