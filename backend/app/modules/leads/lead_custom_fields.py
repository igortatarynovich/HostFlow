"""Lead-scoped custom fields: definitions reuse CustomFieldDefinition(scope=LEAD)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.custom_field import (
    CustomFieldDefinition,
    CustomFieldEntityType,
    CustomFieldScope,
    CustomFieldValue,
)


def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
    parts = [p.strip() for p in str(path or "").split(".") if p.strip()]
    if not parts:
        return None
    node: Any = data
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _coerce_stored_value(raw: Any) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    return {"v": raw}


def _unwrap_stored_value(stored: Any) -> Any:
    if not isinstance(stored, dict):
        return stored
    if set(stored.keys()) == {"v"}:
        return stored.get("v")
    return stored


async def resolve_lead_definition_id_by_key(
    db: AsyncSession,
    *,
    tenant_id: str,
    key: str,
) -> Optional[str]:
    """Return CustomFieldDefinition.id for LEAD scope and key, or None."""
    k = str(key or "").strip()
    if not k:
        return None
    stmt = (
        select(CustomFieldDefinition.id)
        .where(
            CustomFieldDefinition.tenant_id == tenant_id,
            CustomFieldDefinition.scope == CustomFieldScope.LEAD,
            CustomFieldDefinition.key == k,
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return str(row) if row else None


async def automation_context_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    normalized: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Nested dicts for automation rule conditions (dot paths), e.g. custom_fields.my_key, normalized.email.
    """
    norm: Dict[str, Any] = dict(normalized) if isinstance(normalized, dict) else {}
    maps = await batch_lead_custom_field_maps(db, tenant_id=tenant_id, lead_ids=[str(lead_id)])
    cf: Dict[str, Any] = dict(maps.get(str(lead_id), {}))
    return {"normalized": norm, "custom_fields": cf}


async def batch_lead_custom_field_maps(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_ids: List[str],
) -> Dict[str, Dict[str, Any]]:
    if not lead_ids:
        return {}
    stmt = (
        select(CustomFieldValue, CustomFieldDefinition.key)
        .join(CustomFieldDefinition, CustomFieldDefinition.id == CustomFieldValue.definition_id)
        .where(CustomFieldValue.tenant_id == tenant_id)
        .where(CustomFieldValue.entity_type == CustomFieldEntityType.LEAD)
        .where(CustomFieldValue.entity_id.in_(lead_ids))
        .where(CustomFieldDefinition.scope == CustomFieldScope.LEAD)
    )
    rows = (await db.execute(stmt)).all()
    out: Dict[str, Dict[str, Any]] = {}
    for val, key in rows:
        k = str(key or "").strip()
        if not k:
            continue
        lid = str(val.entity_id)
        out.setdefault(lid, {})[k] = _unwrap_stored_value(val.value)
    return out


async def sync_lead_custom_fields_from_normalized(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    normalized: Dict[str, Any],
    updated_by_user_id: Optional[str] = None,
) -> None:
    """Upsert CustomFieldValue rows for active LEAD definitions when normalized carries a value."""
    stmt = (
        select(CustomFieldDefinition)
        .where(CustomFieldDefinition.tenant_id == tenant_id)
        .where(CustomFieldDefinition.scope == CustomFieldScope.LEAD)
        .where(CustomFieldDefinition.is_active.is_(True))
    )
    definitions = (await db.execute(stmt)).scalars().all()
    if not definitions:
        return

    now = datetime.now(timezone.utc)
    for definition in definitions:
        path_key = str(definition.key or "").strip()
        if not path_key:
            continue
        raw = _get_nested_value(normalized, path_key)
        if raw is None:
            continue
        if isinstance(raw, str) and not raw.strip():
            continue

        stored = _coerce_stored_value(raw)
        stmt_v = (
            select(CustomFieldValue)
            .where(CustomFieldValue.tenant_id == tenant_id)
            .where(CustomFieldValue.definition_id == definition.id)
            .where(CustomFieldValue.entity_type == CustomFieldEntityType.LEAD)
            .where(CustomFieldValue.entity_id == lead_id)
        )
        existing = (await db.execute(stmt_v)).scalar_one_or_none()
        if existing:
            existing.value = stored
            existing.updated_at = now
            if updated_by_user_id:
                existing.updated_by_user_id = updated_by_user_id
        else:
            db.add(
                CustomFieldValue(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    definition_id=definition.id,
                    entity_type=CustomFieldEntityType.LEAD,
                    entity_id=lead_id,
                    value=stored,
                    updated_by_user_id=updated_by_user_id,
                )
            )
