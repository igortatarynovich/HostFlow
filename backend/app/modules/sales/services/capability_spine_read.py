"""Sales Capability UI — read-only projection of Pipeline v1 spine.

Display-only. Does not decide Capability, resolve review, convert, or write meta.
Resolves SalesInquiry from transport Lead id (current Sales HTTP facade key).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.sales.services.ambiguous_match_review import (
    STATUS_NOT_REQUIRED,
    STATUS_REQUIRED,
    STATUS_RESOLVED_CREATE_NEW,
    STATUS_RESOLVED_MATCH,
    read_review_state,
    review_blocks_convert,
)
from backend.app.modules.sales.services.convert_mapping import CONVERT_MAPPING_KEY
from backend.app.modules.sales.services.sales_inquiry_traceability import read_lineage

SPINE_CONTRACT = "sales.capability_spine_read.v1"

# Mirror convert_mapping convertible sets — display projection only (no import of privates).
_CONVERTIBLE_STATUSES = frozenset(
    {
        "received",
        "open",
        "reviewing",
        "waiting_for_information",
        "converted",
    }
)
_TERMINAL_BLOCKED_STATUSES = frozenset({"rejected", "closed", "abandoned"})
_REVIEW_CONVERT_ALLOWED = frozenset(
    {STATUS_NOT_REQUIRED, STATUS_RESOLVED_MATCH, STATUS_RESOLVED_CREATE_NEW}
)


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _read_convert_mapping(inquiry: SalesInquiry) -> Optional[dict[str, Any]]:
    meta = _record(getattr(inquiry, "meta", None))
    raw = meta.get(CONVERT_MAPPING_KEY)
    if not isinstance(raw, dict):
        return None
    if not _trim(raw.get("client_account_id")):
        return None
    return dict(raw)


def _capability_projection(inquiry: SalesInquiry) -> dict[str, Any]:
    """Capability decision stamp does not exist yet — entity_profile_code is display proxy."""
    code = _trim(getattr(inquiry, "entity_profile_code", None))
    return {
        "code": code,
        "source": "entity_profile" if code else "undecided",
        "decided": False,
    }


def _review_projection(inquiry: SalesInquiry) -> dict[str, Any]:
    state = read_review_state(inquiry)
    blocks = review_blocks_convert(inquiry)
    if state is None:
        status = STATUS_REQUIRED if blocks else STATUS_NOT_REQUIRED
        return {
            "status": status,
            "decision": None,
            "candidates": [],
            "convert_allowed": not blocks,
            "blocks_convert": blocks,
            "present": False,
        }
    review_status = str(state.get("status") or "").strip()
    decision = state.get("decision")
    candidates = state.get("candidates")
    return {
        "status": review_status or None,
        "decision": dict(decision) if isinstance(decision, dict) else None,
        "candidates": list(candidates) if isinstance(candidates, list) else [],
        "convert_allowed": review_status in _REVIEW_CONVERT_ALLOWED,
        "blocks_convert": blocks,
        "present": True,
        "reason": state.get("reason"),
        "version": state.get("version"),
    }


def _convert_projection(inquiry: SalesInquiry) -> dict[str, Any]:
    status = str(getattr(inquiry, "status", "") or "").strip()
    mapping = _read_convert_mapping(inquiry)
    blocks = review_blocks_convert(inquiry)
    if mapping is not None:
        return {
            "available": False,
            "reason": "already_converted",
            "inquiry_status": status,
            "client_account_id": _trim(mapping.get("client_account_id")),
            "mapping_present": True,
            "mapping": {
                "client_account_id": _trim(mapping.get("client_account_id")),
                "flights_ledger_id": _trim(mapping.get("flights_ledger_id")),
                "destination": _trim(mapping.get("destination")),
                "converted_at": mapping.get("converted_at"),
            },
        }
    if status in _TERMINAL_BLOCKED_STATUSES:
        return {
            "available": False,
            "reason": "invalid_inquiry_state",
            "inquiry_status": status,
            "client_account_id": None,
            "mapping_present": False,
            "mapping": None,
        }
    if blocks:
        return {
            "available": False,
            "reason": "unresolved_review",
            "inquiry_status": status,
            "client_account_id": None,
            "mapping_present": False,
            "mapping": None,
        }
    domain_ok = status in _CONVERTIBLE_STATUSES or status == "review_required"
    # review_required + not blocking is rare; still surface domain readiness only.
    if not domain_ok:
        return {
            "available": False,
            "reason": "invalid_inquiry_state",
            "inquiry_status": status,
            "client_account_id": None,
            "mapping_present": False,
            "mapping": None,
        }
    return {
        "available": True,
        "reason": None,
        "inquiry_status": status,
        "client_account_id": None,
        "mapping_present": False,
        "mapping": None,
    }


def _traceability_projection(inquiry: SalesInquiry) -> dict[str, Any]:
    lineage = read_lineage(inquiry)
    if lineage is None:
        return {"present": False, "lineage": None}
    return {
        "present": True,
        "lineage": {
            "sales_inquiry_id": _trim(lineage.get("sales_inquiry_id")),
            "client_account_id": _trim(lineage.get("client_account_id")),
            "flights_ledger_id": _trim(lineage.get("flights_ledger_id")),
            "company_id": _trim(lineage.get("company_id")),
            "destination": _trim(lineage.get("destination")),
            "recorded_at": lineage.get("recorded_at") or lineage.get("created_at"),
            "chain": list(lineage.get("chain") or [])
            if isinstance(lineage.get("chain"), list)
            else [],
        },
    }


def project_capability_spine(inquiry: SalesInquiry) -> dict[str, Any]:
    """Pure projection — no DB writes, no matching, no convert."""
    return {
        "contract": SPINE_CONTRACT,
        "sales_inquiry_id": str(inquiry.id),
        "transport_lead_id": _trim(getattr(inquiry, "lead_id", None)),
        "inquiry_status": str(getattr(inquiry, "status", "") or "").strip() or None,
        "capability": _capability_projection(inquiry),
        "review": _review_projection(inquiry),
        "convert": _convert_projection(inquiry),
        "traceability": _traceability_projection(inquiry),
    }


async def load_sales_inquiry_for_spine(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
) -> Optional[SalesInquiry]:
    """Resolve by transport Lead id first (Sales HTTP facade), then by SalesInquiry id."""
    tid = str(tenant_id).strip()
    aid = str(application_id or "").strip()
    if not tid or not aid:
        return None
    by_lead = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.tenant_id == tid, SalesInquiry.lead_id == aid)
        .limit(1)
    )
    if by_lead is not None:
        return by_lead
    row = await db.get(SalesInquiry, aid)
    if row is not None and str(row.tenant_id) == tid:
        return row
    return None


async def get_capability_spine_for_application(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
) -> dict[str, Any]:
    inquiry = await load_sales_inquiry_for_spine(
        db, tenant_id=tenant_id, application_id=application_id
    )
    if inquiry is None:
        return {
            "contract": SPINE_CONTRACT,
            "sales_inquiry_id": None,
            "transport_lead_id": str(application_id).strip() or None,
            "inquiry_status": None,
            "capability": {"code": None, "source": "undecided", "decided": False},
            "review": {
                "status": None,
                "decision": None,
                "candidates": [],
                "convert_allowed": False,
                "blocks_convert": False,
                "present": False,
            },
            "convert": {
                "available": False,
                "reason": "missing_sales_inquiry",
                "inquiry_status": None,
                "client_account_id": None,
                "mapping_present": False,
                "mapping": None,
            },
            "traceability": {"present": False, "lineage": None},
            "missing_sales_inquiry": True,
        }
    out = project_capability_spine(inquiry)
    out["missing_sales_inquiry"] = False
    return out
