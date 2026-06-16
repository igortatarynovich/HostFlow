"""HR acceptance review workflow (stage A): checklist, basis, approve / return / reject."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_review import (
    HR_REVIEW_STATUS_APPROVED,
    HR_REVIEW_STATUS_IN_PROGRESS,
    HR_REVIEW_STATUS_REJECTED,
    HR_REVIEW_STATUS_RETURNED,
    HR_REVIEW_STATUS_WAITING_DOCUMENTS,
    HR_REVIEW_STATUS_WAITING_PAYMENTS,
    HR_REVIEW_STATUS_WAITING_RED_PAPER,
    HR_REVIEW_STATUS_WAITING_WORK_PERMIT,
    HR_REVIEW_TERMINAL_STATUSES,
    WorkforceHrReview,
)
from backend.app.services import workforce_employees as we_svc
from backend.app.services.handoff import return_handoff
from backend.app.services.workforce_work_eligibility_journey import build_work_eligibility_journey
from backend.app.services.workforce_work_eligibility_payments import list_payment_requirements
from backend.app.services.workforce_eligibility_delivery_contract import (
    WorkforceEligibilityContext,
    resolve_workforce_eligibility_via_contract,
)
from backend.app.services.document_hub_delivery_contract import (
    list_candidate_documents_via_contract,
)
from backend.app.modules.documents.document_open_service import (
    enrich_documents_for_approval_open_urls,
)
from backend.app.services.hr_review_document_resolution import merge_candidate_documents_into_approval_rows
from backend.app.services.hr_verification_plan import (
    build_hr_verification_plan,
    documents_for_approval_from_plan,
    plan_blocks_approve,
    sync_verification_plan_with_enriched_docs,
)
from backend.app.services.hr_document_verification import (
    VERIFICATION_GATED_CHECKLIST,
    enrich_approval_rows_with_verification,
    sync_checklist_from_verifications,
)
from backend.app.services.hr_data_verification import rebuild_panel_checklists_after_data_verification
from backend.app.services.hr_verification_requirements import (
    resolve_critical_field_codes,
    resolve_position_category_for_review,
)
from backend.app.services.hr_review_case_ux import enrich_hr_review_panel
from backend.app.services import hr_verified_fields as vf_svc
from backend.app.services.employment_identity_read_adapter import (
    CONSUMER_HR_REVIEW_DISPLAY,
    get_trusted_employment_identity,
)
from backend.app.services.tenant_hr_flags import delayed_hr_workforce_creation_enabled
from backend.app.services.workforce_work_eligibility_rules import payment_row_satisfied

CHECKLIST_ITEM_CODES: tuple[str, ...] = (
    "identity_verified",
    "legal_stay_verified",
    "work_permit_verified",
    "red_paper_verified",
    "required_payments_confirmed",
    "documents_uploaded",
    "zus_readiness_confirmed",
    "employment_data_complete",
)

CHECKLIST_LABELS: dict[str, str] = {
    "identity_verified": "Identity verified",
    "legal_stay_verified": "Legal stay verified",
    "work_permit_verified": "Work permit verified",
    "red_paper_verified": "Red paper verified",
    "required_payments_confirmed": "Required payments confirmed",
    "documents_uploaded": "Documents uploaded",
    "zus_readiness_confirmed": "ZUS readiness confirmed",
    "employment_data_complete": "Employment data complete",
}

REQUIRED_CHECKLIST_ITEMS = frozenset(CHECKLIST_ITEM_CODES)

ITEM_SATISFIED = "satisfied"
ITEM_BLOCKED = "blocked"
ITEM_NEEDS_ATTENTION = "needs_attention"
ITEM_UNKNOWN = "unknown"

_VERIFICATION_OK = frozenset({"verified", "not_required"})


def _is_hybrid_verification_plan(plan: Any) -> bool:
    return isinstance(plan, dict) and str(plan.get("plan_mode") or "") == "hybrid"


def finalize_hr_review_can_approve(panel: dict[str, Any]) -> bool:
    """Single gate for UI + API.

    Hybrid mode (PR15): ``verification_plan`` only. Legacy: checklist + verified-fields + doc loop.
    """
    status = str(panel.get("status") or "")
    if status in HR_REVIEW_TERMINAL_STATUSES:
        return False
    plan = panel.get("verification_plan")
    if _is_hybrid_verification_plan(plan):
        return not plan_blocks_approve(plan)
    if isinstance(plan, dict) and plan_blocks_approve(plan):
        return False
    if panel.get("failed_required_items"):
        return False
    if panel.get("blockers"):
        return False
    vfs = panel.get("verified_fields_summary") or {}
    if isinstance(vfs, dict) and vfs.get("blockers"):
        return False
    dv = panel.get("data_verification_summary") or {}
    if isinstance(dv, dict) and dv.get("total", 0) > 0 and not dv.get("ready_for_approval"):
        return False
    for row in panel.get("documents_for_approval") or []:
        if not isinstance(row, dict):
            continue
        tier = str(row.get("requirement_tier") or "")
        if tier in ("recommended", "not_required"):
            continue
        if row.get("required") is False:
            continue
        vs = str(row.get("verification_status") or row.get("status") or "").lower()
        if vs in _VERIFICATION_OK:
            continue
        return False
    return True


class HrReviewBlockedError(Exception):
    def __init__(self, *, blockers: list[str], failed_items: list[str]):
        self.blockers = blockers
        self.failed_items = failed_items
        super().__init__("HR_REVIEW_BLOCKED")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _handoff_id_from_employee(employee: WorkforceEmployee) -> Optional[str]:
    meta = employee.meta if isinstance(employee.meta, dict) else {}
    hid = str(meta.get("internal_hr_handoff_id") or "").strip()
    return hid or None


def _journey_step_by_code(journey: dict[str, Any], code: str) -> Optional[dict[str, Any]]:
    for s in journey.get("steps") or []:
        if isinstance(s, dict) and str(s.get("step_code") or "") == code:
            return s
    return None


def _step_satisfied(step: Optional[dict[str, Any]]) -> bool:
    if not step:
        return False
    st = str(step.get("status") or "").strip().lower()
    if st == "done":
        return True
    if st == "not_required":
        conf = step.get("confidence")
        if conf is not None and float(conf) >= 0.85:
            return True
        if step.get("decision_reason") and not step.get("cannot_determine_reason"):
            return True
    return False


def _step_blocked(step: Optional[dict[str, Any]]) -> bool:
    if not step:
        return True
    st = str(step.get("status") or "").strip().lower()
    return st in ("blocked", "needs_data", "current", "pending")


def _merge_manual_item(prev: Optional[dict[str, Any]], auto: dict[str, Any]) -> dict[str, Any]:
    if not prev or not isinstance(prev, dict):
        return auto
    if str(prev.get("source") or "") == "manual" and str(prev.get("status") or "") == ITEM_SATISFIED:
        out = {**auto, **prev}
        out["source"] = "manual"
        return out
    return {**prev, **auto}


async def ensure_hr_review_for_employee(
    db: AsyncSession,
    tenant_id: str,
    employee: WorkforceEmployee,
    *,
    sync_from_sources: bool = True,
) -> WorkforceHrReview:
    tid = str(tenant_id).strip()
    eid = str(employee.id).strip()
    row = (
        await db.execute(
            select(WorkforceHrReview).where(
                WorkforceHrReview.tenant_id == tid,
                WorkforceHrReview.employee_id == eid,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        cid = str(employee.candidate_id or "").strip() or None
        orphan = None
        if cid:
            orphan = (
                await db.execute(
                    select(WorkforceHrReview).where(
                        WorkforceHrReview.tenant_id == tid,
                        WorkforceHrReview.candidate_id == cid,
                        WorkforceHrReview.employee_id.is_(None),
                    )
                )
            ).scalar_one_or_none()
        if orphan is not None:
            row = orphan
            row.employee_id = eid
            hid = _handoff_id_from_employee(employee)
            if hid and not row.handoff_id:
                row.handoff_id = hid
            await db.flush()
        else:
            row = WorkforceHrReview(
                tenant_id=tid,
                employee_id=eid,
                candidate_id=cid,
                handoff_id=_handoff_id_from_employee(employee),
                status=HR_REVIEW_STATUS_IN_PROGRESS,
                checklist_json={"items": []},
                blockers_json=[],
                decision_basis_json={},
            )
            db.add(row)
            await db.flush()
    elif not row.handoff_id:
        hid = _handoff_id_from_employee(employee)
        if hid:
            row.handoff_id = hid
            await db.flush()
    if sync_from_sources:
        await _sync_review_from_sources(db, tid, employee, row)
    return row


async def get_hr_review_by_handoff(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: str,
) -> Optional[WorkforceHrReview]:
    tid = str(tenant_id).strip()
    hid = str(handoff_id).strip()
    return (
        await db.execute(
            select(WorkforceHrReview).where(
                WorkforceHrReview.tenant_id == tid,
                WorkforceHrReview.handoff_id == hid,
            )
        )
    ).scalar_one_or_none()


async def ensure_hr_review_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    candidate_id: str,
) -> WorkforceHrReview:
    tid = str(tenant_id).strip()
    hid = str(handoff_id).strip()
    cid = str(candidate_id).strip()
    row = await get_hr_review_by_handoff(db, tid, hid)
    if row is None:
        row = WorkforceHrReview(
            tenant_id=tid,
            handoff_id=hid,
            candidate_id=cid,
            employee_id=None,
            status=HR_REVIEW_STATUS_IN_PROGRESS,
            checklist_json={"items": []},
            blockers_json=[],
            decision_basis_json={},
        )
        db.add(row)
        await db.flush()
    elif not row.candidate_id:
        row.candidate_id = cid
        await db.flush()
    await _sync_review_from_candidate_handoff(db, tid, cid, row)
    return row


def _recompute_review_blockers_from_checklist(review: WorkforceHrReview) -> None:
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    items = [it for it in (cl.get("items") or []) if isinstance(it, dict)]
    blockers: list[str] = []
    failed_required: list[str] = []
    for it in items:
        if not it.get("required"):
            continue
        if str(it.get("status") or "") != ITEM_SATISFIED:
            failed_required.append(str(it["item_code"]))
            for b in it.get("blockers") or []:
                bs = str(b).strip()
                if bs and bs not in blockers:
                    blockers.append(bs)
    review.blockers_json = blockers
    if review.status not in HR_REVIEW_TERMINAL_STATUSES:
        review.status = _derive_status_from_blockers(blockers, failed_required)
        if (review.corrections_note or "").strip():
            review.status = HR_REVIEW_STATUS_WAITING_DOCUMENTS


async def _sync_review_from_candidate_handoff(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    review: WorkforceHrReview,
) -> None:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        return
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        return

    docs = await list_candidate_documents_via_contract(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        include_deleted=False,
    )
    n_docs = len(docs)
    identity_ok = bool((cand.first_name or "").strip() and (cand.last_name or "").strip())
    docs_ok = n_docs > 0

    prev_items = {}
    cl_old = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in cl_old.get("items") or []:
        if isinstance(it, dict) and it.get("item_code"):
            prev_items[str(it["item_code"])] = it

    def item(code: str, *, satisfied: bool, blocked: bool, basis: dict, blockers: list[str]) -> dict[str, Any]:
        prev = prev_items.get(code)
        auto = {
            "item_code": code,
            "label": CHECKLIST_LABELS[code],
            "status": ITEM_SATISFIED if satisfied else (ITEM_BLOCKED if blocked else ITEM_NEEDS_ATTENTION),
            "source": "auto",
            "required": code in REQUIRED_CHECKLIST_ITEMS,
            "blockers": blockers,
            "basis": basis,
            "verified_by_user_id": None,
            "verified_at": None,
        }
        return _merge_manual_item(prev, auto)

    items = [
        item("identity_verified", satisfied=identity_ok, blocked=False, basis={"candidate_id": candidate_id}, blockers=[]),
        item("legal_stay_verified", satisfied=False, blocked=False, basis={"pre_employee": True}, blockers=[]),
        item("work_permit_verified", satisfied=False, blocked=False, basis={"pre_employee": True}, blockers=[]),
        item("red_paper_verified", satisfied=False, blocked=False, basis={"pre_employee": True}, blockers=[]),
        item(
            "required_payments_confirmed",
            satisfied=False,
            blocked=False,
            basis={"pre_employee": True},
            blockers=[],
        ),
        item(
            "documents_uploaded",
            satisfied=docs_ok,
            blocked=not docs_ok,
            basis={"documents_count": n_docs},
            blockers=[] if docs_ok else ["missing_documents"],
        ),
        item("zus_readiness_confirmed", satisfied=False, blocked=False, basis={"pre_employee": True}, blockers=[]),
        item("employment_data_complete", satisfied=False, blocked=True, basis={"pre_employee": True}, blockers=["employment_pending_approve"]),
    ]
    review.checklist_json = {"items": items}
    _recompute_review_blockers_from_checklist(review)
    review.decision_basis_json = {
        "generated_at": _now().isoformat(),
        "handoff_id": review.handoff_id,
        "candidate_id": candidate_id,
        "pre_employee_review": True,
        "documents_count": n_docs,
    }
    await db.flush()


async def _sync_review_from_sources(
    db: AsyncSession,
    tenant_id: str,
    employee: WorkforceEmployee,
    review: WorkforceHrReview,
) -> None:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        return

    eid = str(employee.id)
    bundle = await we_svc.get_hr_bundle(db, tenant_id, eid)
    journey = await build_work_eligibility_journey(db, tenant_id, eid)
    payments = await list_payment_requirements(db, tenant_id, eid)
    comp = bundle.get("compliance_state")
    compliance_reasons = list(getattr(comp, "reasons", None) or []) if comp else []
    missing_docs_count = int(getattr(comp, "missing_count", 0) or 0) if comp else 0

    legal = _journey_step_by_code(journey, "legal_stay")
    wp_app = _journey_step_by_code(journey, "work_permit_application")
    wp_recv = _journey_step_by_code(journey, "work_permit_received")
    rp_recv = _journey_step_by_code(journey, "red_paper_received")
    zus = _journey_step_by_code(journey, "zus_registration")

    snap = employee.candidate_snapshot if isinstance(employee.candidate_snapshot, dict) else {}
    identity_ok = bool(
        (employee.display_name or "").strip()
        and (
            str(snap.get("email") or "").strip()
            or str(snap.get("phone") or "").strip()
            or employee.candidate_id
        )
    )

    pay_blockers: list[str] = []
    for p in payments:
        st = str(getattr(p, "payment_status", "") or "").strip().lower()
        if st in ("required", "pending") and not payment_row_satisfied(p):
            pay_blockers.append(f"payment:{getattr(p, 'requirement_type', 'fee')}")

    employments = list(bundle.get("employments") or [])
    employment_ok = any(
        str(getattr(e, "contract_type", "") or "").strip() and getattr(e, "start_date", None) for e in employments
    )

    doc_summary = bundle.get("hr_document_context_summary") or {}
    doc_items = doc_summary.get("items") if isinstance(doc_summary, dict) else []
    required_unverified = 0
    if isinstance(doc_items, list):
        for it in doc_items:
            if not isinstance(it, dict):
                continue
            if it.get("required") and not it.get("verified"):
                required_unverified += 1

    docs_ok = missing_docs_count == 0 and required_unverified == 0

    prev_items = {}
    raw_cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in raw_cl.get("items") or []:
        if isinstance(it, dict) and it.get("item_code"):
            prev_items[str(it["item_code"])] = it

    def item(code: str, *, satisfied: bool, blocked: bool, basis: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
        if satisfied:
            st = ITEM_SATISFIED
        elif blocked:
            st = ITEM_BLOCKED
        else:
            st = ITEM_NEEDS_ATTENTION
        auto = {
            "item_code": code,
            "label": CHECKLIST_LABELS.get(code, code),
            "status": st,
            "source": "auto",
            "required": code in REQUIRED_CHECKLIST_ITEMS,
            "blockers": blockers,
            "basis": basis,
            "verified_by_user_id": None,
            "verified_at": None,
        }
        return _merge_manual_item(prev_items.get(code), auto)

    items = [
        item(
            "identity_verified",
            satisfied=identity_ok,
            blocked=not identity_ok,
            basis={"employee_display_name": employee.display_name, "snapshot": snap},
            blockers=[] if identity_ok else ["identity_incomplete"],
        ),
        item(
            "legal_stay_verified",
            satisfied=_step_satisfied(legal),
            blocked=_step_blocked(legal) and not _step_satisfied(legal),
            basis={"journey_step": legal},
            blockers=list(legal.get("blockers") or []) if legal else ["legal_stay_unknown"],
        ),
        item(
            "work_permit_verified",
            satisfied=_step_satisfied(wp_recv) or (_step_satisfied(wp_app) and _step_satisfied(wp_recv)),
            blocked=(_step_blocked(wp_recv) or _step_blocked(wp_app)) and not _step_satisfied(wp_recv),
            basis={"journey_steps": {"application": wp_app, "received": wp_recv}},
            blockers=list((wp_recv or wp_app or {}).get("blockers") or []),
        ),
        item(
            "red_paper_verified",
            satisfied=_step_satisfied(rp_recv),
            blocked=_step_blocked(rp_recv) and not _step_satisfied(rp_recv),
            basis={"journey_step": rp_recv},
            blockers=list(rp_recv.get("blockers") or []) if rp_recv else [],
        ),
        item(
            "required_payments_confirmed",
            satisfied=len(pay_blockers) == 0,
            blocked=len(pay_blockers) > 0,
            basis={"payments_count": len(payments), "payment_blockers": pay_blockers},
            blockers=pay_blockers,
        ),
        item(
            "documents_uploaded",
            satisfied=docs_ok,
            blocked=not docs_ok,
            basis={"missing_documents_count": missing_docs_count, "required_unverified": required_unverified},
            blockers=(["missing_documents"] if missing_docs_count else [])
            + (["unverified_required"] if required_unverified else []),
        ),
        item(
            "zus_readiness_confirmed",
            satisfied=_step_satisfied(zus),
            blocked=_step_blocked(zus) and not _step_satisfied(zus),
            basis={"journey_step": zus},
            blockers=list(zus.get("blockers") or []) if zus else ["zus_unknown"],
        ),
        item(
            "employment_data_complete",
            satisfied=employment_ok,
            blocked=not employment_ok,
            basis={"employment_rows": len(employments)},
            blockers=[] if employment_ok else ["employment_incomplete"],
        ),
    ]

    blockers: list[str] = []
    failed_required: list[str] = []
    for it in items:
        if not it.get("required"):
            continue
        if str(it.get("status") or "") != ITEM_SATISFIED:
            failed_required.append(str(it["item_code"]))
            for b in it.get("blockers") or []:
                bs = str(b).strip()
                if bs and bs not in blockers:
                    blockers.append(bs)

    review.checklist_json = {"items": items}
    review.blockers_json = blockers
    review.decision_basis_json = await build_hr_decision_basis(
        db,
        tenant_id,
        employee,
        journey=journey,
        compliance_reasons=compliance_reasons,
    )
    review.status = _derive_status_from_blockers(blockers, failed_required)
    if (review.corrections_note or "").strip() and review.status not in HR_REVIEW_TERMINAL_STATUSES:
        review.status = HR_REVIEW_STATUS_WAITING_DOCUMENTS
    await db.flush()


def _derive_status_from_blockers(blockers: list[str], failed_items: list[str]) -> str:
    if not failed_items:
        return HR_REVIEW_STATUS_IN_PROGRESS
    joined = " ".join(blockers).lower()
    if any(x in joined for x in ("document", "missing_doc", "unverified")):
        return HR_REVIEW_STATUS_WAITING_DOCUMENTS
    if any(x in joined for x in ("payment", "fee")):
        return HR_REVIEW_STATUS_WAITING_PAYMENTS
    if "red_paper" in joined:
        return HR_REVIEW_STATUS_WAITING_RED_PAPER
    if any(x in joined for x in ("work_permit", "permit")):
        return HR_REVIEW_STATUS_WAITING_WORK_PERMIT
    return HR_REVIEW_STATUS_IN_PROGRESS


async def build_hr_decision_basis(
    db: AsyncSession,
    tenant_id: str,
    employee: WorkforceEmployee,
    *,
    journey: Optional[dict[str, Any]] = None,
    compliance_reasons: Optional[list[Any]] = None,
) -> dict[str, Any]:
    eid = str(employee.id)
    if journey is None:
        journey = await build_work_eligibility_journey(db, tenant_id, eid)
    if compliance_reasons is None:
        bundle = await we_svc.get_hr_bundle(db, tenant_id, eid)
        comp = bundle.get("compliance_state")
        compliance_reasons = list(getattr(comp, "reasons", None) or []) if comp else []

    steps_out = []
    for s in journey.get("steps") or []:
        if not isinstance(s, dict):
            continue
        steps_out.append(
            {
                "step_code": s.get("step_code"),
                "label": s.get("label"),
                "status": s.get("status"),
                "rule_code": s.get("rule_code"),
                "decision_reason": s.get("decision_reason"),
                "cannot_determine_reason": s.get("cannot_determine_reason"),
                "input_facts": s.get("input_facts"),
                "blockers": s.get("blockers"),
            }
        )

    return {
        "generated_at": _now().isoformat(),
        "handoff_id": _handoff_id_from_employee(employee),
        "candidate_snapshot": employee.candidate_snapshot,
        "eligibility_steps": steps_out,
        "compliance_reasons": compliance_reasons[:20],
        "recommended_next_action": journey.get("recommended_next_action"),
        "next_hr_action": journey.get("next_hr_action"),
    }


def _documents_for_approval(bundle: dict[str, Any], journey: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = bundle.get("hr_document_context_summary") or {}
    items = summary.get("items") if isinstance(summary, dict) else []

    def ctx_row(label: str, context_types: tuple[str, ...]) -> dict[str, Any]:
        match = None
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                ct = str(it.get("context_type") or "").strip().lower()
                if ct in context_types:
                    match = it
                    break
        if match:
            st = "verified" if match.get("verified") else "uploaded" if match.get("document_id") else "missing"
        else:
            st = "missing"
        return {
            "document_key": label,
            "label": label,
            "status": st,
            "context_type": match.get("context_type") if match else None,
            "document_id": match.get("document_id") if match else None,
            "verified": bool(match.get("verified")) if match else False,
            "expires_at": match.get("expires_at") if match else None,
        }

    rows.append(ctx_row("Legal stay", ("legal_stay", "residence_permit", "visa")))
    rows.append(ctx_row("Work permit", ("work_permit", "work_permit_application")))
    rows.append(ctx_row("Red paper", ("red_paper", "red_paper_certificate")))
    rows.append(ctx_row("Medical", ("medical", "medical_certificate")))
    rows.append(ctx_row("Psychological", ("psychological", "psychological_certificate")))
    rows.append(ctx_row("Driver license", ("driver_license", "driver_license_code95")))
    rows.append(ctx_row("Code95", ("code95", "driver_license_code95")))
    rows.append(ctx_row("Tacho card", ("tacho_card", "tachograph_card")))

    legal = _journey_step_by_code(journey, "legal_stay")
    if legal and str(legal.get("status") or "") == "needs_data":
        for r in rows:
            if r["document_key"] == "Legal stay":
                r["status"] = "needs_data"
                r["basis"] = legal.get("cannot_determine_reason") or legal.get("decision_reason")
    return rows


async def _attach_verified_fields_to_panel(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    panel: dict[str, Any],
    *,
    employee_id: Optional[str] = None,
) -> dict[str, Any]:
    position_category = await resolve_position_category_for_review(
        db,
        tenant_id,
        employee_id=employee_id or review.employee_id,
        candidate_id=review.candidate_id,
    )
    critical_field_codes = resolve_critical_field_codes(position_category)
    panel = dict(panel)
    panel["position_category"] = position_category
    panel["verification_critical_field_codes"] = sorted(critical_field_codes)

    await vf_svc.ensure_critical_field_placeholders(
        db,
        tenant_id=tenant_id,
        review=review,
        employee_id=employee_id or review.employee_id,
        critical_field_codes=critical_field_codes,
    )
    fields = await vf_svc.list_for_review(
        db, tenant_id, review.id, critical_field_codes=critical_field_codes
    )
    summary = vf_svc.summarize_critical(fields, critical_field_codes=critical_field_codes)
    vf_blocked, vf_blockers = vf_svc.critical_fields_block_approval(fields)
    if vf_blocked:
        panel = dict(panel)
        panel["can_approve"] = False
        panel["blockers"] = list(dict.fromkeys(list(panel.get("blockers") or []) + vf_blockers))
    panel = dict(panel)
    panel["verified_fields"] = fields
    panel["verified_fields_summary"] = summary
    trusted = await get_trusted_employment_identity(
        db,
        tenant_id=tenant_id,
        review_id=review.id,
        consumer=CONSUMER_HR_REVIEW_DISPLAY,
        raise_on_denied=False,
    )
    panel["employment_identity"] = trusted.projection
    return await rebuild_panel_checklists_after_data_verification(db, tenant_id, review, panel)


async def build_hr_review_panel(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
) -> Optional[dict[str, Any]]:
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        return None
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    bundle = await we_svc.get_hr_bundle(db, tenant_id, employee_id)
    journey = await build_work_eligibility_journey(db, tenant_id, employee_id)

    items = []
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in cl.get("items") or []:
        if isinstance(it, dict):
            items.append(it)

    blockers = list(review.blockers_json or [])
    failed_required = [
        str(it["item_code"])
        for it in items
        if it.get("required") and str(it.get("status") or "") != ITEM_SATISFIED
    ]
    can_approve = review.status not in HR_REVIEW_TERMINAL_STATUSES and not failed_required

    next_action = None
    if blockers:
        next_action = f"Resolve: {', '.join(blockers[:3])}"
    elif journey.get("next_hr_action") and isinstance(journey["next_hr_action"], dict):
        next_action = journey["next_hr_action"].get("title") or journey.get("recommended_next_action")
    else:
        next_action = journey.get("recommended_next_action")

    hid = review.handoff_id or _handoff_id_from_employee(emp)
    legacy_rows = _documents_for_approval(bundle, journey)
    legacy_rows = await merge_candidate_documents_into_approval_rows(
        db, tenant_id, str(emp.candidate_id or ""), legacy_rows
    )
    verification_plan = await build_hr_verification_plan(
        db,
        tenant_id,
        review,
        employee=emp,
        candidate=await db.get(Candidate, str(emp.candidate_id)) if emp.candidate_id else None,
        legacy_approval_rows=legacy_rows,
        bundle=bundle,
        journey=journey,
    )
    docs_rows = documents_for_approval_from_plan(verification_plan)
    docs_rows = await merge_candidate_documents_into_approval_rows(
        db, tenant_id, str(emp.candidate_id or ""), docs_rows
    )
    docs_for_approval = enrich_documents_for_approval_open_urls(
        docs_rows,
        tenant_id=tenant_id,
        workforce_employee_id=employee_id,
        handoff_id=str(hid) if hid else None,
    )
    wel = bundle.get("work_eligibility_profile")
    eligibility_hint = (
        {
            "citizenship": getattr(wel, "citizenship", None),
            "work_country": getattr(wel, "work_country", None),
            "pesel": getattr(wel, "pesel", None),
        }
        if wel
        else None
    )
    docs_for_approval = await enrich_approval_rows_with_verification(
        db,
        tenant_id,
        review,
        docs_for_approval,
        employee=emp,
        eligibility=eligibility_hint,
    )
    await sync_checklist_from_verifications(db, tenant_id, review, docs_for_approval)
    items = []
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in cl.get("items") or []:
        if isinstance(it, dict):
            items.append(it)
    blockers = list(review.blockers_json or [])
    failed_required = [
        str(it["item_code"])
        for it in items
        if it.get("required") and str(it.get("status") or "") != ITEM_SATISFIED
    ]
    panel: dict[str, Any] = {
        "review_id": review.id,
        "employee_id": employee_id,
        "candidate_id": emp.candidate_id,
        "handoff_id": hid,
        "status": review.status,
        "checklist": items,
        "blockers": blockers,
        "failed_required_items": failed_required,
        "can_approve": False,
        "next_required_action": next_action,
        "decision_basis": review.decision_basis_json,
        "documents_for_approval": docs_for_approval,
        "corrections_note": review.corrections_note,
        "return_reason": review.return_reason,
        "reject_reason": review.reject_reason,
        "decided_by_user_id": review.decided_by_user_id,
        "decided_at": review.decided_at.isoformat() if review.decided_at else None,
    }
    panel = await _attach_verified_fields_to_panel(db, tenant_id, review, panel, employee_id=employee_id)
    panel["verification_plan"] = sync_verification_plan_with_enriched_docs(
        verification_plan, docs_for_approval
    )
    panel["can_approve"] = finalize_hr_review_can_approve(panel)
    handoff_status = None
    transferred_at = None
    if hid:
        ho = await db.get(CandidateHandoff, str(hid))
        if ho:
            handoff_status = str(ho.status or "")
            transferred_at = ho.requested_at.isoformat() if ho.requested_at else None
    delayed = await delayed_hr_workforce_creation_enabled(db, tenant_id)
    return enrich_hr_review_panel(
        panel,
        handoff_status=handoff_status,
        candidate_display_name=emp.display_name,
        employee_status=str(emp.status or ""),
        journey=journey,
        delayed_workforce=delayed,
        transferred_at=transferred_at,
    )


async def update_hr_review_checklist_item(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    item_code: str,
    actor_user_id: str,
    satisfied: bool = True,
) -> WorkforceHrReview:
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")

    code = str(item_code or "").strip()
    if code not in CHECKLIST_LABELS:
        raise ValueError("INVALID_CHECKLIST_ITEM")
    if satisfied and code in VERIFICATION_GATED_CHECKLIST:
        raise ValueError("CHECKLIST_REQUIRES_DOCUMENT_VERIFICATION")

    cl = dict(review.checklist_json or {"items": []})
    items = list(cl.get("items") or [])
    found = False
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        if str(it.get("item_code") or "") != code:
            continue
        items[i] = {
            **it,
            "item_code": code,
            "label": CHECKLIST_LABELS[code],
            "status": ITEM_SATISFIED if satisfied else ITEM_NEEDS_ATTENTION,
            "source": "manual",
            "required": code in REQUIRED_CHECKLIST_ITEMS,
            "blockers": [] if satisfied else it.get("blockers") or [],
            "basis": it.get("basis") or {},
            "verified_by_user_id": actor_user_id if satisfied else None,
            "verified_at": _now().isoformat() if satisfied else None,
        }
        found = True
        break
    if not found:
        items.append(
            {
                "item_code": code,
                "label": CHECKLIST_LABELS[code],
                "status": ITEM_SATISFIED if satisfied else ITEM_NEEDS_ATTENTION,
                "source": "manual",
                "required": code in REQUIRED_CHECKLIST_ITEMS,
                "blockers": [],
                "basis": {},
                "verified_by_user_id": actor_user_id if satisfied else None,
                "verified_at": _now().isoformat() if satisfied else None,
            }
        )
    cl["items"] = items
    review.checklist_json = cl
    await _sync_review_from_sources(db, tenant_id, emp, review)
    return review


async def _assert_can_approve(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    *,
    employee: Optional[WorkforceEmployee] = None,
) -> None:
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    emp = employee
    if emp is None and review.employee_id:
        emp = await we_svc.get_employee(db, tenant_id, str(review.employee_id))
    if emp is not None:
        runtime = await resolve_workforce_eligibility_via_contract(
            db,
            context=WorkforceEligibilityContext(
                tenant_id=str(tenant_id),
                employee_id=str(emp.id),
                candidate_id=str(emp.candidate_id) if emp.candidate_id else None,
                stage="hr",
            ),
        )
        allowed_ops = dict(runtime.get("allowed_operations") or {})
        if not bool(allowed_ops.get("approve_hr_verification", True)):
            decision_reasons = [
                str(r.get("reason") or r.get("code") or "").strip()
                for r in (runtime.get("blocking_reasons") or [])
                if isinstance(r, dict) and str(r.get("reason") or r.get("code") or "").strip()
            ]
            raise HrReviewBlockedError(
                blockers=decision_reasons,
                failed_items=decision_reasons or ["decision.approve_hr_verification_blocked"],
            )

        panel = await build_hr_review_panel(db, tenant_id, str(emp.id))
        plan = panel.get("verification_plan") if isinstance(panel, dict) else None
        if _is_hybrid_verification_plan(plan):
            if not finalize_hr_review_can_approve(panel):
                reasons = [str(r) for r in (plan.get("blocking_reasons") or []) if str(r).strip()]
                raise HrReviewBlockedError(blockers=reasons, failed_items=reasons or ["verification_plan"])
            return
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    failed: list[str] = []
    blockers: list[str] = list(review.blockers_json or [])
    for it in cl.get("items") or []:
        if not isinstance(it, dict) or not it.get("required"):
            continue
        if str(it.get("status") or "") != ITEM_SATISFIED:
            failed.append(str(it["item_code"]))
    fields = await vf_svc.list_for_review(db, tenant_id, review.id)
    vf_blocked, vf_blockers = vf_svc.critical_fields_block_approval(fields)
    if vf_blocked:
        failed.extend([f"verified_field:{c}" for c in (vf_svc.summarize_critical(fields).get("pending_codes") or [])])
        failed.extend([f"verified_field_conflict:{c}" for c in (vf_svc.summarize_critical(fields).get("conflict_codes") or [])])
        raise HrReviewBlockedError(blockers=blockers + vf_blockers, failed_items=failed)
    if failed:
        raise HrReviewBlockedError(blockers=blockers, failed_items=failed)


async def approve_hr_review_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    review: WorkforceHrReview,
    employee: WorkforceEmployee,
    actor_user_id: str,
) -> WorkforceHrReview:
    await _sync_review_from_sources(db, tenant_id, employee, review)
    await _assert_can_approve(db, tenant_id, review, employee=employee)
    now = _now()
    review.status = HR_REVIEW_STATUS_APPROVED
    review.decided_by_user_id = actor_user_id
    review.decided_at = now
    review.blockers_json = []
    if employee.status == "onboarding":
        employee.status = "active"
    await db.flush()
    return review


async def approve_hr_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
) -> WorkforceHrReview:
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    hid = (review.handoff_id or _handoff_id_from_employee(emp) or "").strip()
    if hid:
        from backend.app.services.hr_acceptance_orchestrator import approve_employment_for_handoff

        _emp, review = await approve_employment_for_handoff(
            db,
            tenant_id=tenant_id,
            handoff_id=hid,
            actor_user_id=actor_user_id,
        )
        return review
    return await approve_hr_review_record(
        db,
        tenant_id=tenant_id,
        review=review,
        employee=emp,
        actor_user_id=actor_user_id,
    )


async def build_hr_review_panel_for_handoff(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: str,
) -> Optional[dict[str, Any]]:
    review = await get_hr_review_by_handoff(db, tenant_id, handoff_id)
    if not review:
        return None
    if review.employee_id:
        return await build_hr_review_panel(db, tenant_id, str(review.employee_id))

    cid = str(review.candidate_id or "").strip()
    if cid:
        await _sync_review_from_candidate_handoff(db, tenant_id, cid, review)

    items = []
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in cl.get("items") or []:
        if isinstance(it, dict):
            items.append(it)
    blockers = list(review.blockers_json or [])
    failed_required = [
        str(it["item_code"])
        for it in items
        if it.get("required") and str(it.get("status") or "") != ITEM_SATISFIED
    ]
    can_approve = review.status not in HR_REVIEW_TERMINAL_STATUSES and not failed_required
    next_action = f"Resolve: {', '.join(blockers[:3])}" if blockers else "Complete HR review checklist"

    hid = str(handoff_id).strip()
    handoff = await db.get(CandidateHandoff, hid)
    handoff_status = str(handoff.status or "") if handoff else None
    transferred_at = handoff.requested_at.isoformat() if handoff and handoff.requested_at else None
    cand_name = None
    if review.candidate_id:
        cand = await db.get(Candidate, str(review.candidate_id))
        if cand:
            parts = [str(cand.first_name or "").strip(), str(cand.last_name or "").strip()]
            cand_name = " ".join(p for p in parts if p).strip() or None

    emp_for_panel: Optional[WorkforceEmployee] = None
    cand_row = await db.get(Candidate, str(review.candidate_id)) if review.candidate_id else None
    if review.employee_id:
        emp_for_panel = await we_svc.get_employee(db, tenant_id, str(review.employee_id))
    legacy_rows = _documents_for_approval({}, {})
    legacy_rows = await merge_candidate_documents_into_approval_rows(
        db, tenant_id, str(review.candidate_id or ""), legacy_rows
    )
    verification_plan = await build_hr_verification_plan(
        db,
        tenant_id,
        review,
        employee=emp_for_panel,
        candidate=cand_row,
        legacy_approval_rows=legacy_rows,
        bundle={},
        journey={},
    )
    docs_rows = documents_for_approval_from_plan(verification_plan)
    docs_rows = await merge_candidate_documents_into_approval_rows(
        db, tenant_id, str(review.candidate_id or ""), docs_rows
    )
    docs_for_approval = enrich_documents_for_approval_open_urls(
        docs_rows,
        tenant_id=tenant_id,
        workforce_employee_id=str(review.employee_id) if review.employee_id else None,
        handoff_id=hid,
    )
    wel_hint = None
    if emp_for_panel and review.employee_id:
        wel = await we_svc.get_work_eligibility_profile(db, tenant_id, str(review.employee_id))
        if wel:
            wel_hint = {
                "citizenship": getattr(wel, "citizenship", None),
                "work_country": getattr(wel, "work_country", None),
                "pesel": getattr(wel, "pesel", None),
            }
    docs_for_approval = await enrich_approval_rows_with_verification(
        db,
        tenant_id,
        review,
        docs_for_approval,
        employee=emp_for_panel,
        eligibility=wel_hint,
    )
    await sync_checklist_from_verifications(db, tenant_id, review, docs_for_approval)
    items = []
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    for it in cl.get("items") or []:
        if isinstance(it, dict):
            items.append(it)
    blockers = list(review.blockers_json or [])
    failed_required = [
        str(it["item_code"])
        for it in items
        if it.get("required") and str(it.get("status") or "") != ITEM_SATISFIED
    ]
    can_approve = review.status not in HR_REVIEW_TERMINAL_STATUSES and not failed_required

    panel: dict[str, Any] = {
        "review_id": review.id,
        "employee_id": review.employee_id,
        "handoff_id": review.handoff_id,
        "candidate_id": review.candidate_id,
        "status": review.status,
        "checklist": items,
        "blockers": blockers,
        "failed_required_items": failed_required,
        "can_approve": can_approve,
        "next_required_action": next_action,
        "decision_basis": review.decision_basis_json,
        "documents_for_approval": docs_for_approval,
        "corrections_note": review.corrections_note,
        "return_reason": review.return_reason,
        "reject_reason": review.reject_reason,
        "decided_by_user_id": review.decided_by_user_id,
        "decided_at": review.decided_at.isoformat() if review.decided_at else None,
    }
    panel = await _attach_verified_fields_to_panel(db, tenant_id, review, panel)
    panel["verification_plan"] = sync_verification_plan_with_enriched_docs(
        verification_plan, docs_for_approval
    )
    panel["can_approve"] = finalize_hr_review_can_approve(panel)
    delayed = await delayed_hr_workforce_creation_enabled(db, tenant_id)
    return enrich_hr_review_panel(
        panel,
        handoff_status=handoff_status,
        candidate_display_name=cand_name,
        transferred_at=transferred_at,
        delayed_workforce=delayed,
    )


async def update_hr_review_checklist_item_for_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff_id: str,
    item_code: str,
    actor_user_id: str,
    satisfied: bool = True,
) -> WorkforceHrReview:
    review = await get_hr_review_by_handoff(db, tenant_id, handoff_id)
    if not review:
        raise ValueError("HR_REVIEW_NOT_FOUND")
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")

    code = str(item_code or "").strip()
    if code not in CHECKLIST_LABELS:
        raise ValueError("INVALID_CHECKLIST_ITEM")
    if satisfied and code in VERIFICATION_GATED_CHECKLIST:
        raise ValueError("CHECKLIST_REQUIRES_DOCUMENT_VERIFICATION")

    cl = dict(review.checklist_json or {"items": []})
    items = list(cl.get("items") or [])
    found = False
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        if str(it.get("item_code") or "") != code:
            continue
        items[i] = {
            **it,
            "item_code": code,
            "label": CHECKLIST_LABELS[code],
            "status": ITEM_SATISFIED if satisfied else ITEM_NEEDS_ATTENTION,
            "source": "manual",
            "required": code in REQUIRED_CHECKLIST_ITEMS,
            "blockers": [] if satisfied else it.get("blockers") or [],
            "basis": it.get("basis") or {},
            "verified_by_user_id": actor_user_id if satisfied else None,
            "verified_at": _now().isoformat() if satisfied else None,
        }
        found = True
        break
    if not found:
        items.append(
            {
                "item_code": code,
                "label": CHECKLIST_LABELS[code],
                "status": ITEM_SATISFIED if satisfied else ITEM_NEEDS_ATTENTION,
                "source": "manual",
                "required": code in REQUIRED_CHECKLIST_ITEMS,
                "blockers": [],
                "basis": {},
                "verified_by_user_id": actor_user_id if satisfied else None,
                "verified_at": _now().isoformat() if satisfied else None,
            }
        )
    cl["items"] = items
    review.checklist_json = cl

    if review.employee_id:
        emp = await we_svc.get_employee(db, tenant_id, str(review.employee_id))
        if emp:
            await _sync_review_from_sources(db, tenant_id, emp, review)
            return review
    _recompute_review_blockers_from_checklist(review)
    await db.flush()
    return review


async def rebuild_hr_review_panel_for_review(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
) -> Optional[dict[str, Any]]:
    if review.employee_id:
        return await build_hr_review_panel(db, tenant_id, str(review.employee_id))
    if review.handoff_id:
        return await build_hr_review_panel_for_handoff(db, tenant_id, str(review.handoff_id))
    return None


async def return_hr_review_to_recruitment(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
    return_reason: str,
) -> WorkforceHrReview:
    reason = str(return_reason or "").strip()
    if not reason:
        raise ValueError("RETURN_REASON_REQUIRED")
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")

    hid = review.handoff_id or _handoff_id_from_employee(emp)
    if hid:
        handoff, err = await return_handoff(
            db,
            handoff_id=hid,
            reviewed_by_user_id=actor_user_id,
            return_reason=reason,
            tenant_id=tenant_id,
        )
        if err:
            raise ValueError(err)

    review.status = HR_REVIEW_STATUS_RETURNED
    review.return_reason = reason
    review.decided_by_user_id = actor_user_id
    review.decided_at = _now()
    emp.status = "returned_to_recruitment"
    await db.flush()
    return review


async def request_hr_review_corrections(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
    note: str,
) -> WorkforceHrReview:
    note_s = str(note or "").strip()
    if not note_s:
        raise ValueError("CORRECTIONS_NOTE_REQUIRED")
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    review.corrections_note = note_s
    await _sync_review_from_sources(db, tenant_id, emp, review)
    review.decided_by_user_id = None
    review.decided_at = None
    await db.flush()
    return review


async def reject_hr_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
    actor_user_id: str,
    reject_reason: str,
) -> WorkforceHrReview:
    reason = str(reject_reason or "").strip()
    if not reason:
        raise ValueError("REJECT_REASON_REQUIRED")
    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    review = await ensure_hr_review_for_employee(db, tenant_id, emp)
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        raise ValueError("HR_REVIEW_TERMINAL")
    review.status = HR_REVIEW_STATUS_REJECTED
    review.reject_reason = reason
    review.decided_by_user_id = actor_user_id
    review.decided_at = _now()
    emp.status = "terminated"
    await db.flush()
    return review
