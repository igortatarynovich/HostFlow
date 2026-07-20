"""C0.2 — inbound thread/entity resolution (deny silent loss).

Preference order (normative):
  reply_headers → provider_thread → known_participant → entity_contact → manual → unresolved
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.command import CommunicationOrigin
from backend.app.communications.entity_link import (
    _normalize_entity_type,
    get_thread_entity_links,
)
from backend.app.communications.inbound_dto import InboundResolution, NormalizedInboundMessage
from backend.app.communications.inbound_normalize import (
    extract_reply_message_ids,
    normalize_message_id,
)
from backend.app.communications.send_communication import find_thread_id_for_origin
# Destination entities via package facade (C1/C2: no direct destination-module imports).
from backend.app.models import (
    Candidate,
    Lead,
    RecruitmentApplication,
    SalesInquiry,
)
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink


def _trim(value: Any) -> str:
    return str(value or "").strip()


def _norm_addr(value: Any) -> str:
    return _trim(value).lower()


async def _message_by_external_ref(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    external_refs: list[str],
) -> CommunicationMessage | None:
    if not external_refs:
        return None
    # Match normalized + raw variants (legacy rows may omit brackets).
    variants: list[str] = []
    seen: set[str] = set()
    for ref in external_refs:
        for candidate in (ref, normalize_message_id(ref) or "", _trim(ref).strip("<>")):
            c = _trim(candidate)
            if c and c not in seen:
                seen.add(c)
                variants.append(c)
    if not variants:
        return None
    stmt = (
        sa.select(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == channel,
            CommunicationMessage.external_message_ref.in_(variants),
        )
        .order_by(sa.desc(CommunicationMessage.created_at))
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _primary_entity_for_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
) -> tuple[str | None, str | None]:
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=thread_id
    )
    if not links:
        return None, None
    # Prefer work-context entities over bare person/account.
    priority = (
        "application",
        "sales_inquiry",
        "lead",
        "service_order",
        "candidate",
        "client_account",
        "company",
    )
    by_type = {lnk.entity_type: lnk for lnk in links}
    for et in priority:
        if et in by_type:
            return by_type[et].entity_type, by_type[et].entity_id
    first = links[0]
    return first.entity_type, first.entity_id


async def _correlation_from_message(msg: CommunicationMessage) -> str | None:
    payload = dict(msg.payload or {})
    corr = _trim(payload.get("correlation_id"))
    if corr:
        return corr
    snap = payload.get("snapshot")
    if isinstance(snap, dict):
        return _trim(snap.get("correlation_id")) or None
    return None


async def _resolve_reply_headers(
    db: AsyncSession,
    inbound: NormalizedInboundMessage,
) -> InboundResolution | None:
    reply_ids = extract_reply_message_ids(inbound.headers)
    if not reply_ids:
        return None
    matched = await _message_by_external_ref(
        db,
        tenant_id=inbound.tenant_id,
        channel=inbound.channel,
        external_refs=reply_ids,
    )
    if matched is None:
        return None
    entity_type, entity_id = await _primary_entity_for_thread(
        db, tenant_id=inbound.tenant_id, thread_id=str(matched.thread_id)
    )
    return InboundResolution(
        reason="reply_headers",
        thread_id=str(matched.thread_id),
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=await _correlation_from_message(matched),
        matched_outbound_message_id=str(matched.id),
        details={
            "matched_external_message_ref": matched.external_message_ref,
            "reply_ids": reply_ids,
        },
    )


async def _resolve_provider_thread(
    db: AsyncSession,
    inbound: NormalizedInboundMessage,
) -> InboundResolution | None:
    ref = _trim(inbound.provider_thread_ref)
    if not ref:
        return None
    stmt = (
        sa.select(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == inbound.tenant_id,
            CommunicationThread.channel == inbound.channel,
            CommunicationThread.channel_thread_ref == ref,
        )
        .limit(1)
    )
    thread = (await db.execute(stmt)).scalars().first()
    if thread is None:
        return None
    entity_type, entity_id = await _primary_entity_for_thread(
        db, tenant_id=inbound.tenant_id, thread_id=str(thread.id)
    )
    return InboundResolution(
        reason="provider_thread",
        thread_id=str(thread.id),
        entity_type=entity_type,
        entity_id=entity_id,
        details={"provider_thread_ref": ref},
    )


async def _resolve_known_participant(
    db: AsyncSession,
    inbound: NormalizedInboundMessage,
) -> InboundResolution | None:
    """Exact sender among participants on a thread that already has G13 links."""
    sender = _norm_addr(inbound.sender_address)
    if not sender:
        return None
    # Threads with G13 for this tenant+channel, recent first.
    link_thread_ids = (
        await db.execute(
            sa.select(CommunicationThreadEntityLink.thread_id)
            .where(CommunicationThreadEntityLink.tenant_id == inbound.tenant_id)
            .distinct()
        )
    ).scalars().all()
    if not link_thread_ids:
        return None
    stmt = (
        sa.select(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == inbound.tenant_id,
            CommunicationThread.channel == inbound.channel,
            CommunicationThread.id.in_([str(x) for x in link_thread_ids]),
            CommunicationThread.is_archived.is_(False),
        )
        .order_by(
            sa.desc(
                sa.func.coalesce(
                    CommunicationThread.last_message_at,
                    CommunicationThread.updated_at,
                )
            )
        )
        .limit(40)
    )
    if inbound.channel_account_id:
        stmt = stmt.where(
            sa.or_(
                CommunicationThread.channel_account_id == inbound.channel_account_id,
                CommunicationThread.channel_account_id.is_(None),
            )
        )
    threads = (await db.execute(stmt)).scalars().all()
    for th in threads:
        participants = dict(th.participants_json or {})
        senders = participants.get("senders") if isinstance(participants, dict) else None
        recipients = (
            participants.get("recipients") if isinstance(participants, dict) else None
        )
        pool: list[str] = []
        if isinstance(senders, list):
            pool.extend(str(x) for x in senders)
        if isinstance(recipients, list):
            pool.extend(str(x) for x in recipients)
        if any(_norm_addr(x) == sender for x in pool):
            entity_type, entity_id = await _primary_entity_for_thread(
                db, tenant_id=inbound.tenant_id, thread_id=str(th.id)
            )
            return InboundResolution(
                reason="known_participant",
                thread_id=str(th.id),
                entity_type=entity_type,
                entity_id=entity_id,
                details={"sender_address": inbound.sender_address},
            )
    return None


async def _active_application_for_candidate(
    db: AsyncSession, *, tenant_id: str, candidate_id: str
) -> str | None:
    active_statuses = ("applied", "active", "in_progress", "screening", "interview")
    row = (
        await db.execute(
            sa.select(RecruitmentApplication.id)
            .where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.candidate_id == candidate_id,
                RecruitmentApplication.status.in_(active_statuses),
            )
            .order_by(sa.desc(RecruitmentApplication.applied_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    return str(row) if row else None


async def _sales_inquiry_for_lead(
    db: AsyncSession, *, tenant_id: str, lead_id: str
) -> str | None:
    row = (
        await db.execute(
            sa.select(SalesInquiry.id)
            .where(
                SalesInquiry.tenant_id == tenant_id,
                SalesInquiry.lead_id == lead_id,
            )
            .order_by(sa.desc(SalesInquiry.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    return str(row) if row else None


async def _lead_ids_by_email(
    db: AsyncSession, *, tenant_id: str, email: str
) -> list[str]:
    """Match lead.normalized.email (JSON) — exact, case-insensitive."""
    rows = (
        await db.execute(
            sa.select(Lead.id, Lead.normalized)
            .where(Lead.tenant_id == tenant_id)
            .order_by(sa.desc(Lead.created_at))
            .limit(200)
        )
    ).all()
    matched: list[str] = []
    for lead_id, normalized in rows:
        if not isinstance(normalized, dict):
            continue
        lead_email = _norm_addr(normalized.get("email"))
        if lead_email and lead_email == email:
            matched.append(str(lead_id))
    return matched


async def _resolve_entity_contact(
    db: AsyncSession,
    inbound: NormalizedInboundMessage,
) -> InboundResolution | None:
    """Exact contact → prefer active application / inquiry → client/candidate.

    Ambiguous matches (multiple candidates/leads, or candidate+lead) never pick
    arbitrarily — return ``unresolved`` with ``reason_code=ambiguous_entity_contact``.
    """
    sender = _norm_addr(inbound.sender_address)
    if not sender:
        return None

    matches: list[dict[str, Any]] = []

    candidates = (
        await db.execute(
            sa.select(Candidate).where(
                Candidate.tenant_id == inbound.tenant_id,
                Candidate.email.isnot(None),
                sa.func.lower(Candidate.email) == sender,
            )
        )
    ).scalars().all()
    for candidate in candidates:
        app_id = await _active_application_for_candidate(
            db, tenant_id=inbound.tenant_id, candidate_id=str(candidate.id)
        )
        if app_id:
            matches.append(
                {
                    "entity_type": "application",
                    "entity_id": app_id,
                    "via": "active_application",
                    "candidate_id": str(candidate.id),
                }
            )
        else:
            matches.append(
                {
                    "entity_type": "candidate",
                    "entity_id": str(candidate.id),
                    "via": "candidate_email",
                }
            )

    lead_ids = await _lead_ids_by_email(
        db, tenant_id=inbound.tenant_id, email=sender
    )
    for lead_id in lead_ids:
        si = await _sales_inquiry_for_lead(
            db, tenant_id=inbound.tenant_id, lead_id=lead_id
        )
        if si:
            matches.append(
                {
                    "entity_type": "sales_inquiry",
                    "entity_id": si,
                    "via": "sales_inquiry",
                    "lead_id": lead_id,
                }
            )
        else:
            matches.append(
                {
                    "entity_type": "lead",
                    "entity_id": lead_id,
                    "via": "lead_email",
                }
            )

    if not matches:
        return None

    if len(matches) > 1:
        return InboundResolution(
            reason="unresolved",
            details={
                "reason_code": "ambiguous_entity_contact",
                "sender_address": inbound.sender_address,
                "matches": matches,
            },
        )

    chosen = matches[0]
    entity_type = str(chosen["entity_type"])
    entity_id = str(chosen["entity_id"])
    thread_id = await find_thread_id_for_origin(
        db,
        tenant_id=inbound.tenant_id,
        channel=inbound.channel,
        origin=CommunicationOrigin(entity_type=entity_type, entity_id=entity_id),
    )
    details = {"sender_address": inbound.sender_address, **chosen}
    return InboundResolution(
        reason="entity_contact",
        thread_id=thread_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


def _resolve_manual(inbound: NormalizedInboundMessage) -> InboundResolution | None:
    et = _normalize_entity_type(inbound.hinted_entity_type or "")
    eid = _trim(inbound.hinted_entity_id)
    if et and eid:
        return InboundResolution(
            reason="manual",
            thread_id=None,
            entity_type=et,
            entity_id=eid,
            details={"source": "request_hint"},
        )
    if inbound.linked_candidate_id:
        return InboundResolution(
            reason="manual",
            thread_id=None,
            entity_type="candidate",
            entity_id=_trim(inbound.linked_candidate_id),
            details={"source": "linked_candidate_id"},
        )
    if inbound.linked_company_id:
        return InboundResolution(
            reason="manual",
            thread_id=None,
            entity_type="company",
            entity_id=_trim(inbound.linked_company_id),
            details={"source": "linked_company_id"},
        )
    return None


async def resolve_inbound(
    db: AsyncSession,
    inbound: NormalizedInboundMessage,
) -> InboundResolution:
    """Run the normative resolution chain. Always returns a decision."""
    force = _trim(inbound.force_unresolved_reason_code)
    if force:
        return InboundResolution(
            reason="unresolved",
            details={
                "reason_code": force,
                "sender_address": inbound.sender_address,
            },
        )

    for step in (
        _resolve_reply_headers,
        _resolve_provider_thread,
        _resolve_known_participant,
        _resolve_entity_contact,
    ):
        result = await step(db, inbound)
        if result is not None:
            return result

    manual = _resolve_manual(inbound)
    if manual is not None:
        # Try attach to existing origin thread when possible.
        if manual.entity_type and manual.entity_id:
            thread_id = await find_thread_id_for_origin(
                db,
                tenant_id=inbound.tenant_id,
                channel=inbound.channel,
                origin=CommunicationOrigin(
                    entity_type=manual.entity_type, entity_id=manual.entity_id
                ),
            )
            if thread_id:
                return InboundResolution(
                    reason="manual",
                    thread_id=thread_id,
                    entity_type=manual.entity_type,
                    entity_id=manual.entity_id,
                    details=manual.details,
                )
        return manual

    return InboundResolution(
        reason="unresolved",
        details={
            "sender_address": inbound.sender_address,
            "provider_thread_ref": inbound.provider_thread_ref,
            "has_reply_headers": bool(extract_reply_message_ids(inbound.headers)),
        },
    )
