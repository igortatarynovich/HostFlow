"""Contact attempts service: log attempts, enforce limits, auto-reject."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models.candidate import Candidate
from backend.app.models.contact_attempt import ContactAttempt
from backend.app.models.final_no_contact_notification import FinalNoContactNotification
from backend.app.services.audit import log_audit_event
from backend.app.services.tenant_links import get_tenant_link
from backend.app.services.notifications import notify
from backend.app.services.tenant_email import send_email_for_tenant
from backend.app.services.rodo import get_first_rodo_sent
from backend.app.services.uos_auto_activities import ensure_candidate_stage_follow_up_task
from backend.app.services.handoff import is_client_tenant
from backend.app.models.tenant import TenantLink
from sqlalchemy import or_

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_POST_ACTION = "auto_reject"


async def get_effective_contact_policy(
    db: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
) -> dict:
    """Get contact policy for candidate (from tenant_link or defaults).
    
    Supports both agency and client tenants:
    - For agency: searches TenantLink by agency_tenant_id and client_company_id
      If candidate has no company_id but has vacancy_id, gets company_id from vacancy
    - For client: searches TenantLink by client_tenant_id or client_company_id (if company belongs to client tenant)
    """
    import logging
    from backend.app.models.vacancy import Vacancy
    
    logger = logging.getLogger(__name__)
    
    company_id = candidate.company_id
    
    logger.debug(
        "get_effective_contact_policy: candidate_id=%s tenant_id=%s company_id=%s vacancy_id=%s",
        candidate.id,
        tenant_id,
        company_id,
        candidate.vacancy_id,
    )
    
    # If candidate has no company_id but has vacancy_id, get company_id from vacancy
    # This is important for agency tenants working with candidates destined for client companies
    if not company_id and candidate.vacancy_id:
        vacancy_stmt = select(Vacancy.company_id).where(
            Vacancy.id == candidate.vacancy_id
        )
        vacancy_result = await db.execute(vacancy_stmt)
        vacancy_company_id = vacancy_result.scalar_one_or_none()
        if vacancy_company_id:
            company_id = vacancy_company_id
            logger.debug(
                "get_effective_contact_policy: got company_id=%s from vacancy_id=%s",
                company_id,
                candidate.vacancy_id,
            )
    
    policy = {
        "enabled": False,
        "max_attempts": DEFAULT_MAX_ATTEMPTS,
        "post_action": DEFAULT_POST_ACTION,
        "stage_code": None,
        "rodo_sent": False,
        "tracking_disabled_reason": None,
    }
    tenant_link_found = False

    # Determine if tenant is a client tenant
    is_client = await is_client_tenant(db, tenant_id)
    
    logger.debug(
        "get_effective_contact_policy: is_client=%s company_id=%s",
        is_client,
        company_id,
    )
    
    if company_id:
        link = None
        if is_client:
            # For client tenant: search by client_tenant_id or client_company_id
            stmt = select(TenantLink).where(
                TenantLink.status == "active",
                or_(
                    TenantLink.client_tenant_id == tenant_id,
                    TenantLink.client_company_id == company_id
                )
            )
            result = await db.execute(stmt)
            link = result.scalar_one_or_none()
            logger.debug(
                "get_effective_contact_policy: client tenant link found=%s",
                link is not None,
            )
        else:
            # For agency tenant: search by agency_tenant_id and client_company_id
            # Also check handoff_include_company_id for links to client tenants
            link = await get_tenant_link(
                db, agency_tenant_id=tenant_id, client_company_id=company_id
            )
            # If not found by client_company_id, try searching by handoff_include_company_id
            if not link:
                stmt = select(TenantLink).where(
                    TenantLink.agency_tenant_id == tenant_id,
                    TenantLink.status == "active",
                    TenantLink.handoff_include_company_id == company_id,
                )
                result = await db.execute(stmt)
                link = result.scalar_one_or_none()
            logger.debug(
                "get_effective_contact_policy: agency tenant link found=%s (agency_tenant_id=%s company_id=%s)",
                link is not None,
                tenant_id,
                company_id,
            )
        
        if link:
            tenant_link_found = True
            contact_policy = link.get_contact_policy()
            logger.info(
                "get_effective_contact_policy: applying contact policy from link_id=%s enabled=%s max_attempts=%s",
                link.id,
                contact_policy.get("enabled"),
                contact_policy.get("max_attempts"),
            )
            policy.update(contact_policy)
        else:
            logger.warning(
                "get_effective_contact_policy: no TenantLink found for tenant_id=%s company_id=%s is_client=%s",
                tenant_id,
                company_id,
                is_client,
            )
    else:
        logger.warning(
            "get_effective_contact_policy: no company_id for candidate_id=%s (company_id=%s vacancy_id=%s)",
            candidate.id,
            candidate.company_id,
            candidate.vacancy_id,
        )
    
    # RODO must be sent before contact attempts
    first_rodo = await get_first_rodo_sent(db, candidate.id)
    policy["rodo_sent"] = first_rodo is not None

    if not policy.get("enabled"):
        if not company_id:
            policy["tracking_disabled_reason"] = "no_company"
        elif not tenant_link_found:
            policy["tracking_disabled_reason"] = "no_tenant_link"
        else:
            policy["tracking_disabled_reason"] = "disabled_in_link"
    else:
        policy["tracking_disabled_reason"] = None

    logger.debug(
        "get_effective_contact_policy: final policy enabled=%s rodo_sent=%s",
        policy["enabled"],
        policy["rodo_sent"],
    )

    return policy


async def count_contact_attempts(db: AsyncSession, candidate_id: str) -> int:
    """Number of logged contact attempts for candidate."""
    stmt = select(func.count()).select_from(ContactAttempt).where(ContactAttempt.candidate_id == candidate_id)
    return int((await db.scalar(stmt)) or 0)


async def list_attempts(
    db: AsyncSession,
    candidate_id: str,
) -> list[ContactAttempt]:
    """List contact attempts for candidate, ordered by attempt_number."""
    stmt = (
        select(ContactAttempt)
        .where(ContactAttempt.candidate_id == candidate_id)
        .order_by(ContactAttempt.attempt_number.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_next_attempt_number(db: AsyncSession, candidate_id: str) -> int:
    """Get next attempt_number (count + 1)."""
    stmt = select(func.count(ContactAttempt.id)).where(
        ContactAttempt.candidate_id == candidate_id
    )
    count = (await db.scalar(stmt)) or 0
    return count + 1


async def _all_no_contact(db: AsyncSession, candidate_id: str, max_n: int) -> bool:
    """Check if all attempts up to max_n are no_answer/unavailable/wrong_number (not answered)."""
    stmt = (
        select(ContactAttempt)
        .where(ContactAttempt.candidate_id == candidate_id)
        .order_by(ContactAttempt.attempt_number.asc())
        .limit(max_n)
    )
    result = await db.execute(stmt)
    attempts = list(result.scalars().all())
    if len(attempts) < max_n:
        return False
    no_contact_results = {"no_answer", "wrong_number", "unavailable"}
    return all(a.result in no_contact_results for a in attempts)


async def _apply_auto_reject(
    db: AsyncSession,
    candidate: Candidate,
    tenant_id: str,
    actor_id: Optional[str],
) -> None:
    """Set candidate to rejected, send final notification, log audit."""
    candidate.status = "rejected"
    reasons = list(candidate.status_reason or [])
    if "no_contact_after_3_attempts" not in reasons:
        reasons.append("no_contact_after_3_attempts")
    candidate.status_reason = reasons

    email = (candidate.email or "").strip()
    channel = "email" if email else "sms"
    recipient = email or (candidate.phone or "")

    notif = FinalNoContactNotification(
        id=str(uuid4()),
        candidate_id=candidate.id,
        sent_at=datetime.now(timezone.utc),
        channel=channel,
        template_id="final_no_contact",
        status="sent",
    )
    db.add(notif)
    await db.flush()

    if recipient:
        subject = "HostFlow – brak kontaktu"
        body = "Nie udało nam się nawiązać kontaktu. Rekrutacja zakończona."
        if channel == "email":
            await send_email_for_tenant(
                db, tenant_id=tenant_id, to=recipient, subject=subject, body=body
            )
        else:
            await notify(
                to=recipient,
                subject=subject,
                text=body,
                template_key="final_no_contact",
                template_context={"first_name": candidate.first_name or "Kandydacie"},
                channels=[channel],
            )

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.rejected_no_contact,
        entity_type=AuditEntityType.contact_attempt,
        entity_id=notif.id,
        actor_id=actor_id,
        payload={"candidate_id": candidate.id},
    )


async def create_attempt(
    db: AsyncSession,
    *,
    candidate_id: str,
    tenant_id: str,
    channel: str,
    result: str,
    note: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> tuple[ContactAttempt | None, str | None]:
    """
    Create contact attempt. Returns (attempt, error_message).
    If max attempts reached and all no-contact, applies post_action (auto_reject).
    """
    cand = await db.get(Candidate, candidate_id)
    if not cand:
        return None, "Candidate not found"

    # RODO must be sent before contact attempts (art.14 compliance)
    first_rodo = await get_first_rodo_sent(db, candidate_id)
    if not first_rodo:
        return None, "RODO must be sent to candidate before logging contact attempts"

    policy = await get_effective_contact_policy(db, tenant_id, cand)
    if not policy.get("enabled", False):
        return None, "Contact attempts not enabled for this candidate"

    max_attempts = policy.get("max_attempts") or DEFAULT_MAX_ATTEMPTS
    next_num = await get_next_attempt_number(db, candidate_id)
    if next_num > max_attempts:
        return None, f"Maximum {max_attempts} attempts already reached"

    now = datetime.now(timezone.utc)
    attempt = ContactAttempt(
        id=str(uuid4()),
        candidate_id=candidate_id,
        attempt_number=next_num,
        attempted_at=now,
        attempted_by_user_id=actor_id,
        channel=channel,
        result=result,
        note=note,
    )
    db.add(attempt)
    await db.flush()

    await log_audit_event(
        db,
        tenant_id=tenant_id,
        event_type=AuditEventType.contact_attempt_logged,
        entity_type=AuditEntityType.contact_attempt,
        entity_id=attempt.id,
        actor_id=actor_id,
        payload={"candidate_id": candidate_id, "attempt_number": next_num, "result": result},
    )

    # Auto-set stage based on result
    previous_stage = str(getattr(cand, "stage", None) or "").strip() or None
    no_contact_results = {"no_answer", "wrong_number", "unavailable"}
    if result in no_contact_results:
        cand.stage = "no_answer"
        if cand.status != "rejected":
            cand.status = "no_answer"
    elif result == "answered":
        cand.stage = "contacted"
        cand.status = "contacted"
        await ensure_candidate_stage_follow_up_task(
            db,
            tenant_id=tenant_id,
            actor_id=str(actor_id or "").strip() or "uos-auto",
            candidate=cand,
            old_stage=previous_stage,
            new_stage="contacted",
        )

    # Check post-action: if we just reached max and all are no-contact
    if next_num == max_attempts and await _all_no_contact(db, candidate_id, max_attempts):
        post_action = policy.get("post_action") or DEFAULT_POST_ACTION
        if post_action == "auto_reject":
            await _apply_auto_reject(db, cand, tenant_id, actor_id)
        elif post_action == "stage_change":
            stage = policy.get("stage_code")
            if stage:
                cand.stage = stage
                # Optionally add status_reason

    return attempt, None
