"""Resolve mapping rules for ingest — MA-2 wrapper around the one resolver.

Callers keep this import path. The precedence chain is gone: leftover Meta
form / tenant stores are read-through only inside ``resolve_mapping_authority``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.mapping_resolve import resolve_mapping_authority


async def resolve_field_mapping_for_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    payload: Dict[str, Any],
    source: str = "meta",
    settings_row: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    result = await resolve_mapping_authority(
        db,
        tenant_id=tenant_id,
        payload=payload,
        source=source,
        settings_row=settings_row,
    )
    return list(result.rules)
