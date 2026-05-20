"""Unified HR data verification read-model (recruiter values + documents + verified SoT)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.workforce_hr_review import HR_REVIEW_TERMINAL_STATUSES, WorkforceHrReview
from backend.app.services.hr_verification_requirements import resolve_critical_field_codes
from backend.app.services.hr_verified_field_catalog import FIELD_CATALOG
_ITEM_SATISFIED = "satisfied"

VERIFIED_STATUSES = frozenset({"verified", "overridden"})
ITEM_STATUS_VERIFIED = "verified"
ITEM_STATUS_OVERRIDDEN = "overridden"
ITEM_STATUS_CONFLICT = "conflict"
ITEM_STATUS_PENDING = "pending"
ITEM_STATUS_MISSING = "missing"


def _pick_recruiter_value(profile_values: dict[str, Any] | None) -> Optional[str]:
    if not isinstance(profile_values, dict):
        return None
    for key in sorted(profile_values.keys(), key=lambda k: (0 if str(k).startswith("handoff.") else 1, str(k))):
        v = profile_values[key]
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def _field_label(field_code: str, field_row: Optional[dict[str, Any]], verified: Optional[dict[str, Any]]) -> str:
    if field_row and field_row.get("label"):
        return str(field_row["label"])
    if verified and verified.get("field_label"):
        return str(verified["field_label"])
    cat = FIELD_CATALOG.get(field_code) or {}
    return str(cat.get("label") or field_code)


def _pick_primary_appearance(
    appearances: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    if not appearances:
        return None, None
    scored: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for doc, field in appearances:
        score = 0
        if doc.get("document_id"):
            score += 4
        if doc.get("open_url") or doc.get("file_url"):
            score += 2
        vals = field.get("current_profile_values") or {}
        if isinstance(vals, dict) and _pick_recruiter_value(vals):
            score += 3
        if str(doc.get("verification_status") or "") == "verified":
            score += 1
        scored.append((score, doc, field))
    scored.sort(key=lambda x: x[0], reverse=True)
    _, doc, field = scored[0]
    return doc, field


def _derive_item_status(
    *,
    verified: Optional[dict[str, Any]],
    field_row: Optional[dict[str, Any]],
    recruiter_value: Optional[str],
    doc: Optional[dict[str, Any]],
) -> str:
    vf = str((verified or {}).get("status") or "").lower()
    if vf in VERIFIED_STATUSES:
        return ITEM_STATUS_VERIFIED if vf == "verified" else ITEM_STATUS_OVERRIDDEN
    if vf == "conflict":
        return ITEM_STATUS_CONFLICT
    if not recruiter_value:
        return ITEM_STATUS_MISSING
    if field_row and field_row.get("confirmed"):
        return ITEM_STATUS_PENDING
    if doc and str(doc.get("verification_status") or "") == "verified":
        return ITEM_STATUS_PENDING
    return ITEM_STATUS_PENDING


def _critical_field_codes_for_panel(panel: dict[str, Any]) -> frozenset[str]:
    raw = panel.get("verification_critical_field_codes")
    if isinstance(raw, (list, tuple)) and raw:
        return frozenset(str(x) for x in raw if str(x).strip())
    return resolve_critical_field_codes(panel.get("position_category"))


def build_data_verification_items(panel: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten document field reviews + verified SoT into one row per field_code."""
    critical_codes = _critical_field_codes_for_panel(panel)
    docs = [d for d in (panel.get("documents_for_approval") or []) if isinstance(d, dict)]
    verified_by_code: dict[str, dict[str, Any]] = {}
    for v in panel.get("verified_fields") or []:
        if isinstance(v, dict) and v.get("field_code"):
            verified_by_code[str(v["field_code"])] = v

    by_code: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for doc in docs:
        key = str(doc.get("document_key") or "")
        for f in doc.get("fields_to_review") or []:
            if not isinstance(f, dict):
                continue
            code = str(f.get("field_code") or "").strip()
            if not code:
                continue
            by_code.setdefault(code, []).append((doc, f))

    for code in critical_codes:
        if code not in by_code and code in verified_by_code:
            by_code[code] = []

    def sort_key(code: str) -> tuple:
        critical_rank = 0 if code in critical_codes else 1
        return (critical_rank, code)

    items: list[dict[str, Any]] = []
    for code in sorted(by_code.keys(), key=sort_key):
        appearances = by_code[code]
        verified = verified_by_code.get(code)
        doc, field_row = _pick_primary_appearance(appearances)

        profile_values: dict[str, Any] = {}
        if field_row:
            profile_values = dict(field_row.get("current_profile_values") or {})
        elif verified:
            profile_values = dict(verified.get("profile_values") or {})

        recruiter_value = _pick_recruiter_value(profile_values)
        current_verified = (verified or {}).get("verified_value")
        if current_verified is not None:
            current_verified = str(current_verified)

        status = _derive_item_status(
            verified=verified,
            field_row=field_row,
            recruiter_value=recruiter_value,
            doc=doc,
        )

        doc_key = (doc or {}).get("document_key") or (verified or {}).get("source_document_key")
        doc_id = (doc or {}).get("document_id") or (verified or {}).get("source_document_id")
        open_url = (doc or {}).get("open_url") or (doc or {}).get("file_url")
        doc_label = (doc or {}).get("label") or doc_key

        downstream = []
        if field_row:
            downstream = list(field_row.get("downstream_use") or [])
        elif verified:
            downstream = list(verified.get("downstream_use") or [])

        missing_reason = None
        conflict_reason = (verified or {}).get("conflict_reason")
        if status == ITEM_STATUS_MISSING:
            missing_reason = "no_recruiter_value"
            if doc and str(doc.get("status") or "").lower() == "missing":
                missing_reason = "document_missing"

        required = code in critical_codes
        has_doc = bool(doc_id and open_url)
        can_confirm = bool(
            recruiter_value
            and status in (ITEM_STATUS_PENDING, ITEM_STATUS_CONFLICT)
            and doc_key
        )
        can_correct = status in (ITEM_STATUS_PENDING, ITEM_STATUS_MISSING, ITEM_STATUS_CONFLICT)
        can_request_info = status == ITEM_STATUS_MISSING

        items.append(
            {
                "field_code": code,
                "label": _field_label(code, field_row, verified),
                "recruiter_value": recruiter_value,
                "recruiter_profile_values": profile_values,
                "current_verified_value": current_verified,
                "source_document_type": doc_key,
                "source_document_id": doc_id,
                "source_document_label": doc_label,
                "document_open_url": open_url,
                "document_verification_id": (doc or {}).get("verification_id") or (verified or {}).get(
                    "document_verification_id"
                ),
                "status": status,
                "used_for": downstream,
                "required_for_approval": required,
                "can_confirm": can_confirm,
                "can_correct": can_correct,
                "can_request_info": can_request_info,
                "can_mark_not_applicable": False,
                "conflict_reason": conflict_reason,
                "missing_reason": missing_reason,
            }
        )
    return items


def summarize_data_verification(
    items: list[dict[str, Any]],
    *,
    employment_identity: dict[str, Any] | None = None,
    verified_fields_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = len(items)
    verified_count = sum(1 for i in items if i.get("status") in VERIFIED_STATUSES)
    pending_count = sum(1 for i in items if i.get("status") == ITEM_STATUS_PENDING)
    missing_count = sum(1 for i in items if i.get("status") == ITEM_STATUS_MISSING)
    conflict_count = sum(1 for i in items if i.get("status") == ITEM_STATUS_CONFLICT)
    critical_items = [i for i in items if i.get("required_for_approval")]
    critical_verified = sum(1 for i in critical_items if i.get("status") in VERIFIED_STATUSES)
    critical_total = len(critical_items)
    docs_missing = sum(
        1
        for i in items
        if i.get("missing_reason") == "document_missing" or (i.get("required_for_approval") and not i.get("document_open_url"))
    )
    identity_status = (employment_identity or {}).get("status")
    vf = verified_fields_summary or {}
    ready = bool(vf.get("ready")) if vf else critical_verified >= critical_total and conflict_count == 0
    return {
        "total": total,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "missing_count": missing_count,
        "conflict_count": conflict_count,
        "critical_total": critical_total,
        "critical_verified": critical_verified,
        "documents_missing": docs_missing,
        "identity_status": identity_status,
        "ready_for_approval": ready,
    }


def attach_data_verification_to_panel(panel: dict[str, Any]) -> dict[str, Any]:
    out = dict(panel)
    items = build_data_verification_items(out)
    summary = summarize_data_verification(
        items,
        employment_identity=out.get("employment_identity"),
        verified_fields_summary=out.get("verified_fields_summary"),
    )
    out["data_verification_items"] = items
    out["data_verification_summary"] = summary
    return out


async def sync_checklist_from_data_verification(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    panel: dict[str, Any],
) -> None:
    """Derive identity_verified from critical data verification rows."""
    if review.status in HR_REVIEW_TERMINAL_STATUSES:
        return
    summary = panel.get("data_verification_summary") or {}
    critical_total = int(summary.get("critical_total") or 0)
    critical_verified = int(summary.get("critical_verified") or 0)
    identity_ok = critical_total > 0 and critical_verified >= critical_total and int(summary.get("conflict_count") or 0) == 0

    cl = dict(review.checklist_json or {"items": []})
    items = list(cl.get("items") or [])
    changed = False

    for i, it in enumerate(items):
        if not isinstance(it, dict) or str(it.get("item_code") or "") != "identity_verified":
            continue
        new_status = _ITEM_SATISFIED if identity_ok else "blocked"
        blockers = [] if identity_ok else ["data_verification_incomplete"]
        if str(it.get("status")) == new_status and it.get("source") == "data_verification":
            return
        items[i] = {
            **it,
            "status": new_status,
            "source": "data_verification",
            "blockers": blockers,
            "basis": {**(it.get("basis") or {}), "data_verification_sync": True, "critical_verified": critical_verified},
        }
        changed = True
        break

    if changed:
        cl["items"] = items
        review.checklist_json = cl
        from backend.app.services.workforce_hr_review import _recompute_review_blockers_from_checklist

        _recompute_review_blockers_from_checklist(review)
        await db.flush()


async def rebuild_panel_checklists_after_data_verification(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    panel: dict[str, Any],
) -> dict[str, Any]:
    """Attach data verification and sync derived checklist; refresh checklist slice on panel."""
    panel = attach_data_verification_to_panel(panel)
    await sync_checklist_from_data_verification(db, tenant_id, review, panel)
    cl = review.checklist_json if isinstance(review.checklist_json, dict) else {}
    items = [it for it in (cl.get("items") or []) if isinstance(it, dict)]
    panel = dict(panel)
    panel["checklist"] = items
    blockers = list(review.blockers_json or [])
    failed = [
        str(it["item_code"])
        for it in items
        if it.get("required") and str(it.get("status") or "") != _ITEM_SATISFIED
    ]
    panel["blockers"] = blockers
    panel["failed_required_items"] = failed
    from backend.app.services.workforce_hr_review import finalize_hr_review_can_approve

    panel["can_approve"] = finalize_hr_review_can_approve(panel)
    return panel
