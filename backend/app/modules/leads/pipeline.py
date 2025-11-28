from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.modules.leads import crud
from backend.app.modules.leads.payload import (
    MetaField,
    MetaWebhookIn,
    _model_validate,
    extract_field_data_from_payload,
    merge_meta_fields,
    to_meta_fields,
)

logger = logging.getLogger("backend.app.modules.leads.pipeline")


class GraphAPIError(Exception):
    def __init__(self, code: Optional[str], message: str):
        self.code = str(code or "UNKNOWN")
        super().__init__(message)


async def _fetch_field_data_from_graph(lead_id: str, access_token: str) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/v24.0/{lead_id}"
    params = {
        "fields": "field_data,ad_id,form_id",
        "access_token": access_token,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover - defensive
        raise GraphAPIError("UNKNOWN", f"Invalid Graph response: {exc}") from exc
    if response.status_code == 200:
        assert isinstance(payload, dict)
        return payload
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else "Graph API error"
    raise GraphAPIError(code, message or "Graph API error")


async def enrich_entries_with_graph(
    db: AsyncSession,
    tenant_id: str,
    webhook_event: MetaWebhookIn,
    *,
    existing_leads: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Request field_data/ad_id/form_id from Graph for skeleton events when feature flag enabled.
    """
    if not settings.pull_field_data_from_graph:
        return
    from backend.app.modules.leads import admin_service  # local import to avoid circular

    for entry in webhook_event.entry:
        for change in entry.changes:
            if change.field != "leadgen":
                continue
            value = change.value
            if not value.page_id and entry.id:
                value.page_id = entry.id
            if value.field_data:
                continue
            page_id = value.page_id or entry.id
            if not page_id:
                value.graph_error = "GRAPH_NO_PAGE_ID"
                continue
            token = await admin_service.get_page_access_token(db, tenant_id, page_id)
            if not token:
                value.graph_error = "GRAPH_NO_TOKEN"
                continue
            last_error: Optional[GraphAPIError] = None
            graph_payload: Optional[Dict[str, Any]] = None
            for attempt in range(3):
                try:
                    graph_payload = await _fetch_field_data_from_graph(value.leadgen_id, token)
                    break
                except GraphAPIError as exc:
                    last_error = exc
                    if exc.code in {"190", "104", "100"} and attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    value.graph_error = f"GRAPH_{exc.code}"
                    break
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Meta Graph fetch failed for lead %s: %s", value.leadgen_id, exc)
                    value.graph_error = "GRAPH_UNKNOWN"
                    break
            if graph_payload is None:
                if not value.graph_error:
                    code = last_error.code if last_error else "UNKNOWN"
                    value.graph_error = f"GRAPH_{code}"
                message = last_error.args[0] if last_error else ""
                logger.info(
                    "[meta] graph: fetch fail lead=%s code=%s msg=%s",
                    value.leadgen_id,
                    value.graph_error,
                    message,
                )
                continue
            field_data = []
            if isinstance(graph_payload, dict):
                field_data = graph_payload.get("field_data") or []
                if graph_payload.get("ad_id") and not value.ad_id:
                    value.ad_id = str(graph_payload["ad_id"])
                if graph_payload.get("form_id") and not value.form_id:
                    value.form_id = str(graph_payload["form_id"])
            if field_data:
                value.field_data = to_meta_fields(field_data)  # type: ignore[arg-type]
                value.graph_error = None
                logger.info("[meta] graph: fetch ok lead=%s", value.leadgen_id)
            else:
                value.graph_error = value.graph_error or "GRAPH_EMPTY_FIELD_DATA"
                logger.info(
                    "[meta] graph: fetch fail lead=%s code=%s msg=%s",
                    value.leadgen_id,
                    value.graph_error,
                    "empty field_data",
                )


async def merge_existing_field_data(
    db: AsyncSession,
    tenant_id: str,
    webhook_event: MetaWebhookIn,
    *,
    existing_leads: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Ensure new payloads keep field_data already stored on existing leads and reuse ad/form hints.
    """
    for entry in webhook_event.entry:
        for change in entry.changes:
            if change.field != "leadgen":
                continue
            value = change.value
            lead_id = value.leadgen_id
            existing = None
            if existing_leads is not None:
                existing = existing_leads.get(lead_id)
            if existing is None:
                existing = await crud.get_lead_by_external_id(
                    db,
                    tenant_id=tenant_id,
                    source="meta",
                    external_id=lead_id,
                )
            if not existing:
                continue
            existing_fields: List[MetaField] = []
            if existing.payload:
                existing_fields = extract_field_data_from_payload(existing.payload, lead_id)
            merged_fields = merge_meta_fields(existing_fields, list(value.field_data))
            if merged_fields:
                value.field_data = merged_fields
            if not value.ad_id and existing.normalized:
                ad_id = existing.normalized.get("ad_id") if isinstance(existing.normalized, dict) else None
                if ad_id:
                    value.ad_id = str(ad_id)
            if not value.form_id and existing.normalized:
                form_id = existing.normalized.get("form_id") if isinstance(existing.normalized, dict) else None
                if form_id:
                    value.form_id = str(form_id)


async def hydrate_webhook_payload(
    db: AsyncSession,
    tenant_id: str,
    raw_payload: Dict[str, Any],
    *,
    existing_leads: Optional[Dict[str, Any]] = None,
    refresh_graph: bool = True,
) -> Dict[str, Any]:
    """
    Validate webhook payload, optionally enrich via Graph, merge with existing data and return dict.
    """
    try:
        webhook_event = _model_validate(MetaWebhookIn, raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid webhook payload: {exc}") from exc

    if refresh_graph:
        await enrich_entries_with_graph(
            db,
            tenant_id,
            webhook_event,
            existing_leads=existing_leads,
        )
    await merge_existing_field_data(
        db,
        tenant_id,
        webhook_event,
        existing_leads=existing_leads,
    )

    if hasattr(webhook_event, "model_dump"):
        return webhook_event.model_dump()
    return webhook_event.dict()


def collect_leadgen_ids(payload: Dict[str, Any]) -> Iterable[str]:
    """
    Helper to gather all leadgen_ids present in raw payload.
    """
    try:
        webhook_event = _model_validate(MetaWebhookIn, payload)
    except ValidationError:
        return []
    ids: set[str] = set()
    for entry in webhook_event.entry:
        for change in entry.changes:
            if change.field == "leadgen":
                ids.add(change.value.leadgen_id)
    return ids
