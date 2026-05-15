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


HR_LINKED_DOCS_ANCHOR = "#hr-employee-linked-documents"


def _input_facts_snapshot(wel: Optional[WorkforceWorkEligibilityProfile]) -> dict[str, Any]:
    if wel is None:
        return {
            "citizenship": None,
            "position_category": None,
            "work_country": None,
            "requires_work_permit": None,
            "legal_stay_document_type": None,
            "legal_stay_valid_to": None,
        }
    c = (wel.citizenship or "").strip().upper() or None
    wc = (wel.work_country or "").strip().upper() or None
    return {
        "citizenship": c,
        "position_category": (wel.position_category or "").strip().lower() or None,
        "work_country": wc,
        "requires_work_permit": wel.requires_work_permit,
        "legal_stay_document_type": (wel.legal_stay_document_type or "").strip() or None,
        "legal_stay_valid_to": wel.legal_stay_valid_to.isoformat() if wel.legal_stay_valid_to else None,
    }


def _citizenship_kind(cit: Optional[str]) -> str:
    raw = (cit or "").strip().upper()
    if not raw:
        return "missing"
    if len(raw) != 2:
        return "invalid"
    return "third" if _is_third_country(raw) else "eu"


def _missing_profile_fields_for_fee(wel: Optional[WorkforceWorkEligibilityProfile]) -> list[str]:
    if wel is None:
        return ["profile"]
    out: list[str] = []
    ck = _citizenship_kind(wel.citizenship)
    if ck in ("missing", "invalid"):
        out.append("citizenship")
    if not (wel.position_category or "").strip():
        out.append("position_category")
    if not (wel.work_country or "").strip():
        out.append("work_country")
    return out


def _legal_stay_pack(wel: Optional[WorkforceWorkEligibilityProfile]) -> dict[str, Any]:
    facts = _input_facts_snapshot(wel)
    ck = _citizenship_kind(wel.citizenship if wel else None)
    if ck == "missing":
        explain = {
            "decision_reason": (
                "Citizenship is not recorded. Legal stay cannot be classified as EU free movement "
                "vs third-country requirements until a valid ISO-3166 alpha-2 citizenship code is known."
            ),
            "rule_code": "needs_input_citizenship",
            "input_facts": facts,
            "confidence": 0.0,
            "cannot_determine_reason": "citizenship_missing",
            "primary_action": {
                "code": "edit_profile",
                "label": "Fill citizenship (ISO2) in work eligibility profile",
                "href": None,
            },
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "needs_data", "blockers": [], "required_documents": ["legal_stay"], "explain": explain}
    if ck == "invalid":
        explain = {
            "decision_reason": "Citizenship must be a valid ISO 3166-1 alpha-2 code (two letters).",
            "rule_code": "needs_input_citizenship",
            "input_facts": facts,
            "confidence": 0.0,
            "cannot_determine_reason": "citizenship_invalid_format",
            "primary_action": {
                "code": "edit_profile",
                "label": "Correct citizenship code in work eligibility profile",
                "href": None,
            },
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "needs_data", "blockers": [], "required_documents": ["legal_stay"], "explain": explain}
    if ck == "eu":
        explain = {
            "decision_reason": (
                "EU/EEA/CH citizen: this pipeline does not require a separate legal-stay proof step "
                "(free movement baseline for Poland employment context)."
            ),
            "rule_code": "eu_citizen_no_legal_stay_required",
            "input_facts": facts,
            "confidence": 0.95,
            "cannot_determine_reason": None,
            "primary_action": None,
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "not_required", "blockers": [], "required_documents": [], "explain": explain}

    assert wel is not None
    req_docs = ["legal_stay"]
    vt = wel.legal_stay_valid_to
    doc_t = (wel.legal_stay_document_type or "").strip()
    if doc_t:
        if vt is None or vt >= _TODAY():
            explain = {
                "decision_reason": "Legal stay documentation is recorded and validity covers today (or open-ended).",
                "rule_code": "third_country_legal_stay_document_valid",
                "input_facts": facts,
                "confidence": 0.9,
                "cannot_determine_reason": None,
                "primary_action": {
                    "code": "open_document",
                    "label": "Open linked legal stay document",
                    "href": HR_LINKED_DOCS_ANCHOR,
                    "document_type": "legal_stay",
                },
                "secondary_actions": [],
                "document_actions": [
                    {
                        "code": "open",
                        "label": "Open / review legal stay proof",
                        "href": HR_LINKED_DOCS_ANCHOR,
                        "document_type": "legal_stay",
                    },
                    {
                        "code": "replace",
                        "label": "Replace document if details changed",
                        "href": HR_LINKED_DOCS_ANCHOR,
                        "document_type": "legal_stay",
                    },
                ],
                "payment_actions": [],
            }
            return {"status": "done", "blockers": [], "required_documents": [], "explain": explain}
        explain = {
            "decision_reason": "Legal stay proof exists but the valid-to date is before today; upload a current document.",
            "rule_code": "legal_stay_expired",
            "input_facts": facts,
            "confidence": 0.95,
            "cannot_determine_reason": None,
            "primary_action": {
                "code": "upload_replacement",
                "label": "Upload replacement legal stay proof",
                "href": HR_LINKED_DOCS_ANCHOR,
                "document_type": "legal_stay",
            },
            "secondary_actions": [],
            "document_actions": [
                {
                    "code": "replace",
                    "label": "Upload replacement legal stay proof",
                    "href": HR_LINKED_DOCS_ANCHOR,
                    "document_type": "legal_stay",
                },
            ],
            "payment_actions": [],
        }
        return {"status": "blocked", "blockers": ["legal_stay_expired"], "required_documents": req_docs, "explain": explain}

    explain = {
        "decision_reason": "Third-country national: documented legal stay is required before downstream permit steps.",
        "rule_code": "third_country_legal_stay_required",
        "input_facts": facts,
        "confidence": 0.88,
        "cannot_determine_reason": None,
        "primary_action": {
            "code": "upload",
            "label": "Upload legal stay / residence proof",
            "href": HR_LINKED_DOCS_ANCHOR,
            "document_type": "legal_stay",
        },
        "secondary_actions": [],
        "document_actions": [
            {
                "code": "upload",
                "label": "Upload legal stay proof",
                "href": HR_LINKED_DOCS_ANCHOR,
                "document_type": "legal_stay",
            },
        ],
        "payment_actions": [],
    }
    return {"status": "pending", "blockers": [], "required_documents": req_docs, "explain": explain}


def _work_permit_fee_pack(
    wel: Optional[WorkforceWorkEligibilityProfile],
    payments: list[Any],
    wp_fee: Optional[Any],
    fee_path: bool,
) -> dict[str, Any]:
    facts = _input_facts_snapshot(wel)
    missing = _missing_profile_fields_for_fee(wel)
    if missing:
        fields = ", ".join(missing)
        explain = {
            "decision_reason": (
                "Cannot determine whether the statutory work permit fee applies until profile fields are complete: "
                f"{fields}."
            ),
            "rule_code": "needs_input_profile_fields",
            "input_facts": facts,
            "confidence": 0.0,
            "cannot_determine_reason": "missing_profile_fields",
            "primary_action": {
                "code": "edit_profile",
                "label": "Complete citizenship, position category, and work country",
                "href": None,
            },
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "needs_data", "blockers": [], "required_documents": [], "explain": explain}

    assert wel is not None
    if not fee_path:
        if _citizenship_kind(wel.citizenship) == "eu":
            dr = (
                "Work permit fee rows are not enforced: citizenship is EU/EEA/CH (third-country driver fee path does not apply)."
            )
            rc = "eu_citizen_work_permit_fee_not_applicable"
        elif (wel.position_category or "").strip().lower() != "driver":
            dr = "Work permit fee automation is scoped to driver positions for this release."
            rc = "non_driver_work_permit_fee_not_applicable"
        elif wel.requires_work_permit is False:
            dr = "Work permit is marked not required; statutory work permit fee tracking is not applied."
            rc = "permit_not_required_fee_not_applicable"
        else:
            dr = "Work permit fee is not required for this profile under current rules."
            rc = "work_permit_fee_not_applicable"
        explain = {
            "decision_reason": dr,
            "rule_code": rc,
            "input_facts": facts,
            "confidence": 0.9,
            "cannot_determine_reason": None,
            "primary_action": None,
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "not_required", "blockers": [], "required_documents": [], "explain": explain}

    if wp_fee is None:
        explain = {
            "decision_reason": (
                "Driver + third-country profile with work permit required: fee row is expected. "
                "If missing, refresh after profile save or contact support to seed payment requirements."
            ),
            "rule_code": "work_permit_fee_row_pending",
            "input_facts": facts,
            "confidence": 0.55,
            "cannot_determine_reason": None,
            "primary_action": {"code": "edit_profile", "label": "Save profile to trigger fee row seeding", "href": None},
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [],
        }
        return {"status": "pending", "blockers": [], "required_documents": [], "explain": explain}

    if payment_row_satisfied(wp_fee):
        pst = (wp_fee.payment_status or "").strip().lower()
        explain = {
            "decision_reason": f"Work permit fee requirement is satisfied (payment status: {pst}).",
            "rule_code": "work_permit_fee_satisfied",
            "input_facts": {**facts, "payment_status": pst},
            "confidence": 0.95,
            "cannot_determine_reason": None,
            "primary_action": None,
            "secondary_actions": [],
            "document_actions": [],
            "payment_actions": [
                {
                    "code": "view_payment",
                    "label": "Review fee / receipt linkage",
                    "payment_requirement_id": str(wp_fee.id),
                },
            ],
        }
        return {"status": "done", "blockers": [], "required_documents": [], "explain": explain}

    pst = (wp_fee.payment_status or "").strip().lower()
    if pst == "required":
        explain = {
            "decision_reason": "Work permit fee is recorded as required and is not yet paid or waived.",
            "rule_code": "work_permit_fee_payment_required",
            "input_facts": {**facts, "payment_status": pst},
            "confidence": 0.95,
            "cannot_determine_reason": None,
            "primary_action": {
                "code": "record_payment",
                "label": "Record payment or waive with justification",
                "payment_requirement_id": str(wp_fee.id),
            },
            "secondary_actions": [],
            "document_actions": [
                {
                    "code": "upload_receipt",
                    "label": "Upload fee payment confirmation document",
                    "href": HR_LINKED_DOCS_ANCHOR,
                    "document_type": "work_permit_fee_receipt",
                },
            ],
            "payment_actions": [
                {"code": "mark_paid", "label": "Mark fee paid", "payment_requirement_id": str(wp_fee.id)},
                {"code": "upload_receipt", "label": "Attach receipt document id", "payment_requirement_id": str(wp_fee.id)},
                {"code": "waive", "label": "Waive fee (record waiver)", "payment_requirement_id": str(wp_fee.id)},
            ],
        }
        return {"status": "blocked", "blockers": ["work_permit_fee_unpaid"], "required_documents": [], "explain": explain}

    explain = {
        "decision_reason": f"Work permit fee row exists; payment status is {pst or 'unknown'} — finish recording when settled.",
        "rule_code": "work_permit_fee_pending",
        "input_facts": {**facts, "payment_status": pst},
        "confidence": 0.65,
        "cannot_determine_reason": None,
        "primary_action": {
            "code": "record_payment",
            "label": "Update payment status or attach receipt",
            "payment_requirement_id": str(wp_fee.id),
        },
        "secondary_actions": [],
        "document_actions": [
            {
                "code": "upload_receipt",
                "label": "Upload payment confirmation if available",
                "href": HR_LINKED_DOCS_ANCHOR,
                "document_type": "work_permit_fee_receipt",
            },
        ],
        "payment_actions": [
            {"code": "update_status", "label": "Update fee payment record", "payment_requirement_id": str(wp_fee.id)},
        ],
    }
    return {"status": "pending", "blockers": [], "required_documents": [], "explain": explain}


def _step_pack(
    status: str, blockers: list[str], required_documents: list[str]
) -> dict[str, Any]:
    return {"status": status, "blockers": blockers, "required_documents": required_documents, "explain": None}


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
    explain: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    e = explain or {}
    primary = e.get("primary_action")
    resolved_action = action_label
    if isinstance(primary, dict) and primary.get("label"):
        resolved_action = str(primary["label"])
    return {
        "step_code": step_code,
        "label": label,
        "status": status,
        "blockers": blockers,
        "required_documents": required_documents,
        "linked_payment_requirement_id": linked_payment_requirement_id,
        "linked_document_id": linked_document_id,
        "action_label": resolved_action,
        "action_url": action_url,
        "external_submission_url": external_submission_url,
        "decision_reason": e.get("decision_reason"),
        "rule_code": e.get("rule_code"),
        "input_facts": e.get("input_facts"),
        "confidence": e.get("confidence"),
        "cannot_determine_reason": e.get("cannot_determine_reason"),
        "primary_action": e.get("primary_action"),
        "secondary_actions": e.get("secondary_actions") or [],
        "document_actions": e.get("document_actions") or [],
        "payment_actions": e.get("payment_actions") or [],
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

    legal_pack = _legal_stay_pack(wel)
    fee_pack = _work_permit_fee_pack(wel, payments, wp_fee, fee_path)

    def wp_app_eval() -> dict[str, Any]:
        if not permit_required:
            return _step_pack("not_required", [], [])
        if not fee_path or work_permit_fee_paid(payments):
            pass
        else:
            return _step_pack("blocked", ["work_permit_fee"], ["work_permit_application"])
        if wel and wel.work_permit_received_at:
            return _step_pack("done", [], [])
        if wel and _app_submitted(wel):
            return _step_pack("done", [], [])
        return _step_pack("pending", [], ["work_permit_application"])

    def wp_recv_eval() -> dict[str, Any]:
        if not permit_required:
            return _step_pack("not_required", [], [])
        if wel and wel.work_permit_received_at:
            return _step_pack("done", [], [])
        if wel and _app_submitted(wel):
            return _step_pack("pending", [], ["work_permit_decision"])
        return _step_pack("blocked", ["work_permit_application_incomplete"], ["work_permit"])

    def rp_fee_eval() -> dict[str, Any]:
        if not fee_path or not red_needed:
            return _step_pack("not_required", [], [])
        if rp_fee is None:
            return _step_pack("pending", [], [])
        if payment_row_satisfied(rp_fee):
            return _step_pack("done", [], [])
        if (rp_fee.payment_status or "").strip().lower() == "required":
            return _step_pack("blocked", ["red_paper_fee_unpaid"], [])
        return _step_pack("pending", [], [])

    def rp_ord_eval() -> dict[str, Any]:
        if not red_needed:
            return _step_pack("not_required", [], [])
        if wel and _red_received(wel):
            return _step_pack("done", [], [])
        if not fee_path or red_paper_fee_paid(payments):
            pass
        else:
            return _step_pack("blocked", ["red_paper_fee"], ["red_paper_order"])
        if _red_ordered(wel) if wel else False:
            return _step_pack("done", [], [])
        return _step_pack("pending", [], ["red_paper_application"])

    def rp_recv_eval() -> dict[str, Any]:
        if not red_needed:
            return _step_pack("not_required", [], [])
        if _red_received(wel) if wel else False:
            return _step_pack("done", [], [])
        if _red_ordered(wel) if wel else False:
            return _step_pack("pending", [], ["red_paper_certificate"])
        return _step_pack("blocked", ["red_paper_not_ordered"], [])

    def zus_eval() -> dict[str, Any]:
        if ins is None or not should_offer_registration_task(ins):
            return _step_pack("not_required", [], [])
        if ins.registered_at is not None:
            return _step_pack("done", [], [])
        mode, bl = evaluate_zus_registration_gate(wel, employee_row, payments)
        if mode == "allow" and reg_task and (reg_task.status or "").lower() in {"done"}:
            return _step_pack("done", [], [])
        if mode == "allow":
            return _step_pack("pending", [], ["zus_forms"])
        return _step_pack("blocked", bl, ["zus_registration"])

    def elig_eval() -> dict[str, Any]:
        if wel is None:
            return _step_pack("pending", [], [])
        st = (wel.eligibility_status or "").strip().lower()
        if st == "eligible_to_work":
            return _step_pack("done", [], [])
        if st in {"ready_for_zus"}:
            return _step_pack("pending", [], [])
        return _step_pack("blocked", [st or "eligibility_not_ready"], [])

    raw_steps: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = [
        (
            "legal_stay",
            "Legal stay",
            legal_pack,
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
            fee_pack,
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

    for code, label, pack, meta in raw_steps:
        base_st = pack["status"]
        blockers = list(pack["blockers"])
        req_docs = list(pack["required_documents"])
        explain = pack.get("explain")
        st = base_st

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
                    explain=explain if isinstance(explain, dict) else None,
                )
            )
            continue

        if upstream_incomplete:
            st = "pending"
            blockers = _dedupe_strs(blockers + ["upstream_incomplete"])
        else:
            if st == "blocked" or blockers or st == "needs_data":
                if st != "needs_data":
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
                explain=explain if isinstance(explain, dict) else None,
            )
        )

    recommended = _recommended_next(steps_out)
    focal = _pick_focal_step(steps_out)
    next_hr = _next_hr_action_payload(focal)
    return {"steps": steps_out, "recommended_next_action": recommended, "next_hr_action": next_hr}


def _dedupe_strs(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = str(x).strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _pick_focal_step(steps: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for s in steps:
        if s.get("status") == "current":
            return s
    for s in steps:
        if s.get("status") == "needs_data":
            return s
    for s in steps:
        if s.get("status") == "blocked":
            return s
    for s in steps:
        if s.get("status") == "pending":
            return s
    return None


def _next_hr_action_payload(focal: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not focal:
        return None
    primary = focal.get("primary_action")
    title = None
    if isinstance(primary, dict) and primary.get("label"):
        title = str(primary["label"])
    if not title:
        title = str(focal.get("action_label") or focal.get("label") or focal.get("step_code") or "Next HR action")
    pa = primary if isinstance(primary, dict) else None
    secondaries = focal.get("secondary_actions") or []
    if not isinstance(secondaries, list):
        secondaries = []
    return {
        "title": title[:400],
        "step_code": focal.get("step_code"),
        "step_status": focal.get("status"),
        "reason": focal.get("decision_reason"),
        "blockers": list(focal.get("blockers") or []),
        "cannot_determine_reason": focal.get("cannot_determine_reason"),
        "primary_cta": pa,
        "secondary_ctas": [x for x in secondaries if isinstance(x, dict)],
    }


def _recommended_next(steps: list[dict[str, Any]]) -> str:
    for s in steps:
        if s.get("status") == "current":
            return f"Focus: {s.get('label') or s.get('step_code')} — {s.get('action_label') or 'complete this step'}."
    for s in steps:
        if s.get("status") == "needs_data":
            cnd = s.get("cannot_determine_reason") or "missing_inputs"
            return f"Provide data: {s.get('label') or s.get('step_code')} — {cnd.replace('_', ' ')}."
    for s in steps:
        if s.get("status") == "blocked" and (s.get("blockers") or []):
            bl = ", ".join(s.get("blockers") or [])
            return f"Unblock: {s.get('label') or s.get('step_code')} ({bl})."
    for s in steps:
        if s.get("status") == "pending":
            return f"Next: {s.get('label') or s.get('step_code')} — {s.get('action_label') or 'continue onboarding'}."
    return "All journey steps are complete or not applicable."
