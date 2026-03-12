"""Draft intake reminders: email candidates who started but did not complete the questionnaire."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.core.settings import settings
from backend.app.services.tenant_email import send_email_for_tenant


DRAFT_REMINDER_COOLDOWN_DAYS = 7
DRAFT_REMINDER_MIN_IDLE_HOURS = 24


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def send_draft_reminders(db: AsyncSession, tenant_id: Optional[str] = None) -> int:
    """
    Send reminder emails to candidates with draft intake (not submitted).
    - intake_status = 'draft'
    - updated_at > 24h ago
    - has email or phone
    - intake_token not expired
    - last reminder sent > 7 days ago (or never)

    If tenant_id is None, processes all tenants.
    Returns count of reminders sent.
    """
    now = _now()
    cutoff_updated = now - timedelta(hours=DRAFT_REMINDER_MIN_IDLE_HOURS)
    cutoff_last_reminder = now - timedelta(days=DRAFT_REMINDER_COOLDOWN_DAYS)

    stmt = (
        select(Candidate)
        .where(Candidate.deleted_at.is_(None))
        .where(Candidate.intake_token.isnot(None))
        .where(
            or_(
                Candidate.intake_token_expires_at.is_(None),
                Candidate.intake_token_expires_at > now,
            )
        )
        .where(Candidate.intake_status == "draft")
        .where(Candidate.updated_at < cutoff_updated)
        .where(
            (Candidate.email.isnot(None) & (Candidate.email != ""))
            | (Candidate.phone.isnot(None) & (Candidate.phone != ""))
        )
    )
    if tenant_id:
        stmt = stmt.where(Candidate.tenant_id == tenant_id)
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    sent = 0
    base_url = (settings.frontend_url or "").strip().rstrip("/")
    if not base_url and hasattr(db, "bind") and db.bind:
        pass
    # Fallback for local dev
    if not base_url:
        base_url = "https://hostflow.cc"

    for cand in candidates:
        # Prefer email for reminder (candidate.email or intake_state.contacts)
        to_email = (cand.email or "").strip()
        if not to_email:
            state_raw = cand.intake_state or {}
            contacts = state_raw.get("contacts") or {}
            to_email = (contacts.get("email") or "").strip()
        if not to_email:
            continue

        # Check last reminder
        state = cand.intake_state or {}
        prefs = state.get("notifications", {}) or {}
        last_sent_raw = prefs.get("draft_reminder_sent_at")
        if last_sent_raw:
            try:
                last_sent = datetime.fromisoformat(last_sent_raw.replace("Z", "+00:00"))
                if last_sent > cutoff_last_reminder:
                    continue
            except (ValueError, TypeError):
                pass

        apply_url = f"{base_url}/public/apply/{cand.intake_token}"
        subject = "HostFlow — Kontynuuj wypełnianie ankiety"
        body = f"""Witaj,

Rozpocząłeś wypełnianie ankiety, ale nie ukończyłeś jej. Możesz kontynuować w dowolnym momencie:

{apply_url}

Link jest ważny przez ograniczony czas. W razie pytań skontaktuj się z rekruterem.

Pozdrawiamy,
HostFlow"""

        try:
            ok = await send_email_for_tenant(
                db,
                tenant_id=cand.tenant_id,
                to=to_email,
                subject=subject,
                body=body,
            )
            if ok:
                if not cand.intake_state:
                    cand.intake_state = {}
                prefs = cand.intake_state.get("notifications", {}) or {}
                prefs["draft_reminder_sent_at"] = now.isoformat()
                cand.intake_state["notifications"] = prefs
                sent += 1
        except Exception:
            pass

    if sent:
        await db.commit()
    return sent
