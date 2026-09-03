"""RPM-2 persistence for the existing R5 tenant_delta.

Loads and saves overlay deltas that ``validate_tenant_overlay_delta`` already
accepts. Does not define merge. reason is sibling metadata — never stored in
the JSONB delta and never passed to ``merge_resolved_policy``.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant_document_policy_delta import TenantDocumentPolicyDelta
from backend.app.reference.document_policy_merge import (
    load_platform_pack_payload,
    merge_resolved_policy,
    validate_tenant_overlay_delta,
)

_ALLOWED_DELTA_ROOT_KEYS = frozenset({"candidate", "vacancy", "validity"})


def overlay_delta_payload(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of the R5 delta contract only. Reject metadata keys."""
    if not raw:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("tenant_delta must be a mapping")
    if "reason" in raw:
        raise ValueError("reason is metadata, not part of tenant_delta")
    validate_tenant_overlay_delta(raw)
    return {key: copy.deepcopy(raw[key]) for key in _ALLOWED_DELTA_ROOT_KEYS if key in raw}


def resolved_policy_from_delta(tenant_delta: Mapping[str, Any] | None) -> dict[str, Any]:
    """Existing merge only — not a sample evaluation."""
    payload = overlay_delta_payload(tenant_delta) if tenant_delta else None
    return merge_resolved_policy(payload or None)


def pack_version() -> str:
    payload = load_platform_pack_payload()
    return str(payload.get("pack_version") or "")


async def load_overlay_row(
    db: AsyncSession, tenant_id: str
) -> Optional[TenantDocumentPolicyDelta]:
    return (
        await db.execute(
            select(TenantDocumentPolicyDelta).where(
                TenantDocumentPolicyDelta.tenant_id == str(tenant_id)
            )
        )
    ).scalar_one_or_none()


async def load_persisted_tenant_delta(
    db: AsyncSession, tenant_id: str
) -> Optional[dict[str, Any]]:
    """Delta only — never includes reason. None when no overlay row exists."""
    row = await load_overlay_row(db, tenant_id)
    if row is None:
        return None
    return overlay_delta_payload(row.tenant_delta or {})


async def save_persisted_tenant_delta(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant_delta: Mapping[str, Any] | None,
    reason: str,
    updated_by_user_id: Optional[str],
) -> TenantDocumentPolicyDelta:
    payload = overlay_delta_payload(tenant_delta)
    comment = str(reason or "").strip()
    if len(comment) < 3:
        raise ValueError("reason is required")
    row = await load_overlay_row(db, tenant_id)
    if row is None:
        row = TenantDocumentPolicyDelta(
            tenant_id=str(tenant_id),
            tenant_delta=payload,
            reason=comment,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(row)
    else:
        row.tenant_delta = payload
        row.reason = comment
        row.updated_by_user_id = updated_by_user_id
    await db.commit()
    await db.refresh(row)
    return row


__all__ = [
    "load_overlay_row",
    "load_persisted_tenant_delta",
    "overlay_delta_payload",
    "pack_version",
    "resolved_policy_from_delta",
    "save_persisted_tenant_delta",
]
