"""Application matching for match_or_create (ADR-022 §4). Phase 1: Sales Inquiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.intake_platform.constants import MatchConfidence
from backend.app.intake_platform.operational_scope import is_open_sales_application, offering_context_matches
from backend.app.intake_platform.schemas import MatchPolicy, MatchResult
from backend.app.models.lead import Lead
from backend.app.services.contact_identifiers import normalize_email, normalize_phone_digits


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _lead_email(lead: Lead) -> Optional[str]:
    normalized = _record(lead.normalized)
    for key in ("email", "contact_email"):
        found = normalize_email(normalized.get(key))
        if found:
            return found
    contacts = _record(normalized.get("contact_person"))
    return normalize_email(contacts.get("email"))


def _lead_phone(lead: Lead) -> Optional[str]:
    normalized = _record(lead.normalized)
    for key in ("phone", "contact_phone"):
        found = normalize_phone_digits(normalized.get(key))
        if found:
            return found
    contacts = _record(normalized.get("contact_person"))
    return normalize_phone_digits(contacts.get("phone"))


def _lead_entity_profile_code(lead: Lead) -> Optional[str]:
    normalized = _record(lead.normalized)
    code = str(normalized.get("entity_profile_code") or "").strip()
    return code or None


def _match_strength(
    *,
    lead: Lead,
    email: Optional[str],
    phone: Optional[str],
) -> tuple[bool, bool]:
    lead_email = _lead_email(lead)
    lead_phone = _lead_phone(lead)
    email_hit = bool(email and lead_email and email == lead_email)
    phone_hit = bool(phone and lead_phone and phone == lead_phone)
    return email_hit, phone_hit


async def find_sales_inquiry_matches(
    db: AsyncSession,
    *,
    tenant_id: str,
    email: Optional[str],
    phone: Optional[str],
    entity_profile_code: str,
    match_policy: MatchPolicy,
    exclude_lead_id: Optional[str] = None,
    publication_id: Optional[str] = None,
    intake_source_profile_id: Optional[str] = None,
) -> MatchResult:
    norm_email = normalize_email(email)
    norm_phone = normalize_phone_digits(phone)
    if not norm_email and not norm_phone:
        return MatchResult(
            confidence=MatchConfidence.none.value,
            suggested_action="create",
            reasons=["no_identifiers"],
        )

    # Strong auto-attach requires both identifiers on the submission side.
    if not norm_email or not norm_phone:
        partial_only = True
    else:
        partial_only = False

    window_days = max(int(match_policy.window_days or 90), 1)
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    stmt = select(Lead).where(
        Lead.tenant_id == str(tenant_id),
        Lead.lead_type == "client",
        Lead.lead_target_type == "client_lead",
        Lead.created_at >= cutoff,
    )
    if exclude_lead_id:
        stmt = stmt.where(Lead.id != str(exclude_lead_id))

    rows = (await db.execute(stmt)).scalars().all()
    candidates: list[tuple[Lead, bool, bool]] = []
    for lead in rows:
        if not is_open_sales_application(
            lead,
            allowed_lifecycle_statuses=list(match_policy.allowed_lifecycle_statuses),
        ):
            continue
        if match_policy.require_entity_profile_match:
            ep = _lead_entity_profile_code(lead)
            if ep and ep != str(entity_profile_code).strip():
                continue
        if not offering_context_matches(
            lead=lead,
            publication_id=publication_id,
            intake_source_profile_id=intake_source_profile_id,
            require_offering_match=bool(match_policy.require_offering_match),
        ):
            continue
        email_hit, phone_hit = _match_strength(lead=lead, email=norm_email, phone=norm_phone)
        if email_hit or phone_hit:
            candidates.append((lead, email_hit, phone_hit))

    if not candidates:
        return MatchResult(
            confidence=MatchConfidence.none.value,
            suggested_action="create",
            reasons=["no_open_application_match"],
        )

    if partial_only:
        if len(candidates) == 1:
            lead, e_hit, p_hit = candidates[0]
            return MatchResult(
                confidence=MatchConfidence.possible.value,
                matched_application_ids=[str(lead.id)],
                suggested_action="review",
                reasons=["partial_identifier_only"],
            )
        return MatchResult(
            confidence=MatchConfidence.conflict.value,
            matched_application_ids=[str(lead.id) for lead, _, _ in candidates],
            suggested_action="review",
            reasons=["multiple_partial_matches"],
        )

    strong = [lead for lead, e_hit, p_hit in candidates if e_hit and p_hit]
    if len(strong) == 1:
        return MatchResult(
            confidence=MatchConfidence.strong_single.value,
            matched_application_ids=[str(strong[0].id)],
            suggested_action="attach",
            reasons=["email_and_phone_match"],
        )
    if len(strong) > 1:
        return MatchResult(
            confidence=MatchConfidence.multiple.value,
            matched_application_ids=[str(x.id) for x in strong],
            suggested_action="review",
            reasons=["multiple_strong_matches"],
        )

    if len(candidates) == 1:
        lead, e_hit, p_hit = candidates[0]
        reason = "email_match" if e_hit else "phone_match"
        return MatchResult(
            confidence=MatchConfidence.possible.value,
            matched_application_ids=[str(lead.id)],
            suggested_action="review",
            reasons=[reason],
        )

    return MatchResult(
        confidence=MatchConfidence.conflict.value,
        matched_application_ids=[str(lead.id) for lead, _, _ in candidates],
        suggested_action="review",
        reasons=["multiple_partial_matches"],
    )
