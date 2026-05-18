"""BFF payloads for HR Review Case UX (hero, stages, next action, readiness)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.workforce_hr_review import (
    HR_REVIEW_STATUS_APPROVED,
    HR_REVIEW_STATUS_REJECTED,
    HR_REVIEW_STATUS_RETURNED,
    HR_REVIEW_STATUS_WAITING_DOCUMENTS,
    HR_REVIEW_STATUS_WAITING_PAYMENTS,
    HR_REVIEW_STATUS_WAITING_RED_PAPER,
    HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
    HR_REVIEW_TERMINAL_STATUSES,
)
from backend.app.services.hr_review_current_task import build_current_task

STAGE_TRANSFERRED = "transferred_from_recruitment"
STAGE_HR_PICKUP = "hr_pickup"
STAGE_DOCUMENTS = "document_verification"
STAGE_LEGAL = "legal_eligibility"
STAGE_DECISION = "hr_decision"
STAGE_EMPLOYEE = "employee_onboarding"

STAGE_LABELS: dict[str, str] = {
    STAGE_TRANSFERRED: "Transferred from recruiting",
    STAGE_HR_PICKUP: "Taken into HR work",
    STAGE_DOCUMENTS: "Document verification",
    STAGE_LEGAL: "Legal / work eligibility",
    STAGE_DECISION: "HR decision",
    STAGE_EMPLOYEE: "Employee created / onboarding",
}

ITEM_SATISFIED = "satisfied"


def _checklist_progress(items: list[dict[str, Any]]) -> tuple[int, int]:
    required = [it for it in items if it.get("required")]
    if not required:
        return 0, 0
    done = sum(1 for it in required if str(it.get("status") or "") == ITEM_SATISFIED)
    return done, len(required)


def _stage_state(
    *,
    index: int,
    current_index: int,
    blocked_index: Optional[int],
    terminal_skip_after: Optional[int],
) -> str:
    if terminal_skip_after is not None and index > terminal_skip_after:
        return "skipped"
    if blocked_index is not None and index == blocked_index:
        return "blocked"
    if index < current_index:
        return "done"
    if index == current_index:
        return "current"
    return "pending"


def _resolve_stage_index(
    *,
    handoff_status: str | None,
    review_status: str,
    has_employee: bool,
    failed_required: list[str],
    blockers: list[str],
    journey: dict[str, Any] | None,
) -> tuple[int, Optional[int], str]:
    hs = str(handoff_status or "").strip().lower()
    rs = str(review_status or "").strip()

    if rs == HR_REVIEW_STATUS_APPROVED or has_employee and rs in HR_REVIEW_TERMINAL_STATUSES:
        return 5, None, "Employee profile is active; onboarding and ZUS tasks may continue."

    if rs in (HR_REVIEW_STATUS_RETURNED, HR_REVIEW_STATUS_REJECTED):
        return 4, 4, "Case closed — returned to recruitment or rejected by HR."

    doc_blockers = any(
        b in failed_required or "document" in b.lower() or "missing" in b.lower()
        for b in blockers + failed_required
    )
    if rs == HR_REVIEW_STATUS_WAITING_DOCUMENTS or doc_blockers:
        return 2, 2, "Verify required documents and close document blockers before approval."

    if rs in (
        HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
        HR_REVIEW_STATUS_WAITING_RED_PAPER,
        HR_REVIEW_STATUS_WAITING_PAYMENTS,
    ):
        return 3, 3, "Complete work eligibility checks (permit, red paper, or payments)."

    journey_blocked = False
    if journey:
        steps = journey.get("steps") or []
        for s in steps:
            if isinstance(s, dict) and str(s.get("status") or "") in ("blocked", "needs_data"):
                journey_blocked = True
                break
    if journey_blocked:
        return 3, 3, "Work eligibility profile is incomplete — fill citizenship, work country, and permit data."

    if hs == "pending_review":
        return 0, None, "Take this case into HR review to start the checklist."

    if hs == "accepted" and rs:
        failed = bool(failed_required or blockers)
        if failed:
            return 2, 2, "Complete checklist items and resolve blockers before approval."
        return 4, None, "Review complete — you can approve for employment when ready."

    return 1, None, "Continue HR review checklist and document verification."


def build_process_stages(
    *,
    handoff_status: str | None,
    review_status: str,
    has_employee: bool,
    failed_required: list[str],
    blockers: list[str],
    journey: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    current_idx, blocked_idx, _msg = _resolve_stage_index(
        handoff_status=handoff_status,
        review_status=review_status,
        has_employee=has_employee,
        failed_required=failed_required,
        blockers=blockers,
        journey=journey,
    )
    terminal_skip: Optional[int] = None
    if str(review_status) in (HR_REVIEW_STATUS_RETURNED, HR_REVIEW_STATUS_REJECTED):
        terminal_skip = 3

    codes = (
        STAGE_TRANSFERRED,
        STAGE_HR_PICKUP,
        STAGE_DOCUMENTS,
        STAGE_LEGAL,
        STAGE_DECISION,
        STAGE_EMPLOYEE,
    )
    out: list[dict[str, Any]] = []
    for i, code in enumerate(codes):
        out.append(
            {
                "code": code,
                "label": STAGE_LABELS[code],
                "state": _stage_state(
                    index=i,
                    current_index=current_idx,
                    blocked_index=blocked_idx,
                    terminal_skip_after=terminal_skip,
                ),
            }
        )
    return out


def build_hero(
    *,
    candidate_display_name: str | None,
    handoff_id: str | None,
    handoff_status: str | None,
    review_status: str,
    vacancy_label: str | None,
    transferred_at: str | None,
    transferred_by: str | None,
    has_employee: bool,
    employee_status: str | None,
    failed_required: list[str],
    blockers: list[str],
    journey: dict[str, Any] | None,
) -> dict[str, Any]:
    _, _, state_message = _resolve_stage_index(
        handoff_status=handoff_status,
        review_status=review_status,
        has_employee=has_employee,
        failed_required=failed_required,
        blockers=blockers,
        journey=journey,
    )
    stages = build_process_stages(
        handoff_status=handoff_status,
        review_status=review_status,
        has_employee=has_employee,
        failed_required=failed_required,
        blockers=blockers,
        journey=journey,
    )
    current = next((s for s in stages if s["state"] == "current"), stages[0] if stages else None)
    return {
        "candidate_display_name": candidate_display_name,
        "handoff_id": handoff_id,
        "handoff_status": handoff_status,
        "review_status": review_status,
        "vacancy_label": vacancy_label,
        "transferred_at": transferred_at,
        "transferred_by": transferred_by,
        "employee_status": employee_status,
        "has_employee": has_employee,
        "current_stage_code": current.get("code") if current else None,
        "current_stage_label": current.get("label") if current else None,
        "state_message": state_message,
        "process_stages": stages,
    }


def build_next_action(
    *,
    review_status: str,
    blockers: list[str],
    failed_required: list[str],
    documents_for_approval: list[dict[str, Any]],
    journey: dict[str, Any] | None,
    can_approve: bool,
) -> dict[str, Any]:
    if str(review_status) == HR_REVIEW_STATUS_APPROVED:
        return {
            "title": "Employment approved",
            "reason": "Workforce employee and onboarding tasks were created.",
            "blockers": [],
            "primary_label": None,
            "primary_anchor": None,
            "secondary_label": None,
            "secondary_anchor": None,
        }

    missing_docs = [
        d for d in documents_for_approval if str(d.get("status") or "").lower() in ("missing", "needs_data")
    ]
    if missing_docs:
        names = ", ".join(str(d.get("label") or d.get("document_key")) for d in missing_docs[:4])
        return {
            "title": "Verify required documents",
            "reason": f"Missing or incomplete: {names}",
            "blockers": blockers[:8],
            "primary_label": "Open document review",
            "primary_anchor": "#hr-review-documents",
            "secondary_label": "Work eligibility",
            "secondary_anchor": "#hr-review-eligibility",
        }

    if blockers or failed_required:
        return {
            "title": "Resolve blockers before approval",
            "reason": ", ".join((failed_required or blockers)[:4]).replace("_", " "),
            "blockers": blockers[:8],
            "primary_label": "Open HR review checklist",
            "primary_anchor": "#hr-employee-review",
            "secondary_label": None,
            "secondary_anchor": None,
        }

    if journey and isinstance(journey.get("next_hr_action"), dict):
        na = journey["next_hr_action"]
        return {
            "title": str(na.get("title") or journey.get("recommended_next_action") or "Continue work eligibility"),
            "reason": str(na.get("reason") or na.get("description") or ""),
            "blockers": blockers[:8],
            "primary_label": "Open work eligibility",
            "primary_anchor": "#hr-review-eligibility",
            "secondary_label": None,
            "secondary_anchor": None,
        }

    if can_approve:
        return {
            "title": "Approve for employment",
            "reason": "Checklist complete — approval will create workforce employee and onboarding/ZUS tasks.",
            "blockers": [],
            "primary_label": "Approve for employment",
            "primary_anchor": "#hr-employee-review",
            "secondary_label": None,
            "secondary_anchor": None,
        }

    return {
        "title": "Complete HR review checklist",
        "reason": "Satisfy required checklist items and document verification.",
        "blockers": blockers[:8],
        "primary_label": "Open checklist",
        "primary_anchor": "#hr-employee-review",
        "secondary_label": None,
        "secondary_anchor": None,
    }


def build_decision_readiness(
    *,
    checklist: list[dict[str, Any]],
    can_approve: bool,
    blockers: list[str],
    failed_required: list[str],
    review_status: str,
    delayed_workforce: bool,
) -> dict[str, Any]:
    done, total = _checklist_progress(checklist)
    reason = None
    if not can_approve:
        if failed_required:
            reason = f"Required checklist incomplete: {', '.join(failed_required[:5])}"
        elif blockers:
            reason = f"Blockers: {', '.join(blockers[:5])}"
        elif str(review_status) in HR_REVIEW_TERMINAL_STATUSES:
            reason = f"Review is terminal ({review_status})"
        else:
            reason = "Complete required checklist and documents"

    post_approve: list[str] = []
    if delayed_workforce and str(review_status) != HR_REVIEW_STATUS_APPROVED:
        post_approve = [
            "Creates workforce employee record",
            "Seeds onboarding tasks",
            "Opens ZUS profile workflow",
        ]
    elif str(review_status) != HR_REVIEW_STATUS_APPROVED:
        post_approve = ["Finalizes HR review and continues onboarding pipeline"]

    return {
        "checklist_done": done,
        "checklist_total": total,
        "can_approve": can_approve,
        "approve_blocked_reason": reason,
        "post_approve_effects": post_approve,
    }


def build_recent_timeline(panel: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if panel.get("decided_at"):
        events.append(
            {
                "at": panel["decided_at"],
                "kind": "decision",
                "label": f"HR decision: {panel.get('status', '')}",
            }
        )
    if panel.get("corrections_note"):
        events.append(
            {
                "at": panel.get("decided_at"),
                "kind": "corrections",
                "label": "Corrections requested",
            }
        )
    if panel.get("return_reason"):
        events.append({"at": panel.get("decided_at"), "kind": "return", "label": "Returned to recruitment"})
    if panel.get("reject_reason"):
        events.append({"at": panel.get("decided_at"), "kind": "reject", "label": "Rejected by HR"})
    return events[:3]


def enrich_hr_review_panel(
    panel: dict[str, Any],
    *,
    handoff_status: str | None = None,
    candidate_display_name: str | None = None,
    vacancy_label: str | None = None,
    transferred_at: str | None = None,
    transferred_by: str | None = None,
    employee_status: str | None = None,
    journey: dict[str, Any] | None = None,
    delayed_workforce: bool = False,
    recent_timeline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Attach UX BFF fields to an existing hr-review panel dict."""
    items = panel.get("checklist") or []
    blockers = list(panel.get("blockers") or [])
    failed = list(panel.get("failed_required_items") or [])
    docs = list(panel.get("documents_for_approval") or [])
    has_employee = bool(str(panel.get("employee_id") or "").strip())
    review_status = str(panel.get("status") or "")

    mode = "employee_profile" if review_status == HR_REVIEW_STATUS_APPROVED and has_employee else "hr_review_case"

    hero = build_hero(
        candidate_display_name=candidate_display_name,
        handoff_id=panel.get("handoff_id"),
        handoff_status=handoff_status,
        review_status=review_status,
        vacancy_label=vacancy_label,
        transferred_at=transferred_at,
        transferred_by=transferred_by,
        has_employee=has_employee,
        employee_status=employee_status,
        failed_required=failed,
        blockers=blockers,
        journey=journey,
    )
    next_action = build_next_action(
        review_status=review_status,
        blockers=blockers,
        failed_required=failed,
        documents_for_approval=docs,
        journey=journey,
        can_approve=bool(panel.get("can_approve")),
    )
    readiness = build_decision_readiness(
        checklist=items,
        can_approve=bool(panel.get("can_approve")),
        blockers=blockers,
        failed_required=failed,
        review_status=review_status,
        delayed_workforce=delayed_workforce,
    )
    timeline = recent_timeline if recent_timeline is not None else build_recent_timeline(panel)

    current_task = None
    if mode == "hr_review_case":
        current_task = build_current_task(
            handoff_status=handoff_status,
            review_status=review_status,
            can_approve=bool(panel.get("can_approve")),
            blockers=blockers,
            failed_required=failed,
            checklist=items,
            documents_for_approval=docs,
            journey=journey,
            handoff_id=panel.get("handoff_id"),
        )

    out = dict(panel)
    out.update(
        {
            "mode": mode,
            "hero": hero,
            "next_action": next_action,
            "decision_readiness": readiness,
            "recent_timeline": timeline,
            "work_eligibility_summary": _compact_eligibility(journey),
            "current_task": current_task,
        }
    )
    return out


def _compact_eligibility(journey: dict[str, Any] | None) -> dict[str, Any] | None:
    if not journey:
        return None
    steps = [s for s in (journey.get("steps") or []) if isinstance(s, dict)]
    current = next(
        (s for s in steps if str(s.get("status") or "") not in ("done", "skipped")),
        steps[-1] if steps else None,
    )
    blockers: list[str] = []
    for s in steps:
        if str(s.get("status") or "") in ("blocked", "needs_data"):
            label = str(s.get("title") or s.get("step_code") or "step")
            blockers.append(label)
    return {
        "current_step_code": current.get("step_code") if current else None,
        "current_step_title": current.get("title") if current else None,
        "current_step_status": current.get("status") if current else None,
        "recommended_next_action": journey.get("recommended_next_action"),
        "blockers": blockers[:6],
        "decision_basis": journey.get("decision_basis"),
    }
