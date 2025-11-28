# owner_summary.py
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Set, Tuple

from ...models.enums import DocumentStatus
from ...services.document_ruleset import load_default_ruleset
from .rules_engine import compute_candidate_checklist, expiring_threshold_for

_DEFAULT_RULESET = load_default_ruleset()
_DEFAULT_CANDIDATE_DEFAULTS = (
    (_DEFAULT_RULESET.get("candidate") or {}).get("defaults") or {}
)

READY_STATUSES: Set[str] = {
    DocumentStatus.approved.value,
    DocumentStatus.received.value,
    DocumentStatus.delivered.value,
    DocumentStatus.completed.value,
    DocumentStatus.submitted.value,
}
IN_PROGRESS_STATUSES: Set[str] = {
    DocumentStatus.requested.value,
    DocumentStatus.in_progress.value,
    DocumentStatus.submitted.value,
}
PROBLEM_STATUSES: Set[str] = {
    DocumentStatus.rejected.value,
    DocumentStatus.expired.value,
    DocumentStatus.overdue.value,
}

EQUIVALENT_SATISFACTION: Dict[str, List[str]] = {
    "driver_license_code95": ["driver_license", "code95"],
}


def _normalize_status(value: Any) -> str:
    if isinstance(value, DocumentStatus):
        return value.value
    return str(value or "").lower()


def _classify_required_type(statuses: Dict[str, int]) -> Tuple[str, str]:
    """
    Returns tuple (bucket, representative_status)
    bucket ∈ {"ready","in_progress","problem","missing"}
    """
    for status in READY_STATUSES:
        if statuses.get(status, 0) > 0:
            return ("ready", status)
    for status in PROBLEM_STATUSES:
        if statuses.get(status, 0) > 0:
            return ("problem", status)
    for status in IN_PROGRESS_STATUSES:
        if statuses.get(status, 0) > 0:
            return ("in_progress", status)
    return ("missing", DocumentStatus.missing.value)


def _apply_default_checklist(checklist: Dict[str, Any], ruleset: Dict[str, Any]) -> Dict[str, Any]:
    defaults = (ruleset.get("candidate") or {}).get("defaults") or {}
    fallback = _DEFAULT_CANDIDATE_DEFAULTS
    if not checklist.get("requiredTypes"):
        checklist["requiredTypes"] = list(
            defaults.get("requiredTypes")
            or fallback.get("requiredTypes")
            or []
        )
    if not checklist.get("optionalTypes"):
        checklist["optionalTypes"] = list(
            defaults.get("optionalTypes")
            or fallback.get("optionalTypes")
            or []
        )
    return checklist


def compute_owner_summary(
    ctx: Dict[str, Any], ruleset: Dict[str, Any], docs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    checklist = _apply_default_checklist(compute_candidate_checklist(ctx, ruleset), ruleset)
    required = checklist.get("requiredTypes", []) or []

    # индекс статусов по типам
    by_type: Dict[str, Dict[str, Any]] = {}
    for d in docs:
        t = d.get("type") or d.get("doc_type")
        if not t:
            continue
        targets = EQUIVALENT_SATISFACTION.get(str(t)) or [str(t)]
        status_map = {status.value: 0 for status in DocumentStatus}
        for target in targets:
            cur = by_type.setdefault(
                target,
                status_map.copy(),
            )
            st = _normalize_status(d.get("status"))
            if st not in cur:
                cur[st] = 0
            cur[st] += 1
            by_type[target] = cur

    ready_types: List[str] = []
    in_progress_types: List[str] = []
    problematic_types: List[str] = []
    missing_types: List[str] = []

    for t in required:
        statuses = by_type.get(t, {})
        bucket, _ = _classify_required_type(statuses)
        if bucket == "ready":
            ready_types.append(t)
        elif bucket == "problem":
            problematic_types.append(t)
        elif bucket == "in_progress":
            in_progress_types.append(t)
        else:
            missing_types.append(t)

    expiring_soon: List[Dict[str, Any]] = []
    today = date.today()
    for d in docs:
        doc_type = d.get("type") or d.get("doc_type")
        expires_at = d.get("expires_at") or d.get("expire_date")
        if not doc_type or not expires_at:
            continue
        try:
            exp_date = datetime.fromisoformat(str(expires_at)[:10]).date()
        except Exception:
            continue
        threshold = expiring_threshold_for(doc_type, ruleset)
        if threshold <= 0:
            continue
        if today <= exp_date <= (today + timedelta(days=threshold)):
            expiring_soon.append({"type": doc_type, "expires_at": str(exp_date)})

    total_req = len(required)
    ready_count = len(ready_types)
    percent_ready = 100 if total_req == 0 else round(100 * ready_count / total_req)

    status = "ok"
    if total_req == 0:
        status = "no_required"
    elif problematic_types:
        status = "problems"
    elif expiring_soon:
        status = "expiring_soon"
    elif missing_types:
        status = "missing"
    elif in_progress_types:
        status = "in_progress"

    return {
        "status": status,
        "percent_ready": percent_ready,
        "required": {
            "total": total_req,
            "approved": ready_count,  # backward compatible alias
            "ready": ready_count,
            "in_progress": len(in_progress_types),
            "missing_count": len(missing_types),
            "problems": len(problematic_types),
            "missing": missing_types,
            "problematic": problematic_types,
            "ready_types": ready_types,
            "in_progress_types": in_progress_types,
        },
        "expiring_soon": expiring_soon,
        "checklist": checklist,
    }
