"""Service order beneficiary + execution helpers (product model, no new entities)."""

from __future__ import annotations

from typing import Any, Literal, Optional, Tuple

BeneficiaryKind = Literal["client", "candidate", "employee"]

EXECUTION_INLINE = "inline"
EXECUTION_HANDOFF = "handoff"


def resolve_beneficiary(
    *,
    company_id: Optional[str],
    candidate_id: Optional[str],
    employee_id: Optional[str],
) -> Tuple[Optional[BeneficiaryKind], Optional[str]]:
    """Return (beneficiary_kind, beneficiary_id) for a service order."""
    cid = str(company_id or "").strip() or None
    cand = str(candidate_id or "").strip() or None
    emp = str(employee_id or "").strip() or None
    owners = [
        ("client", cid),
        ("candidate", cand),
        ("employee", emp),
    ]
    active = [(kind, oid) for kind, oid in owners if oid]
    if len(active) != 1:
        return None, None
    return active[0][0], active[0][1]  # type: ignore[return-value]


def beneficiary_from_order(order: Any) -> Tuple[Optional[BeneficiaryKind], Optional[str]]:
    return resolve_beneficiary(
        company_id=getattr(order, "company_id", None),
        candidate_id=getattr(order, "candidate_id", None),
        employee_id=getattr(order, "employee_id", None),
    )


# --- Customer (Bill-To) + per-line Beneficiary (Variant B) -----------------
CustomerKind = BeneficiaryKind
_VALID_ROLE_KINDS = ("client", "candidate", "employee")


def _normalize_role_kind(value: Any) -> Optional[BeneficiaryKind]:
    kind = str(value or "").strip().lower()
    return kind if kind in _VALID_ROLE_KINDS else None  # type: ignore[return-value]


def resolve_customer(order: Any) -> Tuple[Optional[CustomerKind], Optional[str]]:
    """Who pays (Bill-To). Canonical customer_kind/customer_id, else typed owner."""
    kind = _normalize_role_kind(getattr(order, "customer_kind", None))
    cid = str(getattr(order, "customer_id", None) or "").strip() or None
    if kind and cid:
        return kind, cid
    # Fallback for legacy orders (pre-migration / typed owner materialization).
    return beneficiary_from_order(order)


def order_customer_columns(
    customer_kind: Any,
    customer_id: Any,
) -> dict[str, Optional[str]]:
    """Materialize customer into the typed FK columns used by joins/scope/billing."""
    kind = _normalize_role_kind(customer_kind)
    cid = str(customer_id or "").strip() or None
    cols: dict[str, Optional[str]] = {"company_id": None, "candidate_id": None, "employee_id": None}
    if not kind or not cid:
        return cols
    if kind == "client":
        cols["company_id"] = cid
    elif kind == "candidate":
        cols["candidate_id"] = cid
    elif kind == "employee":
        cols["employee_id"] = cid
    return cols


def resolve_item_beneficiary(
    item: Any,
    order: Any = None,
) -> Tuple[Optional[BeneficiaryKind], Optional[str]]:
    """Who receives this line. Item beneficiary, else the order customer."""
    kind = _normalize_role_kind(getattr(item, "beneficiary_kind", None))
    bid = str(getattr(item, "beneficiary_id", None) or "").strip() or None
    if kind and bid:
        return kind, bid
    if order is not None:
        return resolve_customer(order)
    return None, None


def context_vacancy_id(order: Any) -> Optional[str]:
    vid = str(getattr(order, "vacancy_id", None) or "").strip()
    return vid or None


def execution_meta(meta: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    raw = meta.get("execution")
    if isinstance(raw, dict):
        return dict(raw)
    mode = str(meta.get("execution_mode") or "").strip().lower()
    if mode in (EXECUTION_INLINE, EXECUTION_HANDOFF):
        return {"mode": mode, "handoff_action": meta.get("handoff_action")}
    return {}


def service_execution_mode(meta: Any) -> str:
    block = execution_meta(meta)
    mode = str(block.get("mode") or EXECUTION_INLINE).strip().lower()
    return EXECUTION_HANDOFF if mode == EXECUTION_HANDOFF else EXECUTION_INLINE


def service_handoff_action(meta: Any) -> Optional[str]:
    block = execution_meta(meta)
    action = str(block.get("handoff_action") or meta.get("handoff_action") if isinstance(meta, dict) else "").strip()
    return action or None


def service_requires_handoff(meta: Any) -> bool:
    return service_execution_mode(meta) == EXECUTION_HANDOFF and bool(service_handoff_action(meta))


def build_execution_meta(*, mode: str, handoff_action: Optional[str] = None) -> dict[str, Any]:
    normalized = EXECUTION_HANDOFF if str(mode or "").strip().lower() == EXECUTION_HANDOFF else EXECUTION_INLINE
    block: dict[str, Any] = {"mode": normalized}
    if normalized == EXECUTION_HANDOFF and handoff_action:
        block["handoff_action"] = str(handoff_action).strip()
    return {"execution": block, "execution_mode": normalized}


def stamp_item_execution_meta(item_meta: Optional[dict[str, Any]], service_meta: Any) -> dict[str, Any]:
    """Snapshot catalog execution onto line item (stable after catalog edits)."""
    out = dict(item_meta or {})
    if isinstance(out.get("execution"), dict):
        return out
    block = execution_meta(service_meta)
    if not block:
        block = {"mode": EXECUTION_INLINE}
    out["execution"] = block
    out["execution_mode"] = block.get("mode") or EXECUTION_INLINE
    if block.get("handoff_action"):
        out["handoff_action"] = block.get("handoff_action")
    return out


def item_execution_mode(item_meta: Any, service_meta: Any = None) -> str:
    return service_execution_mode(item_meta if execution_meta(item_meta) else service_meta)


def item_handoff_action(item_meta: Any, service_meta: Any = None) -> Optional[str]:
    if execution_meta(item_meta):
        return service_handoff_action(item_meta)
    return service_handoff_action(service_meta)


def item_requires_handoff(item_meta: Any, service_meta: Any = None) -> bool:
    mode = item_execution_mode(item_meta, service_meta)
    if mode != EXECUTION_HANDOFF:
        return False
    return bool(item_handoff_action(item_meta, service_meta))
