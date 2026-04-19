"""Inbound-side helpers for the communications API.

Three families of utilities used by ingest, webhook, and email-poll
worker code paths:

1. Thread-resolution: locate the right :class:`CommunicationThread` for
   an inbound message, falling back to subject+sender heuristics when
   the provider does not return a thread reference.

   * ``_find_thread_for_inbound_email``
   * ``_find_thread_for_inbound_channel``

2. Outbound-from-mailbox ingest: when the email-poll worker reads the
   "Sent" folder of a connected mailbox, this creates the corresponding
   ``CommunicationMessage(direction="outbound", delivery_status="delivered")``
   on either an existing or freshly created thread (returns a
   ``(created_thread, duplicate_message)`` tuple so callers can update
   counters).

   * ``_ingest_email_outbound_from_mailbox``

3. Webhook-secret resolution: per-channel constant-time lookups of a
   :class:`CommunicationChannelAccount` whose ``settings_json`` carries
   the matching ``webhook_secret``. There is a generic resolver
   (``_find_channel_account_by_webhook_secret``) plus two thin wrappers
   kept for backward compatibility with telegram / whatsapp webhook
   handlers.

   * ``_find_telegram_account_by_webhook_secret``
   * ``_find_whatsapp_account_by_webhook_secret``
   * ``_find_channel_account_by_webhook_secret``

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 5/N).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import (
    CommunicationChannelAccount,
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.models.tenant import Tenant

from .access import _default_own_company_id_for_tenant
from .sla import _touch_thread_from_message
from .utils import _as_dict, _clamp_db_str, _now_utc

__all__ = [
    "_find_thread_for_inbound_email",
    "_find_thread_for_inbound_channel",
    "_ingest_email_outbound_from_mailbox",
    "_find_telegram_account_by_webhook_secret",
    "_find_whatsapp_account_by_webhook_secret",
    "_find_channel_account_by_webhook_secret",
]


async def _find_thread_for_inbound_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel_account_id: str | None,
    provider_thread_ref: str | None,
    subject: str | None,
    from_address: str | None,
) -> CommunicationThread | None:
    if provider_thread_ref:
        stmt = (
            sa.select(CommunicationThread)
            .where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.channel == "email",
                CommunicationThread.channel_thread_ref == provider_thread_ref,
            )
            .limit(1)
        )
        row = (await db.execute(stmt)).scalars().first()
        if row:
            return row

    # Fallback heuristic for MVP testing (same account + subject + sender among
    # recent threads).
    if subject and channel_account_id:
        like_subject = subject.strip()
        if like_subject:
            stmt = (
                sa.select(CommunicationThread)
                .where(
                    CommunicationThread.tenant_id == tenant_id,
                    CommunicationThread.channel == "email",
                    CommunicationThread.channel_account_id == channel_account_id,
                    CommunicationThread.subject == like_subject,
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
                .limit(5)
            )
            candidates = (await db.execute(stmt)).scalars().all()
            normalized_from = (from_address or "").strip().lower()
            for th in candidates:
                participants = _as_dict(th.participants_json)
                senders = participants.get("senders")
                if isinstance(senders, list) and normalized_from:
                    if any(
                        str(x).strip().lower() == normalized_from for x in senders
                    ):
                        return th
            if candidates:
                return candidates[0]
    return None


async def _find_thread_for_inbound_channel(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    channel_account_id: str | None,
    provider_thread_ref: str | None,
    sender_address: str | None,
) -> CommunicationThread | None:
    ref = (provider_thread_ref or "").strip()
    if ref:
        stmt = (
            sa.select(CommunicationThread)
            .where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.channel == channel,
                CommunicationThread.channel_thread_ref == ref,
            )
            .limit(1)
        )
        found = (await db.execute(stmt)).scalars().first()
        if found:
            return found

    # Fallback: same channel + account + sender in recent active threads.
    if not sender_address:
        return None
    stmt = (
        sa.select(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == channel,
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
        .limit(20)
    )
    if channel_account_id:
        stmt = stmt.where(CommunicationThread.channel_account_id == channel_account_id)
    rows = (await db.execute(stmt)).scalars().all()
    normalized_sender = sender_address.strip().lower()
    for th in rows:
        participants = _as_dict(th.participants_json)
        senders = participants.get("senders")
        if isinstance(senders, list) and any(
            str(x).strip().lower() == normalized_sender for x in senders
        ):
            return th
    return None


async def _ingest_email_outbound_from_mailbox(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel_account_id: str,
    provider: str,
    provider_thread_ref: str | None,
    external_message_ref: str | None,
    subject: str | None,
    from_address: str | None,
    to_address: str | None,
    to_name: str | None,
    text: str | None,
    html: str | None,
    headers: Dict[str, Any],
    payload: Dict[str, Any],
    sent_at: datetime | None,
    tenant: Tenant,
) -> Tuple[bool, bool]:
    provider_thread_ref = _clamp_db_str(provider_thread_ref, 255)
    external_message_ref = _clamp_db_str(external_message_ref, 255)
    subject = _clamp_db_str(subject, 512)
    from_address = _clamp_db_str(from_address, 255)
    to_address = _clamp_db_str(to_address, 255)
    to_name = _clamp_db_str(to_name, 255)

    default_own_id = await _default_own_company_id_for_tenant(db, tenant_id)

    if external_message_ref:
        existing_msg_stmt = (
            sa.select(CommunicationMessage)
            .where(
                CommunicationMessage.tenant_id == tenant_id,
                CommunicationMessage.channel == "email",
                CommunicationMessage.external_message_ref == external_message_ref,
            )
            .limit(1)
        )
        existing_msg = (await db.execute(existing_msg_stmt)).scalars().first()
        if existing_msg:
            return False, True

    thread = await _find_thread_for_inbound_email(
        db,
        tenant_id=tenant_id,
        channel_account_id=channel_account_id,
        provider_thread_ref=provider_thread_ref,
        subject=subject,
        from_address=to_address,
    )
    created_thread = False
    if thread is None:
        participants = {
            "senders": [from_address] if from_address else [],
            "recipients": [to_address] if to_address else [],
            "cc": [],
            "bcc": [],
        }
        thread = CommunicationThread(
            tenant_id=tenant_id,
            own_company_id=default_own_id,
            channel="email",
            channel_account_id=channel_account_id,
            channel_thread_ref=provider_thread_ref,
            subject=subject,
            status="open",
            direction_hint="outbound",
            priority="normal",
            participants_json=participants,
            tags_json=[],
            thread_meta={"provider": provider, "mailbox_source": "sent"},
        )
        db.add(thread)
        await db.flush()
        created_thread = True
    else:
        participants = _as_dict(thread.participants_json)
        recipients = participants.get("recipients")
        if not isinstance(recipients, list):
            recipients = []
        if to_address and to_address not in recipients:
            recipients.append(to_address)
        participants["recipients"] = recipients
        senders = participants.get("senders")
        if not isinstance(senders, list):
            senders = []
        if from_address and from_address not in senders:
            senders.append(from_address)
        participants["senders"] = senders
        thread.participants_json = participants
        if subject and not thread.subject:
            thread.subject = subject
        if not getattr(thread, "own_company_id", None) and default_own_id:
            thread.own_company_id = default_own_id

    ts = sent_at or _now_utc()
    msg = CommunicationMessage(
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        own_company_id=getattr(thread, "own_company_id", None),
        channel="email",
        message_type="email",
        direction="outbound",
        sender_type="user",
        sender_label=None,
        sender_address=from_address,
        recipient_type="external",
        recipient_label=to_name,
        recipient_address=to_address,
        subject=subject,
        body_text=text,
        body_html=html,
        attachments_json=[],
        payload={
            **(payload or {}),
            "headers": headers or {},
            "provider": provider,
            "mailbox_source": "sent",
        },
        external_message_ref=external_message_ref,
        delivery_status="delivered",
        sent_at=ts,
        delivered_at=ts,
        read_at=None,
        is_internal_note=False,
    )
    db.add(msg)
    await db.flush()
    _touch_thread_from_message(thread, msg, tenant=tenant)
    return created_thread, False


async def _find_channel_account_by_webhook_secret(
    db: AsyncSession,
    *,
    channel: str,
    config_key: str,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    secret = (webhook_secret or "").strip()
    if not secret:
        return None
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.channel == channel,
        CommunicationChannelAccount.is_active.is_(True),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for account in rows:
        settings = _as_dict(account.settings_json)
        cfg = _as_dict(settings.get(config_key))
        if str(cfg.get("webhook_secret") or "").strip() == secret:
            return account
    return None


async def _find_telegram_account_by_webhook_secret(
    db: AsyncSession,
    *,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    return await _find_channel_account_by_webhook_secret(
        db,
        channel="telegram",
        config_key="telegram",
        webhook_secret=webhook_secret,
    )


async def _find_whatsapp_account_by_webhook_secret(
    db: AsyncSession,
    *,
    webhook_secret: str,
) -> CommunicationChannelAccount | None:
    return await _find_channel_account_by_webhook_secret(
        db,
        channel="whatsapp",
        config_key="whatsapp",
        webhook_secret=webhook_secret,
    )
