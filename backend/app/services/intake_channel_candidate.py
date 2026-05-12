"""Non-lead intake paths: create Candidate via ``create_candidate_full`` + shared audit.

Public intake and Telegram historically used ``Candidate(...)`` + ``db.add``; this module
keeps behavior while aligning with ``docs/specs/workflows/lead-conversion-contract.md``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.core.audit_events import AuditEntityType
from backend.app.models.candidate import Candidate
from backend.app.modules.leads.lead_candidate_conversion import CONVERSION_CONTRACT_VERSION
from backend.app.services.audit import log_audit_event
from backend.app.services.tenant_quota import ensure_active_records_quota

async def emit_intake_channel_candidate_created_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    source_channel: str,
    creation_mode: str,
    stable_intake_id: Optional[str],
    stable_intake_id_kind: Optional[str],
    assignment_state: str,
    vacancy_id: Optional[str],
    idempotent_replay: bool,
    recruiter_id: Optional[str] = None,
) -> None:
    payload: Dict[str, Any] = {
        "event_name": "candidate_created",
        "conversion_contract_version": CONVERSION_CONTRACT_VERSION,
        "intake_bootstrap": True,
        "source_channel": source_channel,
        "creation_mode": creation_mode,
        "stable_intake_id": stable_intake_id,
        "stable_intake_id_kind": stable_intake_id_kind,
        "assignment_state": assignment_state,
        "vacancy_id": vacancy_id,
        "recruiter_id": recruiter_id,
        "idempotent_replay": idempotent_replay,
        "source_lead_id": None,
        "external_id": None,
        "duplicate_result": "no_duplicate",
    }
    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type="candidate_created",
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate_id),
        actor_id=None,
        payload=payload,
    )


def public_intake_stable_contact_key(
    *,
    email: Optional[str],
    phone: Optional[str],
    phone_country_code: Optional[str],
) -> str:
    e = (email or "").strip().lower()
    p = (phone or "").strip()
    cc = (phone_country_code or "").strip()
    return f"{e}|{cc}|{p}"


async def create_public_intake_draft_via_service(
    db: AsyncSession,
    tenant_id: str,
    *,
    intake_source: str,
    vacancy_id: Optional[str],
    phone_country_code: Optional[str],
    phone: Optional[str],
    email: Optional[str],
    intake_token: str,
    intake_token_created_at: datetime,
    intake_token_expires_at: datetime,
    intake_state: Dict[str, Any],
) -> Candidate:
    """INSERT draft dossier for public apply flow using ``create_candidate_full`` + intake columns."""
    cand_id = str(uuid4())
    contacts: Dict[str, Any] = {}
    if phone:
        contacts["phone"] = phone
    if phone_country_code:
        contacts["phone_country_code"] = phone_country_code
    if email:
        contacts["email"] = email

    payload: Dict[str, Any] = {
        "id": cand_id,
        "first_name": "Candidate",
        "last_name": "Draft",
        "phone": phone,
        "phone_country_code": phone_country_code,
        "email": email,
        "vacancy_id": vacancy_id,
        "source": intake_source,
        "stage": "docs_wait",
        "origin": {"public_intake": {"kind": "draft_session"}},
    }
    if contacts:
        payload["contacts"] = contacts

    c = await create_candidate_full(db, tenant_id, payload, actor_id=None, acl=None)

    await db.execute(
        update(Candidate)
        .where(Candidate.id == c.id, Candidate.tenant_id == tenant_id)
        .values(
            phone_country_code=phone_country_code,
            intake_token=intake_token,
            intake_token_created_at=intake_token_created_at,
            intake_token_expires_at=intake_token_expires_at,
            intake_status="draft",
            intake_state=intake_state,
        )
    )
    await db.flush()
    row = await db.execute(select(Candidate).where(Candidate.id == c.id, Candidate.tenant_id == tenant_id))
    c2 = row.scalar_one()
    stable = public_intake_stable_contact_key(
        email=email, phone=phone, phone_country_code=phone_country_code
    )
    await emit_intake_channel_candidate_created_audit(
        db,
        tenant_id=tenant_id,
        candidate_id=str(c2.id),
        source_channel="public_intake",
        creation_mode="semi_auto",
        stable_intake_id=stable,
        stable_intake_id_kind="contact_fingerprint",
        assignment_state=str(getattr(c2, "assignment_state", "") or ""),
        vacancy_id=str(vacancy_id) if vacancy_id else None,
        idempotent_replay=False,
        recruiter_id=str(c2.recruiter_id) if getattr(c2, "recruiter_id", None) else None,
    )
    return c2


async def create_telegram_intake_bootstrap_via_service(
    db: AsyncSession,
    *,
    tenant_id: str,
    chat_id: str,
    username: Optional[str],
    sender_label: Optional[str],
    sender_address: Optional[str],
    contact_phone: Optional[str],
) -> Candidate:
    """Bootstrap Telegram /intake dossier; idempotent on ``telegram_chat_id``."""
    # Deferred imports avoid circular imports (public.intake → this module → communications).
    from backend.app.api.v1.communications._helpers.candidate_lookup import (
        _find_candidate_by_telegram_chat,
    )
    from backend.app.api.v1.communications._helpers.telegram_intake.candidate_link import (
        _link_candidate_to_telegram_chat,
    )
    from backend.app.api.v1.communications._helpers.telegram_intake.docs_bridge import (
        _ensure_candidate_intake_token,
    )
    from backend.app.api.v1.communications._helpers.telegram_intake.ui_text import (
        _telegram_name_parts,
    )
    from backend.app.api.v1.communications._helpers.utils import _digits_only

    existing = await _find_candidate_by_telegram_chat(db, tenant_id=tenant_id, chat_id=chat_id)
    if existing is not None:
        await emit_intake_channel_candidate_created_audit(
            db,
            tenant_id=tenant_id,
            candidate_id=str(existing.id),
            source_channel="telegram",
            creation_mode="manual_bot",
            stable_intake_id=str(chat_id).strip(),
            stable_intake_id_kind="telegram_chat_id",
            assignment_state=str(getattr(existing, "assignment_state", "") or ""),
            vacancy_id=str(existing.vacancy_id) if getattr(existing, "vacancy_id", None) else None,
            idempotent_replay=True,
            recruiter_id=str(existing.recruiter_id) if getattr(existing, "recruiter_id", None) else None,
        )
        await db.commit()
        return existing

    await ensure_active_records_quota(db, tenant_id)
    first_name, last_name = _telegram_name_parts(sender_label, username)
    phone_digits = _digits_only(contact_phone)
    cand_id = str(uuid4())
    payload: Dict[str, Any] = {
        "id": cand_id,
        "first_name": first_name,
        "last_name": last_name or "Telegram",
        "phone": phone_digits or None,
        "stage": "docs_wait",
        "source": "telegram_bot",
        "origin": {"telegram_intake": {"chat_id": str(chat_id).strip()}},
    }
    if phone_digits:
        payload["contacts"] = {"phone": phone_digits}

    c = await create_candidate_full(db, tenant_id, payload, actor_id=None, acl=None)

    state: Dict[str, Any] = {}
    contacts: Dict[str, Any] = {
        "preferred_messenger": "telegram",
        "telegram_chat_id": chat_id,
    }
    if sender_address:
        contacts["telegram_user_id"] = sender_address
    if username:
        contacts["telegram_username"] = username
    if phone_digits:
        contacts["phone"] = phone_digits
    state["contacts"] = contacts

    await db.execute(
        update(Candidate)
        .where(Candidate.id == c.id, Candidate.tenant_id == tenant_id)
        .values(
            intake_status="draft",
            intake_state=state,
        )
    )
    await db.flush()
    row = await db.execute(select(Candidate).where(Candidate.id == c.id, Candidate.tenant_id == tenant_id))
    c2 = row.scalar_one()
    changed = _ensure_candidate_intake_token(c2)
    if changed:
        await db.flush()
    await _link_candidate_to_telegram_chat(
        db,
        tenant_id=tenant_id,
        chat_id=chat_id,
        candidate=c2,
        username=username,
    )
    await db.flush()
    await emit_intake_channel_candidate_created_audit(
        db,
        tenant_id=tenant_id,
        candidate_id=str(c2.id),
        source_channel="telegram",
        creation_mode="manual_bot",
        stable_intake_id=str(chat_id).strip(),
        stable_intake_id_kind="telegram_chat_id",
        assignment_state=str(getattr(c2, "assignment_state", "") or ""),
        vacancy_id=str(c2.vacancy_id) if getattr(c2, "vacancy_id", None) else None,
        idempotent_replay=False,
        recruiter_id=str(c2.recruiter_id) if getattr(c2, "recruiter_id", None) else None,
    )
    await db.commit()
    return c2
