"""HR review case: single prioritized ``current_task`` for Employment Case workspace (PR2).

**Operational priority v1 (default system order, tenant-overridable later):**

See ``TASK_PRIORITY_V1`` and ``docs/specs/workflows/hr-review-task-priority-v1.md``.
The first matching rule wins; tests assert this ordering.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Sequence

from backend.app.models.workforce_hr_review import (
    HR_REVIEW_STATUS_APPROVED,
    HR_REVIEW_STATUS_REJECTED,
    HR_REVIEW_STATUS_RETURNED,
    HR_REVIEW_STATUS_WAITING_DOCUMENTS,
    HR_REVIEW_STATUS_WAITING_PAYMENTS,
    HR_REVIEW_STATUS_WAITING_RED_PAPER,
    HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
)
_ITEM_SATISFIED = "satisfied"

HrCurrentTaskType = Literal[
    "take_into_review",
    "verify_documents",
    "fill_missing_data",
    "verify_work_eligibility",
    "confirm_payments",
    "prepare_zus",
    "complete_employment_data",
    "ready_to_approve",
]

# Canonical v1 ladder: (task_type, short label, one-line meaning for docs/UI/tests).
TASK_PRIORITY_V1: Sequence[tuple[HrCurrentTaskType, str, str]] = (
    (
        "take_into_review",
        "Take into review",
        "HR has not accepted the recruitment handoff into active review.",
    ),
    (
        "verify_documents",
        "Verify documents",
        "Required hire documents are missing or not yet verified.",
    ),
    (
        "fill_missing_data",
        "Fill missing data",
        "Decision inputs are incomplete (citizenship, work country, identity, etc.).",
    ),
    (
        "verify_work_eligibility",
        "Verify work eligibility",
        "Legal stay, work permit, or red paper are not confirmed.",
    ),
    (
        "confirm_payments",
        "Confirm payments",
        "Mandatory statutory fees block submission or approval.",
    ),
    (
        "prepare_zus",
        "Prepare ZUS",
        "HR review is nearly ready but ZUS readiness is not closed.",
    ),
    (
        "complete_employment_data",
        "Complete employment data",
        "Employment contract / start data required for hire is incomplete.",
    ),
    (
        "ready_to_approve",
        "Ready to approve",
        "No blockers remain; approve for employment is allowed.",
    ),
)

TASK_PRIORITY_V1_TOTAL = len(TASK_PRIORITY_V1)

ANCHOR_REVIEW = "#hr-employee-review"
ANCHOR_DOCUMENTS = "#hr-review-documents"
ANCHOR_ELIGIBILITY = "#hr-review-eligibility"
ANCHOR_HANDOFF_ACCEPT = "#hr-handoff-accept"


def _item_by_code(checklist: list[dict[str, Any]], code: str) -> Optional[dict[str, Any]]:
    for it in checklist:
        if isinstance(it, dict) and str(it.get("item_code") or "") == code:
            return it
    return None


def _item_unsatisfied(checklist: list[dict[str, Any]], code: str) -> bool:
    it = _item_by_code(checklist, code)
    if not it:
        return False
    return str(it.get("status") or "") != _ITEM_SATISFIED


def _journey_step(journey: dict[str, Any] | None, code: str) -> Optional[dict[str, Any]]:
    if not journey:
        return None
    for s in journey.get("steps") or []:
        if isinstance(s, dict) and str(s.get("step_code") or "") == code:
            return s
    return None


def _journey_has_needs_data(journey: dict[str, Any] | None) -> bool:
    if not journey:
        return False
    for s in journey.get("steps") or []:
        if isinstance(s, dict) and str(s.get("status") or "").lower() == "needs_data":
            return True
    return False


def _missing_approval_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in documents:
        if not isinstance(d, dict):
            continue
        raw = str(d.get("status") or "").lower()
        if raw in ("missing", "needs_data") or (raw in ("uploaded", "pending") and not d.get("verified")):
            out.append(d)
    return out


def _related_documents(documents: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for d in _missing_approval_documents(documents)[:limit]:
        rows.append(
            {
                "document_key": d.get("document_key"),
                "document_id": d.get("document_id"),
                "label": d.get("label") or d.get("document_key"),
                "status": d.get("status"),
            }
        )
    return rows


def _action(label: str, anchor: str | None = None) -> dict[str, Any]:
    return {"label": label, "anchor": anchor}


def _priority_step_for(task_type: HrCurrentTaskType) -> int:
    for i, (code, _, _) in enumerate(TASK_PRIORITY_V1, start=1):
        if code == task_type:
            return i
    return 0


def build_task_priority_ladder(current_task_type: str | None) -> list[dict[str, Any]]:
    """Full v1 priority order for UI; marks which step is the active ``current_task``."""
    out: list[dict[str, Any]] = []
    for step, (code, label, summary) in enumerate(TASK_PRIORITY_V1, start=1):
        out.append(
            {
                "step": step,
                "task_type": code,
                "label": label,
                "summary": summary,
                "state": "current" if code == current_task_type else "idle",
            }
        )
    return out


def _task(
    *,
    task_type: HrCurrentTaskType,
    title: str,
    description: str,
    why: str,
    priority: str,
    blocks_approval: bool,
    primary_action: dict[str, Any],
    secondary_actions: list[dict[str, Any]] | None = None,
    target_anchor: str | None = None,
    related_documents: list[dict[str, Any]] | None = None,
    related_checklist_items: list[str] | None = None,
    completion_condition: str,
) -> dict[str, Any]:
    step = _priority_step_for(task_type)
    return {
        "task_type": task_type,
        "title": title,
        "description": description,
        "why": why,
        "priority": priority,
        "priority_step": step,
        "priority_total": TASK_PRIORITY_V1_TOTAL,
        "priority_catalog_label": next((lbl for c, lbl, _ in TASK_PRIORITY_V1 if c == task_type), title),
        "blocks_approval": blocks_approval,
        "primary_action": primary_action,
        "secondary_actions": list(secondary_actions or []),
        "target_anchor": target_anchor or primary_action.get("anchor"),
        "related_documents": list(related_documents or []),
        "related_checklist_items": list(related_checklist_items or []),
        "completion_condition": completion_condition,
    }


def build_current_task(
    *,
    handoff_status: str | None,
    review_status: str,
    can_approve: bool,
    blockers: list[str],
    failed_required: list[str],
    checklist: list[dict[str, Any]],
    documents_for_approval: list[dict[str, Any]],
    journey: dict[str, Any] | None,
    handoff_id: str | None = None,
) -> dict[str, Any] | None:
    """Pick one prioritized task for the Employment Case workspace."""
    rs = str(review_status or "").strip()
    if rs in (HR_REVIEW_STATUS_APPROVED, HR_REVIEW_STATUS_RETURNED, HR_REVIEW_STATUS_REJECTED):
        return None

    hs = str(handoff_status or "").strip().lower()
    items = [it for it in checklist if isinstance(it, dict)]
    failed = list(failed_required or [])
    bl = list(blockers or [])
    missing_docs = _missing_approval_documents(documents_for_approval)

    # 1. Handoff not accepted
    if hs == "pending_review":
        return _task(
            task_type="take_into_review",
            title="Take case into HR review",
            description="Accept the recruitment handoff to unlock the HR checklist, document verification, and eligibility workflow.",
            why="Until HR accepts the handoff, this case stays in the recruitment transfer queue and cannot progress toward employment approval.",
            priority="critical",
            blocks_approval=True,
            primary_action=_action("Take into HR review", ANCHOR_HANDOFF_ACCEPT),
            secondary_actions=[_action("View handoff summary", "#hr-handoff-summary")],
            target_anchor=ANCHOR_HANDOFF_ACCEPT,
            completion_condition="Handoff status becomes accepted and the HR review checklist is active.",
        )

    # 2. Missing required documents
    if missing_docs or _item_unsatisfied(items, "documents_uploaded") or rs == HR_REVIEW_STATUS_WAITING_DOCUMENTS:
        labels = ", ".join(str(d.get("label") or d.get("document_key")) for d in missing_docs[:4])
        doc_codes = [str(d.get("document_key")) for d in missing_docs if d.get("document_key")]
        return _task(
            task_type="verify_documents",
            title="Verify required documents",
            description=(
                f"Open and verify each required hire document{': ' + labels if labels else ''}. "
                "Mark checklist items satisfied only after files match identity and stay rules."
            ),
            why="Employment approval is blocked until mandatory documents are present and verified in the HR channel.",
            priority="critical",
            blocks_approval=True,
            primary_action=_action("Open document review", ANCHOR_DOCUMENTS),
            secondary_actions=[_action("HR review checklist", ANCHOR_REVIEW)],
            target_anchor=ANCHOR_DOCUMENTS,
            related_documents=_related_documents(documents_for_approval),
            related_checklist_items=["documents_uploaded"] + doc_codes[:6],
            completion_condition="All required documents are uploaded and verified; document blockers are cleared.",
        )

    # 3. Missing input data
    identity_gap = _item_unsatisfied(items, "identity_verified")
    legal = _journey_step(journey, "legal_stay")
    legal_needs_data = bool(legal and str(legal.get("status") or "").lower() == "needs_data")
    if identity_gap or _journey_has_needs_data(journey) or legal_needs_data:
        gaps: list[str] = []
        if identity_gap:
            gaps.append("identity / contact data")
        if legal_needs_data:
            gaps.append("legal stay basis")
        if _journey_has_needs_data(journey):
            gaps.append("work eligibility profile fields")
        gap_text = ", ".join(gaps) if gaps else "required HR inputs"
        return _task(
            task_type="fill_missing_data",
            title="Fill missing HR inputs",
            description=f"Complete {gap_text} on the employee record and work eligibility profile before statutory checks can run.",
            why="Automated eligibility and checklist rules cannot proceed without citizenship, work country, identity, and permit basis fields.",
            priority="high",
            blocks_approval=True,
            primary_action=_action("Open work eligibility", ANCHOR_ELIGIBILITY),
            secondary_actions=[_action("HR review checklist", ANCHOR_REVIEW)],
            target_anchor=ANCHOR_ELIGIBILITY,
            related_checklist_items=[c for c in ("identity_verified",) if _item_unsatisfied(items, c)],
            completion_condition="Required profile and eligibility inputs are saved; no journey step remains in needs_data.",
        )

    # 4. Work eligibility blockers
    eligibility_codes = ("legal_stay_verified", "work_permit_verified", "red_paper_verified")
    eligibility_failed = [c for c in eligibility_codes if _item_unsatisfied(items, c)]
    if (
        rs in (HR_REVIEW_STATUS_WAITING_WORK_PERMIT, HR_REVIEW_STATUS_WAITING_RED_PAPER)
        or eligibility_failed
    ):
        return _task(
            task_type="verify_work_eligibility",
            title="Verify work eligibility",
            description="Confirm legal stay, work permit, and red-paper steps in the eligibility journey match the candidate dossier.",
            why="Statutory work authorization must be satisfied before HostFlow can approve employment.",
            priority="high",
            blocks_approval=True,
            primary_action=_action("Open work eligibility", ANCHOR_ELIGIBILITY),
            secondary_actions=[_action("Open document review", ANCHOR_DOCUMENTS)],
            target_anchor=ANCHOR_ELIGIBILITY,
            related_checklist_items=eligibility_failed,
            completion_condition="Legal stay and permit journey steps are satisfied or correctly marked not required.",
        )

    # 5. Unpaid required fees
    if rs == HR_REVIEW_STATUS_WAITING_PAYMENTS or _item_unsatisfied(items, "required_payments_confirmed"):
        pay_blockers = [b for b in bl if str(b).startswith("payment:")]
        return _task(
            task_type="confirm_payments",
            title="Confirm required payments",
            description="Record payment of statutory fees (voivodeship, permit, or other required charges) linked to this hire.",
            why="Outstanding payment requirements block HR approval and downstream ZUS preparation.",
            priority="high",
            blocks_approval=True,
            primary_action=_action("Open work eligibility & fees", ANCHOR_ELIGIBILITY),
            secondary_actions=[_action("HR review checklist", ANCHOR_REVIEW)],
            target_anchor=ANCHOR_ELIGIBILITY,
            related_checklist_items=["required_payments_confirmed"],
            completion_condition="All required payment rows are marked satisfied in the eligibility workspace.",
        )

    # 6. ZUS not ready
    if _item_unsatisfied(items, "zus_readiness_confirmed"):
        return _task(
            task_type="prepare_zus",
            title="Prepare ZUS registration",
            description="Complete ZUS readiness in the eligibility journey and confirm checklist item when registration data is ready.",
            why="ZUS registration is part of the legal hire path; approval should not run while ZUS readiness is unknown.",
            priority="normal",
            blocks_approval=True,
            primary_action=_action("Open work eligibility", ANCHOR_ELIGIBILITY),
            secondary_actions=[_action("HR review checklist", ANCHOR_REVIEW)],
            target_anchor=ANCHOR_ELIGIBILITY,
            related_checklist_items=["zus_readiness_confirmed"],
            completion_condition="ZUS readiness checklist item is satisfied and journey ZUS step is done or not required.",
        )

    # 7. Employment data incomplete
    if _item_unsatisfied(items, "employment_data_complete"):
        return _task(
            task_type="complete_employment_data",
            title="Complete employment data",
            description="Add at least one active employment row with contract type and start date before approval.",
            why="Contract and start date are required to open payroll, onboarding, and operational employee lifecycle after approval.",
            priority="normal",
            blocks_approval=True,
            primary_action=_action("Open HR review checklist", ANCHOR_REVIEW),
            secondary_actions=[],
            target_anchor=ANCHOR_REVIEW,
            related_checklist_items=["employment_data_complete"],
            completion_condition="Employment record includes contract type and start date; checklist item is satisfied.",
        )

    # 8. Ready to approve
    if can_approve and not failed and not bl:
        return _task(
            task_type="ready_to_approve",
            title="Ready to approve for employment",
            description="All required checklist items and blockers are clear. Approve to activate the employee operational profile.",
            why="This is the decision point: approval unlocks onboarding, payroll prep, and ZUS workflows.",
            priority="normal",
            blocks_approval=False,
            primary_action=_action("Approve for employment", ANCHOR_REVIEW),
            secondary_actions=[_action("Review documents", ANCHOR_DOCUMENTS)],
            target_anchor=ANCHOR_REVIEW,
            completion_condition="HR approves the case; status becomes approved_for_employment and employee profile mode opens.",
        )

    # Fallback: unresolved blockers
    if failed or bl:
        hint = ", ".join((failed or bl)[:4]).replace("_", " ")
        return _task(
            task_type="fill_missing_data",
            title="Resolve remaining blockers",
            description=f"Work through the HR checklist and clear: {hint}.",
            why="One or more required checklist items or system blockers still prevent approval.",
            priority="high",
            blocks_approval=True,
            primary_action=_action("Open HR review checklist", ANCHOR_REVIEW),
            secondary_actions=[_action("Open documents", ANCHOR_DOCUMENTS)],
            target_anchor=ANCHOR_REVIEW,
            related_checklist_items=failed[:8],
            completion_condition="No failed required checklist items and no approval blockers remain.",
        )

    return None
