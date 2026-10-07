"""Persistence for R5 document_policy_tenant_overlays (RPM-2).

One loader for operator API and D4 documents resolve.
Optimistic concurrency is SQL-atomic: ``SELECT … FOR UPDATE`` then
revision check under the row lock (insert races → IntegrityError → 409).
Audit in the same transaction; ``previous_delta`` is captured from the
locked row being overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import UserAuditLog
from backend.app.models.document_policy_tenant_overlay import DocumentPolicyTenantOverlay
from backend.app.reference.document_policy_merge import validate_tenant_overlay_delta
from backend.app.reference.requirement_policy_operator import (
    AUDIT_ACTION,
    EMPTY_REVISION,
)


class OverlayRevisionConflict(Exception):
    """Stale expected_revision — authority not overwritten."""

    def __init__(self, *, current_revision: int) -> None:
        self.current_revision = current_revision
        super().__init__(f"overlay revision conflict: current={current_revision}")


@dataclass(frozen=True)
class OverlaySnapshot:
    tenant_id: str
    revision: int
    delta: dict[str, Any]
    reason: str
    updated_by_user_id: Optional[str]


def _row_to_snapshot(row: DocumentPolicyTenantOverlay) -> OverlaySnapshot:
    delta = row.delta if isinstance(row.delta, dict) else {}
    return OverlaySnapshot(
        tenant_id=str(row.tenant_id),
        revision=int(row.revision or 0),
        delta=dict(delta),
        reason=str(row.reason or ""),
        updated_by_user_id=str(row.updated_by_user_id) if row.updated_by_user_id else None,
    )


async def load_tenant_overlay(
    db: AsyncSession, *, tenant_id: str
) -> Optional[OverlaySnapshot]:
    row = (
        await db.execute(
            select(DocumentPolicyTenantOverlay).where(
                DocumentPolicyTenantOverlay.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return _row_to_snapshot(row)


async def load_tenant_delta(
    db: AsyncSession, *, tenant_id: str
) -> Optional[dict[str, Any]]:
    """Delta for R5 evaluate / D4 resolve. None when no overlay row or empty delta."""
    snap = await load_tenant_overlay(db, tenant_id=tenant_id)
    if snap is None:
        return None
    return dict(snap.delta) if snap.delta else None


async def save_tenant_overlay(
    db: AsyncSession,
    *,
    tenant_id: str,
    delta: Mapping[str, Any],
    reason: str,
    expected_revision: int,
    actor_id: Optional[str],
) -> OverlaySnapshot:
    """Write overlay + UserAuditLog in the caller's open transaction.

    Caller must commit. Raises OverlayRevisionConflict on stale revision.
    """
    validate_tenant_overlay_delta(delta)
    tid = str(tenant_id).strip()
    new_delta = dict(delta)
    expected = int(expected_revision)

    # Row lock serializes concurrent writers for this tenant PK.
    row = (
        await db.execute(
            select(DocumentPolicyTenantOverlay)
            .where(DocumentPolicyTenantOverlay.tenant_id == tid)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if row is None:
        if expected != EMPTY_REVISION:
            raise OverlayRevisionConflict(current_revision=EMPTY_REVISION)
        previous_delta: dict[str, Any] = {}
        previous_revision = EMPTY_REVISION
        new_revision = 1
        row = DocumentPolicyTenantOverlay(
            tenant_id=tid,
            revision=new_revision,
            delta=new_delta,
            reason=reason,
            updated_by_user_id=actor_id,
        )
        db.add(row)
    else:
        current = int(row.revision or 0)
        if current != expected:
            raise OverlayRevisionConflict(current_revision=current)
        # Captured under FOR UPDATE — matches the revision being overwritten.
        previous_delta = dict(row.delta) if isinstance(row.delta, dict) else {}
        previous_revision = current
        new_revision = current + 1
        row.delta = new_delta
        row.reason = reason
        row.revision = new_revision
        row.updated_by_user_id = actor_id

    db.add(
        UserAuditLog(
            tenant_id=tid,
            user_id=actor_id,
            actor_id=actor_id,
            action=AUDIT_ACTION,
            payload={
                "previous_delta": previous_delta,
                "new_delta": new_delta,
                "reason": reason,
                "previous_revision": previous_revision,
                "new_revision": new_revision,
            },
        )
    )
    try:
        await db.flush()
    except IntegrityError as exc:
        # Concurrent first-insert on the same tenant_id PK.
        raise OverlayRevisionConflict(current_revision=1) from exc
    await db.refresh(row)
    return _row_to_snapshot(row)
