"""Billing-related guards for communications API routes.

Thin module that wraps :mod:`backend.app.services.billing_restrictions`
in two helpers used across dispatch and ingest paths:

* ``_load_tenant_license_row(db, tenant_id)`` — single-source loader for
  the tenant's :class:`TenantLicense` row (returns ``None`` if absent);
* ``_require_outbound_comms_not_billing_blocked(tenant, license_row)`` —
  raises :class:`fastapi.HTTPException` 403 with a structured ``code``
  payload (``billing_past_due`` / ``billing_trial_expired``) when the
  tenant cannot send outbound messages.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 4/N).
"""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import billing_restrictions

__all__ = [
    "_load_tenant_license_row",
    "_require_outbound_comms_not_billing_blocked",
]


async def _load_tenant_license_row(
    db: AsyncSession, tenant_id: str
) -> TenantLicense | None:
    row = await db.execute(
        sa.select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1)
    )
    return row.scalar_one_or_none()


def _require_outbound_comms_not_billing_blocked(
    tenant: Tenant, license_row: TenantLicense | None = None
) -> None:
    reason = billing_restrictions.billing_write_block_reason(tenant, license_row)
    if reason == "past_due":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "billing_past_due",
                "message": "Outgoing messages are paused until subscription payment succeeds. Open Billing to retry payment.",
            },
        )
    if reason == "trial_expired":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "billing_trial_expired",
                "message": "Your trial has ended. Choose a plan in Billing to send messages.",
            },
        )
