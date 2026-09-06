"""Amend Sales Order commercial snapshot (ADR-032).

PATCH remains locked after non-void billables; explicit amend appends history
and bumps commercial_version.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.sales_order import SalesOrder


COMMERCIAL_FIELDS = (
    "currency",
    "payment_term_days",
    "payment_model",
    "vat_rate",
    "guarantee_days",
    "invoice_right_policy",
    "payer_company_id",
)


def snapshot_commercial(order: SalesOrder) -> dict[str, Any]:
    vat = order.vat_rate
    return {
        "currency": order.currency,
        "payment_term_days": order.payment_term_days,
        "payment_model": order.payment_model,
        "vat_rate": str(vat) if vat is not None else None,
        "guarantee_days": order.guarantee_days,
        "invoice_right_policy": order.invoice_right_policy,
        "payer_company_id": order.payer_company_id,
        "commercial_snapshot": dict(order.commercial_snapshot)
        if isinstance(order.commercial_snapshot, dict)
        else order.commercial_snapshot,
    }


def apply_amendment(
    order: SalesOrder,
    *,
    changes: dict[str, Any],
    reason: Optional[str],
    actor_user_id: Optional[str],
) -> SalesOrder:
    """Append prior commercial state, apply changes, bump version. Mutates order in-place."""
    prior = snapshot_commercial(order)
    history = list(order.commercial_versions or []) if isinstance(order.commercial_versions, list) else []
    history.append(
        {
            "version": int(getattr(order, "commercial_version", None) or 1),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "actor_user_id": actor_user_id,
            "reason": (str(reason).strip() or None) if reason else None,
            "commercial": prior,
        }
    )
    order.commercial_versions = history
    order.commercial_version = int(getattr(order, "commercial_version", None) or 1) + 1

    if "currency" in changes and changes["currency"] is not None:
        order.currency = str(changes["currency"]).strip().upper() or None
    elif "currency" in changes:
        order.currency = None
    if "payment_term_days" in changes:
        order.payment_term_days = changes["payment_term_days"]
    if "payment_model" in changes:
        val = changes["payment_model"]
        order.payment_model = (str(val).strip() or None) if val is not None else None
    if "vat_rate" in changes:
        vat = changes["vat_rate"]
        order.vat_rate = Decimal(str(vat)) if vat is not None else None
    if "guarantee_days" in changes:
        order.guarantee_days = changes["guarantee_days"]
    if "invoice_right_policy" in changes:
        val = changes["invoice_right_policy"]
        order.invoice_right_policy = (str(val).strip() or None) if val is not None else None
    if "payer_company_id" in changes:
        val = changes["payer_company_id"]
        order.payer_company_id = (str(val).strip() or None) if val else None
    if "billing_notes" in changes:
        val = changes["billing_notes"]
        order.billing_notes = (str(val).strip() or None) if val is not None else None

    # Keep live commercial_snapshot aligned with amended header.
    snap = dict(order.commercial_snapshot) if isinstance(order.commercial_snapshot, dict) else {}
    snap.update(snapshot_commercial(order))
    snap.pop("commercial_snapshot", None)
    order.commercial_snapshot = snap
    return order


async def amend_sales_order(
    db: AsyncSession,
    order: SalesOrder,
    *,
    changes: dict[str, Any],
    reason: Optional[str],
    actor_user_id: Optional[str],
) -> SalesOrder:
    if not any(k in changes for k in (*COMMERCIAL_FIELDS, "billing_notes")):
        raise ValueError("No commercial fields to amend")
    apply_amendment(order, changes=changes, reason=reason, actor_user_id=actor_user_id)
    await db.flush()
    return order
