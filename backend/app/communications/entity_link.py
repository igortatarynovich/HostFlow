"""G13 runtime: ensure durable CommunicationThread ↔ origin entity links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.result_link import get_thread_result_link
from backend.app.models.communication import CommunicationThread
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink


class ThreadEntityLinkError(Exception):
    code = "thread_entity_link_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ThreadEntityLinkRequiredError(ThreadEntityLinkError):
    code = "thread_entity_link_required"


@dataclass(frozen=True, slots=True)
class ThreadEntityLinkView:
    link_id: str
    thread_id: str
    entity_type: str
    entity_id: str
    is_immutable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "thread_id": self.thread_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "is_immutable": self.is_immutable,
        }


def _trim(value: Any) -> str:
    return str(value or "").strip()


def _normalize_entity_type(entity_type: str) -> str:
    """Canonical G13 entity types (do not collapse sales_inquiry → lead)."""
    key = _trim(entity_type).lower()
    aliases = {
        "inquiry": "lead",
        "client": "client_account",
        "clientaccount": "client_account",
        "order": "service_order",
        "serviceorder": "service_order",
        "company": "company",
        "candidate": "candidate",
        "lead": "lead",
        "sales_inquiry": "sales_inquiry",
        "application": "application",
        "service_order": "service_order",
        "client_account": "client_account",
    }
    return aliases.get(key, key)


def _view(row: CommunicationThreadEntityLink) -> ThreadEntityLinkView:
    return ThreadEntityLinkView(
        link_id=str(row.id),
        thread_id=str(row.thread_id),
        entity_type=str(row.entity_type),
        entity_id=str(row.entity_id),
        is_immutable=bool(row.is_immutable),
    )


async def get_thread_entity_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> list[ThreadEntityLinkView]:
    rows = (
        await db.execute(
            select(CommunicationThreadEntityLink)
            .where(
                CommunicationThreadEntityLink.tenant_id == str(tenant_id),
                CommunicationThreadEntityLink.thread_id == str(thread_id),
            )
            .order_by(CommunicationThreadEntityLink.created_at.asc())
        )
    ).scalars().all()
    return [_view(r) for r in rows]


async def list_entity_links_for_threads(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_ids: Sequence[str],
) -> dict[str, list[ThreadEntityLinkView]]:
    ids = [str(t).strip() for t in thread_ids if str(t or "").strip()]
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(CommunicationThreadEntityLink).where(
                CommunicationThreadEntityLink.tenant_id == str(tenant_id),
                CommunicationThreadEntityLink.thread_id.in_(ids),
            )
        )
    ).scalars().all()
    out: dict[str, list[ThreadEntityLinkView]] = {i: [] for i in ids}
    for row in rows:
        out.setdefault(str(row.thread_id), []).append(_view(row))
    return out


async def ensure_thread_entity_link(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    entity_type: str,
    entity_id: str,
    is_immutable: bool = False,
) -> ThreadEntityLinkView:
    """Idempotent upsert of one G13 link. Re-call returns the same link (no duplicate)."""
    tid = _trim(tenant_id)
    th = _trim(thread_id)
    et = _normalize_entity_type(entity_type)
    eid = _trim(entity_id)
    if not tid or not th or not et or not eid:
        raise ThreadEntityLinkError(
            "tenant_id, thread_id, entity_type, and entity_id are required",
            details={"reason": "missing_entity_ref"},
        )

    existing = await db.scalar(
        select(CommunicationThreadEntityLink).where(
            CommunicationThreadEntityLink.tenant_id == tid,
            CommunicationThreadEntityLink.thread_id == th,
            CommunicationThreadEntityLink.entity_type == et,
            CommunicationThreadEntityLink.entity_id == eid,
        )
    )
    if existing is not None:
        if is_immutable and not bool(existing.is_immutable):
            existing.is_immutable = True
            await db.flush()
        return _view(existing)

    row = CommunicationThreadEntityLink(
        id=str(uuid4()),
        tenant_id=tid,
        thread_id=th,
        entity_type=et,
        entity_id=eid,
        is_immutable=bool(is_immutable),
    )
    db.add(row)
    await db.flush()
    return _view(row)


def collect_known_origins_from_thread(thread: CommunicationThread) -> list[tuple[str, str]]:
    """Derive origin entity refs from legacy columns / meta / (caller adds C1 separately)."""
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(entity_type: str, entity_id: str) -> None:
        et = _normalize_entity_type(entity_type)
        eid = _trim(entity_id)
        if not et or not eid:
            return
        key = (et, eid)
        if key in seen:
            return
        seen.add(key)
        found.append(key)

    if _trim(getattr(thread, "entity_type", None)) and _trim(getattr(thread, "entity_id", None)):
        _add(str(thread.entity_type), str(thread.entity_id))
    if _trim(getattr(thread, "linked_candidate_id", None)):
        _add("candidate", str(thread.linked_candidate_id))
    if _trim(getattr(thread, "linked_company_id", None)):
        _add("company", str(thread.linked_company_id))

    meta = getattr(thread, "thread_meta", None) or {}
    if isinstance(meta, dict):
        uos = meta.get("uos") if isinstance(meta.get("uos"), dict) else {}
        order_id = _trim((uos or {}).get("linked_service_order_id"))
        if order_id:
            _add("service_order", order_id)
        si = _trim(meta.get("sales_inquiry_id"))
        if si:
            _add("sales_inquiry", si)
        lead_id = _trim(meta.get("transport_lead_id"))
        if lead_id:
            _add("lead", lead_id)

    return found


async def ensure_links_for_known_thread_origin(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    extra_origins: Iterable[tuple[str, str]] | None = None,
    is_immutable: bool = False,
) -> list[ThreadEntityLinkView]:
    """Write G13 links for every known origin on the thread (+ optional extras)."""
    origins = collect_known_origins_from_thread(thread)
    if extra_origins:
        for et, eid in extra_origins:
            et_n, eid_n = _normalize_entity_type(et), _trim(eid)
            if et_n and eid_n and (et_n, eid_n) not in origins:
                origins.append((et_n, eid_n))

    # C1 opaque result is origin knowledge, not a G13 substitute — mirror into G13.
    c1 = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=str(thread.id))
    if c1 is not None:
        pair = (_normalize_entity_type(c1.result_type), _trim(c1.result_id))
        if pair[0] and pair[1] and pair not in origins:
            origins.append(pair)

    if not origins:
        return []

    views: list[ThreadEntityLinkView] = []
    for et, eid in origins:
        views.append(
            await ensure_thread_entity_link(
                db,
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                entity_type=et,
                entity_id=eid,
                is_immutable=is_immutable,
            )
        )
    return views


async def require_entity_links_for_outbound(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
) -> list[ThreadEntityLinkView]:
    """C0.1 gate: when origin is known, durable G13 link(s) must exist (create if possible)."""
    origins = collect_known_origins_from_thread(thread)
    c1 = await get_thread_result_link(db, tenant_id=tenant_id, thread_id=str(thread.id))
    if c1 is not None:
        pair = (_normalize_entity_type(c1.result_type), _trim(c1.result_id))
        if pair[0] and pair[1] and pair not in origins:
            origins.append(pair)

    if not origins:
        # Address-only / unbound inbox thread — allowed without G13.
        return []

    views = await ensure_links_for_known_thread_origin(
        db,
        tenant_id=tenant_id,
        thread=thread,
        is_immutable=False,
    )
    if not views:
        raise ThreadEntityLinkRequiredError(
            "Outbound message requires a durable thread entity link when origin is known",
            details={
                "thread_id": str(thread.id),
                "origins": [{"entity_type": et, "entity_id": eid} for et, eid in origins],
                "reason": "missing_thread_entity_link",
            },
        )
    return views


def g13_thread_filter_clause(tenant_id: str, entity_type: str, entity_id: Optional[str] = None):
    """SQLAlchemy OR clause: legacy columns OR G13 links (for list filters)."""
    et = _normalize_entity_type(entity_type)
    eid = _trim(entity_id) if entity_id else ""
    legacy = [CommunicationThread.entity_type == et]
    if eid:
        legacy.append(CommunicationThread.entity_id == eid)
    legacy_clause = and_all(legacy)

    link_exists = (
        select(CommunicationThreadEntityLink.id)
        .where(
            CommunicationThreadEntityLink.tenant_id == str(tenant_id),
            CommunicationThreadEntityLink.thread_id == CommunicationThread.id,
            CommunicationThreadEntityLink.entity_type == et,
        )
        .correlate(CommunicationThread)
    )
    if eid:
        link_exists = link_exists.where(CommunicationThreadEntityLink.entity_id == eid)
    return or_(legacy_clause, link_exists.exists())


def and_all(parts: list):
    from sqlalchemy import and_

    if len(parts) == 1:
        return parts[0]
    return and_(*parts)
