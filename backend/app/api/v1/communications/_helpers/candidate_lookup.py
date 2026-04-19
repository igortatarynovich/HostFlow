"""Candidate lookup, identity, and public-link helpers.

Shared by the telegram-intake flow and a handful of inbox routes; pulled
out of ``__init__.py`` so the candidate-resolution surface is testable
on its own without booting the rest of the communications module.

* ``_candidate_name`` — canonical display name (first+last → short_id → id).
* ``_candidate_public_status_url`` / ``_candidate_apply_url`` — render the
  public links that we expose in candidate notifications and replies.
* ``_find_candidate_by_bind_token`` — resolve any of intake_token /
  status_share_token / short_id / id within a tenant.
* ``_find_candidate_by_telegram_chat`` — locate the candidate currently
  bound to a given telegram ``chat_id`` (via the linked thread or via
  ``intake_state.notifications.telegram.chat_id`` fallback for chats
  that haven't been thread-linked yet).
* ``_candidate_email_options`` / ``_candidate_phone_options`` — collect
  every known email / phone of a candidate (top-level columns + the
  ``contacts`` blob + ``intake_state.contacts`` overlay) into a set so
  callers can do membership checks.
* ``_find_candidates_by_contact`` — given a free-form email or phone
  string, return the matching candidates within a tenant (substring
  match in either direction for phones to handle missing/extra country
  codes).

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 5/N).
"""

from __future__ import annotations

from typing import Any, List, Set

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.models.candidate import Candidate
from backend.app.models.communication import CommunicationThread

from .utils import _as_dict, _digits_only, _normalize_email_value

__all__ = [
    "_candidate_name",
    "_candidate_public_status_url",
    "_candidate_apply_url",
    "_find_candidate_by_bind_token",
    "_find_candidate_by_telegram_chat",
    "_candidate_email_options",
    "_candidate_phone_options",
    "_find_candidates_by_contact",
]


def _candidate_name(candidate: Candidate) -> str:
    first = str(getattr(candidate, "first_name", "") or "").strip()
    last = str(getattr(candidate, "last_name", "") or "").strip()
    full = " ".join(x for x in [first, last] if x).strip()
    return full or str(
        getattr(candidate, "short_id", "")
        or getattr(candidate, "id", "")
        or "candidate"
    )


def _candidate_public_status_url(candidate: Candidate) -> str | None:
    token = str(
        getattr(candidate, "status_share_token", None)
        or getattr(candidate, "intake_token", None)
        or ""
    ).strip()
    if not token:
        return None
    base_url = (
        str(settings.frontend_url or "https://hostflow.cc").strip()
        or "https://hostflow.cc"
    )
    return f"{base_url.rstrip('/')}/public/status/{token}"


def _candidate_apply_url(candidate: Candidate) -> str | None:
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = (
        str(settings.frontend_url or "https://hostflow.cc").strip()
        or "https://hostflow.cc"
    )
    return f"{base_url.rstrip('/')}/public/apply/{token}"


async def _find_candidate_by_bind_token(
    db: AsyncSession,
    *,
    tenant_id: str,
    token: str,
) -> Candidate | None:
    token_norm = str(token or "").strip()
    if not token_norm:
        return None
    stmt = (
        sa.select(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            sa.or_(
                Candidate.intake_token == token_norm,
                Candidate.status_share_token == token_norm,
                Candidate.short_id == token_norm,
                Candidate.id == token_norm,
            ),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _find_candidate_by_telegram_chat(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
) -> Candidate | None:
    chat_ref = str(chat_id or "").strip()
    if not chat_ref:
        return None
    thread_stmt = (
        sa.select(CommunicationThread.linked_candidate_id)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == "telegram",
            CommunicationThread.channel_thread_ref == chat_ref,
            CommunicationThread.linked_candidate_id.is_not(None),
        )
        .order_by(sa.desc(CommunicationThread.updated_at))
        .limit(1)
    )
    candidate_id = (await db.execute(thread_stmt)).scalar()
    if candidate_id:
        candidate = await db.get(Candidate, str(candidate_id))
        if candidate and str(getattr(candidate, "tenant_id", "")) == tenant_id:
            return candidate
    # Fallback for newly linked chats before thread link sync.
    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.intake_state.is_not(None),
            )
            .limit(5000)
        )
    ).scalars().all()
    for cand in rows:
        state = _as_dict(getattr(cand, "intake_state", None))
        prefs = _as_dict(state.get("notifications"))
        tg = _as_dict(prefs.get("telegram"))
        if str(tg.get("chat_id") or "").strip() == chat_ref:
            return cand
    return None


def _candidate_email_options(candidate: Candidate) -> Set[str]:
    opts: Set[str] = set()
    email = _normalize_email_value(getattr(candidate, "email", None))
    if email:
        opts.add(email)
    contacts = _as_dict(getattr(candidate, "contacts", None))
    c_email = _normalize_email_value(contacts.get("email"))
    if c_email:
        opts.add(c_email)
    state = _as_dict(getattr(candidate, "intake_state", None))
    intake_contacts = _as_dict(state.get("contacts"))
    s_email = _normalize_email_value(intake_contacts.get("email"))
    if s_email:
        opts.add(s_email)
    return opts


def _candidate_phone_options(candidate: Candidate) -> Set[str]:
    opts: Set[str] = set()

    def _add(code: Any, phone: Any) -> None:
        p = _digits_only(phone)
        if not p:
            return
        c = _digits_only(code)
        opts.add(p)
        if c:
            opts.add(f"{c}{p}")

    _add(
        getattr(candidate, "phone_country_code", None),
        getattr(candidate, "phone", None),
    )
    contacts = _as_dict(getattr(candidate, "contacts", None))
    _add(contacts.get("phone_country_code"), contacts.get("phone"))
    state = _as_dict(getattr(candidate, "intake_state", None))
    intake_contacts = _as_dict(state.get("contacts"))
    _add(intake_contacts.get("phone_country_code"), intake_contacts.get("phone"))
    return opts


async def _find_candidates_by_contact(
    db: AsyncSession,
    *,
    tenant_id: str,
    contact_input: str,
) -> List[Candidate]:
    raw = str(contact_input or "").strip()
    if not raw:
        return []
    email_norm = _normalize_email_value(raw)
    phone_norm = _digits_only(raw)

    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
            )
            .limit(5000)
        )
    ).scalars().all()
    if not rows:
        return []
    matches: List[Candidate] = []
    seen: Set[str] = set()
    for candidate in rows:
        is_match = False
        if email_norm:
            if email_norm in _candidate_email_options(candidate):
                is_match = True
        elif phone_norm:
            for cand_phone in _candidate_phone_options(candidate):
                if (
                    cand_phone == phone_norm
                    or cand_phone.endswith(phone_norm)
                    or phone_norm.endswith(cand_phone)
                ):
                    is_match = True
                    break
        if is_match and str(candidate.id) not in seen:
            seen.add(str(candidate.id))
            matches.append(candidate)
    return matches
