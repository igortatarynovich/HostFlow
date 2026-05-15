"""Read-model: ordered work-eligibility journey for HR (no new persistence)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_work_eligibility_profile import (
    WorkPermitSubmissionChannel,
    WorkforceWorkEligibilityProfile,
)
from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask
from backend.app.services.workforce_hr_core_profiles import get_insurance_profile
from backend.app.services.workforce_work_eligibility import ensure_work_eligibility_profile, get_work_eligibility_profile
from backend.app.services.workforce_work_eligibility_payments import list_payment_requirements
from backend.app.services.workforce_work_eligibility_rules import (
    RED_PAPER_ORDER_STATUSES,
    REQUIREMENT_RED_PAPER_FEE,
    REQUIREMENT_WORK_PERMIT_FEE,
    WORK_PERMIT_SUBMITTED_STATUSES,
    _is_third_country,
    evaluate_zus_registration_gate,
    foreign_driver_fee_rows_expected,
    payment_row_satisfied,
    work_permit_fee_paid,
    red_paper_fee_paid,
)
from backend.app.services.workforce_zus_task_autocreate import (
    TASK_KIND_REGISTRATION,
    pick_registration_form_kind,
    should_offer_registration_task,
)

_TODAY = date.today


def _pay_by_type(payments: list[Any], req_type: str) -> Optional[Any]:
    for r in payments:
        if (getattr(r, "requirement_type", None) or "").strip().lower() == req_type.lower():
            return r
    return None


def _app_submitted(wel: WorkforceWorkEligibilityProfile) -> bool:
    st = (wel.work_permit_application_status or "").strip().lower()
    if st in WORK_PERMIT_SUBMITTED_STATUSES:
        return True
    return wel.work_permit_submitted_at is not None


def _red_ordered(wel: WorkforceWorkEligibilityProfile) -> bool:
    st = (wel.red_paper_status or "").strip().lower()
    return st in RED_PAPER_ORDER_STATUSES


def _red_received(wel: WorkforceWorkEligibilityProfile) -> bool:
    st = (wel.red_paper_status or "").strip().lower()
    return st in {"received", "issued", "complete", "completed", "delivered"}


async def _portal_url_for_permit(
    db: AsyncSession, wel: WorkforceWorkEligibilityProfile
) -> Optional[str]:
    country = (wel.work_country or "PL").strip().upper()[:8] or "PL"
    ptype = (wel.work_permit_type or "type_a").strip()[:64] or "type_a"
    row = (
        await db.execute(
            select(WorkPermitSubmissionChannel)
            .where(
                WorkPermitSubmissionChannel.country == country,
                WorkPermitSubmissionChannel.permit_type == ptype,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if row and (row.portal_url or "").strip():
        return str(row.portal_url).strip()
    row2 = (
        await db.execute(
            select(WorkPermitSubmissionChannel)
            .where(WorkPermitSubmissionChannel.country == country)
            .limit(1)
        )
    ).scalar_one_or_none()
    if row2 and (row2.portal_url or "").strip():
        return str(row2.portal_url).strip()
    return None


async def _latest_registration_task(
    db: AsyncSession, tenant_id: str, employee_id: str, form_kind: str
) -> Optional[WorkforceZusWorkspaceTask]:
    tid, eid, fk = str(tenant_id).strip(), str(employee_id).strip(), str(form_kind).strip()
    return (
        await db.execute(
            select(WorkforceZusWorkspaceTask)
            .where(
                WorkforceZusWorkspaceTask.tenant_id == tid,
                WorkforceZusWorkspaceTask.employee_id == eid,
                WorkforceZusWorkspaceTask.task_kind == TASK_KIND_REGISTRATION,
                WorkforceZusWorkspaceTask.form_kind == fk,
                WorkforceZusWorkspaceTask.status.in_({"pending", "open", "in_progress", "blocked", "done"}),
            )
            .order_by(WorkforceZusWorkspaceTask.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _step(
    *,
    step_code: str,
    label: str,
    status: str,
    blockers: list[str],
    required_documents: list[str],
    linked_payment_requirement_id: Optional[str] = None,
    linked_document_id: Optional[str] = None,
    action_label: Optional[str] = None,
    action_url: Optional[str] = None,
    external_submission_url: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "step_code": step_code,
        "label": label,
        "status": status,
        "blockers": blockers,
        "required_documents": required_documents,
        "linked_payment_requirement_id": linked_payment_requirement_id,
        "linked_document_id": linked_document_id,
        "action_label": action_label,
        "action_url": action_url,
        "external_submission_url": external_submission_url,
    }


async def build_work_eligibility_journey(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> dict[str, Any]:
    await ensure_work_eligibility_profile(db, tenant_id, employee_id)
    wel = await get_work_eligibility_profile(db, tenant_id, employee_id)
    payments = await list_payment_requirements(db, tenant_id, employee_id)
    ins = await get_insurance_profile(db, tenant_id, employee_id)
    tid, eid = str(tenant_id).strip(), str(employee_id).strip()
    employee_row = (
        await db.execute(
            select(WorkforceEmployee).where(
                WorkforceEmployee.id == eid,
                WorkforceEmployee.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()

    portal = await _portal_url_for_permit(db, wel) if wel else None
    reg_task: Optional[WorkforceZusWorkspaceTask] = None
    fk = "ZUA"
    if ins and should_offer_registration_task(ins):
        fk = pick_registration_form_kind(ins)
        reg_task = await _latest_registration_task(db, tenant_id, employee_id, fk)

    third = bool(wel and _is_third_country(wel.citizenship))
    permit_required = wel is None or wel.requires_work_permit is not False
    red_needed = wel is None or wel.red_paper_required is not False
    fee_path = bool(wel and foreign_driver_fee_rows_expected(wel))

    wp_fee = _pay_by_type(payments, REQUIREMENT_WORK_PERMIT_FEE)
    rp_fee = _pay_by_type(payments, REQUIREMENT_RED_PAPER_FEE)

    # --- evaluate each step (done / not_required / internal blockers / ready) ---
    def legal_eval() -> tuple[str, list[str], list[str]]:
        if not third:
            return "not_required", [], []
        req_docs = ["legal_stay"]
        vt = wel.legal_stay_valid_to if wel else None
        if wel and (wel.legal_stay_document_type or "").strip():
            if vt is None or vt >= _TODAY():
                return "done", [], []
            return "blocked", ["legal_stay_expired"], req_docs
        return "pending", [], req_docs

    def wp_fee_eval() -> tuple[str, list[str], list[str]]:
        if not fee_path:
            return "not_required", [], []
        if wp_fee is None:
            return "pending", [], []
        if payment_row_satisfied(wp_fee):
            return "done", [], []
        st = (wp_fee.payment_status or "").strip().lower()
        if st == "required":
            return "blocked", ["work_permit_fee_unpaid"], []
        return "pending", [], []

    def wp_app_eval() -> tuple[str, list[str], list[str]]:
        if not permit_required:
            return "not_required", [], []
        if not fee_path or work_permit_fee_paid(payments):
            pass
        else:
            return "blocked", ["work_permit_fee"], ["work_permit_application"]
        if wel and wel.work_permit_received_at:
            return "done", [], []
        if wel and _app_submitted(wel):
            return "done", [], []
        return "pending", [], ["work_permit_application"]

    def wp_recv_eval() -> tuple[str, list[str], list[str]]:
        if not permit_required:
            return "not_required", [], []
        if wel and wel.work_permit_received_at:
            return "done", [], []
        if wel and _app_submitted(wel):
            return "pending", [], ["work_permit_decision"]
        return "blocked", ["work_permit_application_incomplete"], ["work_permit"]

    def rp_fee_eval() -> tuple[str, list[str], list[str]]:
        if not fee_path or not red_needed:
            return "not_required", [], []
        if rp_fee is None:
            return "pending", [], []
        if payment_row_satisfied(rp_fee):
            return "done", [], []
        if (rp_fee.payment_status or "").strip().lower() == "required":
            return "blocked", ["red_paper_fee_unpaid"], []
        return "pending", [], []

    def rp_ord_eval() -> tuple[str, list[str], list[str]]:
        if not red_needed:
            return "not_required", [], []
        if wel and _red_received(wel):
            return "done", [], []
        if not fee_path or red_paper_fee_paid(payments):
            pass
        else:
            return "blocked", ["red_paper_fee"], ["red_paper_order"]
        if _red_ordered(wel) if wel else False:
            return "done", [], []
        return "pending", [], ["red_paper_application"]

    def rp_recv_eval() -> tuple[str, list[str], list[str]]:
        if not red_needed:
            return "not_required", [], []
        if _red_received(wel) if wel else False:
            return "done", [], []
        if _red_ordered(wel) if wel else False:
            return "pending", [], ["red_paper_certificate"]
        return "blocked", ["red_paper_not_ordered"], []

    def zus_eval() -> tuple[str, list[str], list[str]]:
        if ins is None or not should_offer_registration_task(ins):
            return "not_required", [], []
        if ins.registered_at is not None:
            return "done", [], []
        mode, bl = evaluate_zus_registration_gate(wel, employee_row, payments)
        if mode == "allow" and reg_task and (reg_task.status or "").lower() in {"done"}:
            return "done", [], []
        if mode == "allow":
            return "pending", [], ["zus_forms"]
        return "blocked", bl, ["zus_registration"]

    def elig_eval() -> tuple[str, list[str], list[str]]:
        if wel is None:
            return "pending", [], []
        st = (wel.eligibility_status or "").strip().lower()
        if st == "eligible_to_work":
            return "done", [], []
        if st in {"ready_for_zus"}:
            return "pending", [], []
        return "blocked", [st or "eligibility_not_ready"], []

    raw_steps: list[tuple[str, str, tuple[str, list[str], list[str]], dict[str, Any]]] = [
        (
            "legal_stay",
            "Legal stay",
            legal_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Update legal stay in profile" if third else None,
                "action_url": None,
                "external_submission_url": None,
            },
        ),
        (
            "work_permit_fee",
            "Work permit fee",
            wp_fee_eval(),
            {
                "linked_payment_requirement_id": wp_fee.id if wp_fee else None,
                "linked_document_id": (wp_fee.receipt_document_id if wp_fee else None),
                "action_label": "Record fee payment" if fee_path else None,
                "action_url": None,
                "external_submission_url": None,
            },
        ),
        (
            "work_permit_application",
            "Work permit application",
            wp_app_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Submit work permit application" if permit_required else None,
                "action_url": None,
                "external_submission_url": portal,
            },
        ),
        (
            "work_permit_received",
            "Work permit received",
            wp_recv_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Confirm permit decision / upload scan" if permit_required else None,
                "action_url": None,
                "external_submission_url": portal,
            },
        ),
        (
            "red_paper_fee",
            "Red paper fee",
            rp_fee_eval(),
            {
                "linked_payment_requirement_id": rp_fee.id if rp_fee else None,
                "linked_document_id": (rp_fee.receipt_document_id if rp_fee else None),
                "action_label": "Record red paper fee" if fee_path and red_needed else None,
                "action_url": None,
                "external_submission_url": None,
            },
        ),
        (
            "red_paper_ordered",
            "Red paper ordered / applied",
            rp_ord_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Order / apply for red paper" if red_needed else None,
                "action_url": None,
                "external_submission_url": None,
            },
        ),
        (
            "red_paper_received",
            "Red paper received",
            rp_recv_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Upload red paper certificate" if red_needed else None,
                "action_url": None,
                "external_submission_url": None,
            },
        ),
        (
            "zus_registration",
            "ZUS registration",
            zus_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Complete ZUS registration task" if ins and should_offer_registration_task(ins) else None,
                "action_url": None,
                "external_submission_url": "https://www.zus.pl" if ins and should_offer_registration_task(ins) else None,
            },
        ),
        (
            "eligible_to_work",
            "Eligible to work",
            elig_eval(),
            {
                "linked_payment_requirement_id": None,
                "linked_document_id": None,
                "action_label": "Set eligibility to eligible when all checks pass",
                "action_url": None,
                "external_submission_url": None,
            },
        ),
    ]

    steps_out: list[dict[str, Any]] = []
    upstream_incomplete = False

    for code, label, (base_st, bl, req_docs), meta in raw_steps:
        st = base_st
        blockers = list(bl)

        if st in ("done", "not_required"):
            steps_out.append(
                _step(
                    step_code=code,
                    label=label,
                    status=st,
                    blockers=blockers,
                    required_documents=req_docs,
                    linked_payment_requirement_id=meta.get("linked_payment_requirement_id"),
                    linked_document_id=meta.get("linked_document_id"),
                    action_label=meta.get("action_label"),
                    action_url=meta.get("action_url"),
                    external_submission_url=meta.get("external_submission_url"),
                )
            )
            continue

        if upstream_incomplete:
            st = "pending"
            blockers = _dedupe_strs(blockers + ["upstream_incomplete"])
        else:
            if st == "blocked" or blockers:
                st = "blocked"
            elif st == "pending":
                st = "current"

        upstream_incomplete = True
        steps_out.append(
            _step(
                step_code=code,
                label=label,
                status=st,
                blockers=blockers,
                required_documents=req_docs,
                linked_payment_requirement_id=meta.get("linked_payment_requirement_id"),
                linked_document_id=meta.get("linked_document_id"),
                action_label=meta.get("action_label"),
                action_url=meta.get("action_url"),
                external_submission_url=meta.get("external_submission_url"),
            )
        )

    recommended = _recommended_next(steps_out)
    return {"steps": steps_out, "recommended_next_action": recommended}


def _dedupe_strs(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = str(x).strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _recommended_next(steps: list[dict[str, Any]]) -> str:
    for s in steps:
        if s.get("status") == "current":
            return f"Focus: {s.get('label') or s.get('step_code')} — {s.get('action_label') or 'complete this step'}."
        if s.get("status") == "blocked" and (s.get("blockers") or []):
            bl = ", ".join(s.get("blockers") or [])
            return f"Unblock: {s.get('label') or s.get('step_code')} ({bl})."
    for s in steps:
        if s.get("status") == "pending":
            return f"Next: {s.get('label') or s.get('step_code')} — {s.get('action_label') or 'continue onboarding'}."
    return "All journey steps are complete or not applicable."
