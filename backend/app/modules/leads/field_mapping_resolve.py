"""Resolve effective Meta field_mapping for ingest (per-form with tenant fallback)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.leads import crud, normalizer


def _coerce_rules_list(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, dict):
        rules = raw.get("rules")
        return [item for item in rules if isinstance(item, dict)] if isinstance(rules, list) else []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _tenant_fallback_rules(settings_row: Any) -> List[Dict[str, Any]]:
    if settings_row is None:
        return []
    return _coerce_rules_list(getattr(settings_row, "field_mapping", None))


async def resolve_field_mapping_for_ingest(
    db: AsyncSession,
    *,
    tenant_id: str,
    payload: Dict[str, Any],
    source: str = "meta",
    settings_row: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Per-form mapping when form_id is present and a row exists; otherwise tenant-level field_mapping.
    Lookup order: (tenant, source, form_id, page_id) then (tenant, source, form_id, page_id='').
    """
    ctx = normalizer.extract_meta_lead_form_context(payload, source=source)
    form_id = ctx.get("form_id")
    page_id = ctx.get("page_id") or ""
    src = ctx.get("source") or "meta"

    if form_id:
        row = await crud.get_meta_form_mapping(
            db,
            tenant_id=tenant_id,
            source=src,
            form_id=form_id,
            page_id=page_id,
        )
        if row is None and page_id:
            row = await crud.get_meta_form_mapping(
                db,
                tenant_id=tenant_id,
                source=src,
                form_id=form_id,
                page_id="",
            )
        if row is not None:
            rules = _coerce_rules_list(row.mapping_rules)
            if rules:
                return rules

    if settings_row is None:
        settings_row = await crud.get_meta_settings(db, tenant_id=tenant_id)
    return _tenant_fallback_rules(settings_row)
