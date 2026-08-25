"""Sub-module of telegram_intake (Phase 1 god-module split, step 8/N)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.communication import (
    CommunicationThread,
)
from backend.app.services.tenant_email import send_email_for_tenant
from backend.app.services.tenant_quota import ensure_active_records_quota

from ..candidate_lookup import (
    _candidate_name,
)
from ..utils import (
    _as_dict,
    _coerce_datetime,
    _digits_only,
    _now_utc,
)
from .ui_text import (
    _candidate_verification_email_body,
    _telegram_name_parts,
    _telegram_otp_hash,
)
from .docs_bridge import (
    _ensure_candidate_intake_token,
)


# ---------------------------------------------------------------------------
# 3. Candidate ↔ chat linking + bootstrap.
# ---------------------------------------------------------------------------


async def _create_candidate_from_telegram_intake(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    username: str | None,
    sender_label: str | None,
    sender_address: str | None,
    contact_phone: str | None,
) -> Candidate:
    await ensure_active_records_quota(db, tenant_id)
    first_name, last_name = _telegram_name_parts(sender_label, username)
    phone_digits = _digits_only(contact_phone)
    candidate = Candidate(
        id=str(uuid4()),
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name or "Telegram",
        phone=phone_digits or None,
        stage="docs_wait",
        status="docs_wait",
        intake_status="draft",
        source="telegram_bot",
    )
    state = _as_dict(getattr(candidate, "intake_state", None))
    contacts = _as_dict(state.get("contacts"))
    contacts["preferred_messenger"] = "telegram"
    contacts["telegram_chat_id"] = chat_id
    if sender_address:
        contacts["telegram_user_id"] = sender_address
    if username:
        contacts["telegram_username"] = username
    if phone_digits:
        contacts["phone"] = phone_digits
    state["contacts"] = contacts
    candidate.intake_state = state
    _ensure_candidate_intake_token(candidate)
    db.add(candidate)
    await db.flush()
    from backend.app.services.candidate_creation_service import finalize_new_candidate_record

    await finalize_new_candidate_record(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
        source="telegram_intake",
    )
    await _link_candidate_to_telegram_chat(
        db,
        tenant_id=tenant_id,
        chat_id=chat_id,
        candidate=candidate,
        username=username,
    )
    await db.commit()
    return candidate


async def _link_candidate_to_telegram_chat(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    candidate: Candidate,
    username: str | None,
) -> None:
    now_iso = _now_utc().isoformat()
    state = _as_dict(candidate.intake_state)
    notifications = _as_dict(state.get("notifications"))
    telegram_state = _as_dict(notifications.get("telegram"))
    telegram_state["chat_id"] = chat_id
    telegram_state["subscribed"] = True
    telegram_state["linked_at"] = telegram_state.get("linked_at") or now_iso
    telegram_state["updated_at"] = now_iso
    telegram_state.pop("link_verification", None)
    if username:
        telegram_state["username"] = username
    notifications["telegram"] = telegram_state
    state["notifications"] = notifications
    candidate.intake_state = state

    thread_rows = (
        await db.execute(
            sa.select(CommunicationThread).where(
                CommunicationThread.tenant_id == tenant_id,
                CommunicationThread.channel == "telegram",
                CommunicationThread.channel_thread_ref == chat_id,
            )
        )
    ).scalars().all()
    for thread in thread_rows:
        thread.linked_candidate_id = str(candidate.id)
        if not str(thread.subject or "").strip():
            thread.subject = _candidate_name(candidate)


async def _send_telegram_link_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    username: str | None,
    candidate: Candidate,
    email_to: str,
) -> tuple[bool, str]:
    code = str(secrets.randbelow(900000) + 100000)
    now = _now_utc()
    expires_at = now + timedelta(minutes=10)

    state = _as_dict(candidate.intake_state)
    notifications = _as_dict(state.get("notifications"))
    telegram_state = _as_dict(notifications.get("telegram"))
    telegram_state["chat_id"] = chat_id
    if username:
        telegram_state["username"] = username
    telegram_state["updated_at"] = now.isoformat()
    telegram_state["link_verification"] = {
        "chat_id": chat_id,
        "email": email_to,
        "code_hash": _telegram_otp_hash(chat_id=chat_id, code=code),
        "requested_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "attempts": 0,
    }
    notifications["telegram"] = telegram_state
    state["notifications"] = notifications
    candidate.intake_state = state
    await db.commit()

    candidate_name = _candidate_name(candidate)
    ok = await send_email_for_tenant(
        db,
        tenant_id=tenant_id,
        to=email_to,
        subject="HostFlow: код подтверждения Telegram",
        body=_candidate_verification_email_body(
            candidate_name=candidate_name, code=code
        ),
    )
    if not ok:
        return (
            False,
            "Не удалось отправить код на email. Попробуйте позже или напишите менеджеру.",
        )
    return True, f"Код подтверждения отправлен на {email_to}. Введите 6 цифр в этом чате."


async def _find_candidate_by_pending_verification(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
) -> Candidate | None:
    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
                Candidate.intake_state.is_not(None),
            )
            .limit(5000)
        )
    ).scalars().all()
    now = _now_utc()
    latest_candidate: Candidate | None = None
    latest_requested_at: datetime | None = None
    for candidate in rows:
        state = _as_dict(candidate.intake_state)
        notifications = _as_dict(state.get("notifications"))
        tg = _as_dict(notifications.get("telegram"))
        pending = _as_dict(tg.get("link_verification"))
        if str(pending.get("chat_id") or "").strip() != chat_id:
            continue
        expires_at = _coerce_datetime(pending.get("expires_at"))
        if expires_at is not None and expires_at < now:
            continue
        requested_at = _coerce_datetime(pending.get("requested_at"))
        if latest_candidate is None or (
            requested_at
            and (latest_requested_at is None or requested_at > latest_requested_at)
        ):
            latest_candidate = candidate
            latest_requested_at = requested_at
    return latest_candidate
