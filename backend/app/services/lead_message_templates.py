"""Tenant-scoped hub for lead email templates (RODO + operational lead emails)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant

_SETTINGS_KEY = "lead_message_templates_v1"


@dataclass(frozen=True)
class LeadMessageTemplate:
    id: str
    name: str
    subject: str
    body: str
    is_active: bool
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_text(raw: Any, *, max_len: int) -> str:
    return str(raw or "").strip()[:max_len]


def _as_items(settings: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(settings, dict):
        return []
    raw = settings.get(_SETTINGS_KEY)
    if not isinstance(raw, dict):
        return []
    items = raw.get("items")
    return items if isinstance(items, list) else []


def _to_template(raw: dict[str, Any]) -> Optional[LeadMessageTemplate]:
    tid = _sanitize_text(raw.get("id"), max_len=64)
    name = _sanitize_text(raw.get("name"), max_len=180)
    subject = _sanitize_text(raw.get("subject"), max_len=500)
    body = str(raw.get("body") or "")[:20000]
    if not tid or not name:
        return None
    created_at = _sanitize_text(raw.get("created_at"), max_len=64) or _now_iso()
    updated_at = _sanitize_text(raw.get("updated_at"), max_len=64) or created_at
    return LeadMessageTemplate(
        id=tid,
        name=name,
        subject=subject,
        body=body,
        is_active=bool(raw.get("is_active", True)),
        created_at=created_at,
        updated_at=updated_at,
    )


def _serialize(template: LeadMessageTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "subject": template.subject,
        "body": template.body,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


async def list_lead_message_templates(db: AsyncSession, tenant_id: str) -> list[LeadMessageTemplate]:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return []
    st = tenant.settings if isinstance(tenant.settings, dict) else {}
    out: list[LeadMessageTemplate] = []
    for raw in _as_items(st):
        if not isinstance(raw, dict):
            continue
        item = _to_template(raw)
        if item is not None:
            out.append(item)
    out.sort(key=lambda x: (x.name.lower(), x.id))
    return out


async def get_lead_message_template_by_id(
    db: AsyncSession, tenant_id: str, template_id: Optional[str]
) -> Optional[LeadMessageTemplate]:
    tid = _sanitize_text(template_id, max_len=64)
    if not tid:
        return None
    for item in await list_lead_message_templates(db, tenant_id):
        if item.id == tid and item.is_active:
            return item
    return None


async def upsert_lead_message_template(
    db: AsyncSession,
    tenant_id: str,
    *,
    template_id: Optional[str],
    name: str,
    subject: str,
    body: str,
    is_active: bool = True,
) -> LeadMessageTemplate:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        raise ValueError("tenant_not_found")
    st = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    items = [dict(x) for x in _as_items(st) if isinstance(x, dict)]
    now = _now_iso()

    normalized_id = _sanitize_text(template_id, max_len=64) or f"lead_tpl_{uuid4().hex[:12]}"
    normalized_name = _sanitize_text(name, max_len=180)
    if not normalized_name:
        raise ValueError("template_name_required")
    normalized_subject = _sanitize_text(subject, max_len=500)
    normalized_body = str(body or "")[:20000]

    existing_idx = next((i for i, raw in enumerate(items) if _sanitize_text(raw.get("id"), max_len=64) == normalized_id), None)
    if existing_idx is None:
        rec = LeadMessageTemplate(
            id=normalized_id,
            name=normalized_name,
            subject=normalized_subject,
            body=normalized_body,
            is_active=bool(is_active),
            created_at=now,
            updated_at=now,
        )
        items.append(_serialize(rec))
    else:
        prev = items[existing_idx]
        created_at = _sanitize_text(prev.get("created_at"), max_len=64) or now
        rec = LeadMessageTemplate(
            id=normalized_id,
            name=normalized_name,
            subject=normalized_subject,
            body=normalized_body,
            is_active=bool(is_active),
            created_at=created_at,
            updated_at=now,
        )
        items[existing_idx] = _serialize(rec)

    st[_SETTINGS_KEY] = {"items": items}
    tenant.settings = st
    await db.flush()
    return rec


async def delete_lead_message_template(db: AsyncSession, tenant_id: str, template_id: str) -> bool:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if tenant is None:
        return False
    st = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    items = [dict(x) for x in _as_items(st) if isinstance(x, dict)]
    tid = _sanitize_text(template_id, max_len=64)
    if not tid:
        return False
    kept = [row for row in items if _sanitize_text(row.get("id"), max_len=64) != tid]
    if len(kept) == len(items):
        return False
    st[_SETTINGS_KEY] = {"items": kept}
    tenant.settings = st
    await db.flush()
    return True

