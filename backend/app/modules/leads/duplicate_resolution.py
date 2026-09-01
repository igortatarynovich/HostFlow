"""Minimal duplicate resolution for Lead intake (MVP).

Levels:
- ``exact`` — strong identifier match (email, operational phone, passport/tacho digits).
- ``probable`` — same person likely (name + phone fragment) but not exact tier.
- ``none`` — no match.

HR protection: workforce row or agency-blocking handoff forces ``duplicate_review`` instead of
silent attach, even when match is exact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Candidate, Lead
from backend.app.models.user import Role as UserRole
from backend.app.services import events
from backend.app.services.candidate_workforce_lock import is_candidate_locked_by_workforce
from backend.app.services.events import EventAudience
from backend.app.services.handoff import get_accepted_handoff_for_agency

DuplicateMatchLevel = Literal["none", "exact", "probable"]


@dataclass
class LeadDuplicateMatch:
    level: DuplicateMatchLevel
    candidate: Optional[Candidate]
    reasons: list[str]
    hr_blockers: list[str]

    @property
    def needs_duplicate_review(self) -> bool:
        if self.level == "probable":
            return True
        if self.level == "exact" and self.hr_blockers:
            return True
        return False


from backend.app.services.contact_identifiers import digits_only, normalize_email


def duplicate_ignored_candidate_ids(normalized: dict[str, Any]) -> set[str]:
    """Candidates the operator chose to treat as non-matches for this lead (``create_new`` / ``ignore``)."""
    raw = normalized.get("duplicate_override_v1")
    if not isinstance(raw, dict):
        return set()
    ids = raw.get("ignored_candidate_ids")
    if not isinstance(ids, list):
        return set()
    return {str(x).strip() for x in ids if str(x).strip()}


def _candidate_unless_ignored(
    cand: Optional[Candidate], ignored: set[str]
) -> Optional[Candidate]:
    if cand is None:
        return None
    if str(cand.id) in ignored:
        return None
    return cand


def _is_placeholder_lead_name(first_name: Optional[str], last_name: Optional[str]) -> bool:
    fn = (first_name or "").strip().lower()
    ln = (last_name or "").strip().lower()
    if not fn and not ln:
        return True
    if fn == "meta" and ln == "lead":
        return True
    return False


def _passport_digits_from_normalized(normalized: dict[str, Any]) -> Optional[str]:
    for key in (
        "passport_number",
        "document_number",
        "national_id_number",
        "id_number",
        "pesel",
    ):
        raw = normalized.get(key)
        if raw is None:
            continue
        d = digits_only(str(raw))
        if len(d) >= 4:
            return d
    return None


def _tachograph_digits_from_normalized(normalized: dict[str, Any]) -> Optional[str]:
    for key in ("tachograph_card_number", "tacho_card_number", "tachograph_number"):
        raw = normalized.get(key)
        if raw is None:
            continue
        d = digits_only(str(raw))
        if len(d) >= 4:
            return d
    return None


def _candidate_personal_digits(candidate: Candidate, *keys: str) -> str:
    pd = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    if not isinstance(pd, dict):
        return ""
    for k in keys:
        d = digits_only(str(pd.get(k) or ""))
        if d:
            return d
    return ""


def _phones_operational_match(lead_phone_digits: str, candidate: Candidate) -> bool:
    """Intl/national tolerant match (legacy lead dedup semantics)."""
    if not lead_phone_digits:
        return False
    variants: set[str] = set()
    if candidate.phone:
        variants.add(digits_only(candidate.phone.strip()))
    cc = (candidate.phone_country_code or "").strip()
    pn = (candidate.phone or "").strip()
    combined = digits_only(f"{cc}{pn}")
    if combined:
        variants.add(combined)
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    if isinstance(contacts, dict):
        ccp = (contacts.get("phone_country_code") or "").strip()
        cp = (contacts.get("phone") or "").strip()
        variants.add(digits_only(cp))
        variants.add(digits_only(f"{ccp}{cp}"))
    variants = {v for v in variants if v}
    if not variants:
        return False
    for cand_d in variants:
        if cand_d == lead_phone_digits:
            return True
        if len(lead_phone_digits) >= 9:
            last_l = lead_phone_digits[-min(9, len(lead_phone_digits)) :]
            if cand_d.endswith(last_l):
                return True
        if len(cand_d) >= 9:
            last_c = cand_d[-min(9, len(cand_d)) :]
            if lead_phone_digits.endswith(last_c):
                return True
    return False


def _candidate_phone_digit_variants(candidate: Candidate) -> set[str]:
    variants: set[str] = set()
    if candidate.phone:
        variants.add(digits_only(candidate.phone.strip()))
    cc = (candidate.phone_country_code or "").strip()
    pn = (candidate.phone or "").strip()
    combined = digits_only(f"{cc}{pn}")
    if combined:
        variants.add(combined)
    contacts = candidate._get_contacts() if hasattr(candidate, "_get_contacts") else {}
    if isinstance(contacts, dict):
        ccp = (contacts.get("phone_country_code") or "").strip()
        cp = (contacts.get("phone") or "").strip()
        variants.add(digits_only(cp))
        variants.add(digits_only(f"{ccp}{cp}"))
    return {v for v in variants if v}


async def _hr_duplicate_blockers(
    db: AsyncSession, *, tenant_id: str, candidate_id: str
) -> list[str]:
    blockers: list[str] = []
    cid = str(candidate_id).strip()
    tid = str(tenant_id).strip()
    if await is_candidate_locked_by_workforce(db, tenant_id=tid, candidate_id=cid):
        blockers.append("workforce")
    ho = await get_accepted_handoff_for_agency(db, cid, tid)
    if ho is not None:
        blockers.append("active_handoff")
    return blockers


async def _find_exact_by_document_digits(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    digits: str,
    doc_kind: str,
) -> Optional[Candidate]:
    if not digits:
        return None
    filters = [Candidate.tenant_id == tenant_id, Candidate.deleted_at.is_(None)]
    if company_id:
        filters.append(or_(Candidate.company_id == company_id, Candidate.company_id.is_(None)))
    result = await db.execute(select(Candidate).where(and_(*filters)))
    keys = (
        ("passport_number", "document_number", "pesel", "national_id_number")
        if doc_kind == "passport"
        else ("tachograph_card_number", "tacho_card_number", "tachograph_number")
    )
    for row in result.scalars().all():
        pd_digits = _candidate_personal_digits(row, *keys)
        if pd_digits and pd_digits == digits:
            return row
    return None


async def _find_exact_by_email(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    email_lower: str,
) -> Optional[Candidate]:
    filters = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
        func.lower(Candidate.email) == email_lower,
    ]
    if company_id:
        filters.append(or_(Candidate.company_id == company_id, Candidate.company_id.is_(None)))
    stmt = (
        select(Candidate)
        .where(and_(*filters))
        .order_by(Candidate.created_at.asc())
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def _find_exact_by_phone_operational(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    lead_phone_digits: str,
) -> Optional[Candidate]:
    if not lead_phone_digits:
        return None
    phone_matchers = []
    phone_matchers.append(
        func.regexp_replace(func.coalesce(Candidate.phone, ""), r"[^0-9]", "", "g")
        == lead_phone_digits
    )
    if len(lead_phone_digits) >= 9:
        last_digits = lead_phone_digits[-min(9, len(lead_phone_digits)) :]
        stored_phone_digits = func.regexp_replace(
            func.coalesce(Candidate.phone, ""), r"[^0-9]", "", "g"
        )
        phone_matchers.append(stored_phone_digits.like(f"%{last_digits}"))
    filters = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
        or_(*phone_matchers),
    ]
    if company_id:
        filters.append(or_(Candidate.company_id == company_id, Candidate.company_id.is_(None)))
    stmt = (
        select(Candidate)
        .where(and_(*filters))
        .order_by(Candidate.created_at.asc())
        .limit(1)
    )
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()
    if row is None:
        return None
    if _phones_operational_match(lead_phone_digits, row):
        return row
    return None


async def _find_probable_by_name_and_phone_fragment(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    normalized: dict[str, Any],
    lead_phone_digits: str,
) -> Optional[Candidate]:
    fn = str(normalized.get("first_name") or "").strip()
    ln = str(normalized.get("last_name") or "").strip()
    if not ln and normalized.get("full_name"):
        # Avoid matching placeholder split; require explicit last_name for probable tier.
        parts = str(normalized.get("full_name") or "").strip().split(None, 1)
        if len(parts) >= 2:
            fn = fn or parts[0]
            ln = parts[1]
    if _is_placeholder_lead_name(fn, ln):
        return None
    if not lead_phone_digits or len(lead_phone_digits) < 7:
        return None
    filters = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
        func.lower(Candidate.first_name) == fn.lower(),
        func.lower(Candidate.last_name) == ln.lower(),
    ]
    if company_id:
        filters.append(or_(Candidate.company_id == company_id, Candidate.company_id.is_(None)))
    stmt = select(Candidate).where(and_(*filters)).order_by(Candidate.created_at.asc()).limit(20)
    res = await db.execute(stmt)
    # Weaker than operational match: shared 7-digit fragment inside the longer number.
    frag = lead_phone_digits[-7:]
    for cand in res.scalars().all():
        if _phones_operational_match(lead_phone_digits, cand):
            continue
        for variant in _candidate_phone_digit_variants(cand):
            if len(variant) < 7:
                continue
            if lead_phone_digits == variant:
                continue
            if frag in variant:
                return cand
    return None


async def resolve_lead_duplicate_match(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    normalized: dict[str, Any],
    email: Optional[str],
    phone: Optional[str],
) -> LeadDuplicateMatch:
    """Classify duplicate match for a normalized lead payload."""
    ignored = duplicate_ignored_candidate_ids(normalized)
    em = normalize_email(email)
    phone_digits = digits_only(str(phone or "").strip())

    passport_d = _passport_digits_from_normalized(normalized)
    if passport_d:
        hit = _candidate_unless_ignored(
            await _find_exact_by_document_digits(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                digits=passport_d,
                doc_kind="passport",
            ),
            ignored,
        )
        if hit is not None:
            blockers = await _hr_duplicate_blockers(db, tenant_id=tenant_id, candidate_id=str(hit.id))
            return LeadDuplicateMatch(
                level="exact",
                candidate=hit,
                reasons=["passport_digits"],
                hr_blockers=blockers,
            )

    tacho_d = _tachograph_digits_from_normalized(normalized)
    if tacho_d:
        hit = _candidate_unless_ignored(
            await _find_exact_by_document_digits(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                digits=tacho_d,
                doc_kind="tacho",
            ),
            ignored,
        )
        if hit is not None:
            blockers = await _hr_duplicate_blockers(db, tenant_id=tenant_id, candidate_id=str(hit.id))
            return LeadDuplicateMatch(
                level="exact",
                candidate=hit,
                reasons=["tachograph_digits"],
                hr_blockers=blockers,
            )

    if em:
        hit = _candidate_unless_ignored(
            await _find_exact_by_email(db, tenant_id=tenant_id, company_id=company_id, email_lower=em),
            ignored,
        )
        if hit is not None:
            blockers = await _hr_duplicate_blockers(db, tenant_id=tenant_id, candidate_id=str(hit.id))
            return LeadDuplicateMatch(
                level="exact",
                candidate=hit,
                reasons=["email"],
                hr_blockers=blockers,
            )

    if phone_digits:
        hit = _candidate_unless_ignored(
            await _find_exact_by_phone_operational(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                lead_phone_digits=phone_digits,
            ),
            ignored,
        )
        if hit is not None:
            blockers = await _hr_duplicate_blockers(db, tenant_id=tenant_id, candidate_id=str(hit.id))
            return LeadDuplicateMatch(
                level="exact",
                candidate=hit,
                reasons=["phone_operational"],
                hr_blockers=blockers,
            )

    probable = _candidate_unless_ignored(
        await _find_probable_by_name_and_phone_fragment(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            normalized=normalized,
            lead_phone_digits=phone_digits,
        ),
        ignored,
    )
    if probable is not None:
        blockers = await _hr_duplicate_blockers(db, tenant_id=tenant_id, candidate_id=str(probable.id))
        return LeadDuplicateMatch(
            level="probable",
            candidate=probable,
            reasons=["name_and_phone_fragment"],
            hr_blockers=blockers,
        )

    return LeadDuplicateMatch(level="none", candidate=None, reasons=[], hr_blockers=[])


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def build_duplicate_prior_summary(candidate: Any) -> Optional[dict[str, Any]]:
    """Compact history of the matched candidate (created? outcome? reason?)."""
    if candidate is None:
        return None
    cid = str(getattr(candidate, "id", "") or "").strip()
    if not cid:
        return None

    extra = _as_mapping(getattr(candidate, "extra", None))
    origin = _as_mapping(getattr(candidate, "origin", None))
    first = str(getattr(candidate, "first_name", "") or "").strip()
    last = str(getattr(candidate, "last_name", "") or "").strip()
    display = f"{first} {last}".strip() or None
    stage = str(getattr(candidate, "stage", "") or "").strip() or None
    status = str(getattr(candidate, "status", "") or "").strip() or None

    raw_reasons = getattr(candidate, "status_reason", None)
    reason_list = (
        [str(x).strip() for x in raw_reasons if str(x).strip()]
        if isinstance(raw_reasons, list)
        else []
    )

    source_lead_id = str(extra.get("source_lead_id") or "").strip() or None
    continuity = extra.get("lead_continuity_v1")
    intake_status: Optional[str] = None
    intake_reason: Optional[str] = None
    if isinstance(continuity, Mapping):
        ir = continuity.get("intake_resolution_v1")
        if isinstance(ir, Mapping):
            intake_status = str(ir.get("status") or "").strip() or None
            intake_reason = str(ir.get("reason_code") or "").strip() or None
        if not source_lead_id:
            source_lead_id = str(continuity.get("source_lead_id") or "").strip() or None

    intakes = origin.get("lead_duplicate_intakes_v1")
    intake_count = 0
    last_at: Optional[str] = None
    if isinstance(intakes, list):
        kept = [row for row in intakes if isinstance(row, Mapping)]
        intake_count = len(kept)
        if kept:
            last_at = str(kept[-1].get("ingested_at") or "").strip() or None

    reason = reason_list[0] if reason_list else intake_reason
    stage_l = (stage or "").lower()
    outcome = None
    if stage_l in {"rejected", "declined", "employed"}:
        outcome = stage_l
    elif intake_status in {"rejected", "converted", "pooled"}:
        outcome = intake_status

    summary: dict[str, Any] = {
        "candidate_created": True,
        "candidate_id": cid,
    }
    if display:
        summary["display_name"] = display
    if stage:
        summary["stage"] = stage
    if status:
        summary["status"] = status
    if reason:
        summary["reason"] = reason
    if reason_list:
        summary["status_reason"] = reason_list
    if intake_status:
        summary["intake_status"] = intake_status
    if intake_reason:
        summary["intake_reason"] = intake_reason
    if source_lead_id:
        summary["source_lead_id"] = source_lead_id
    if intake_count:
        summary["previous_duplicate_intakes"] = intake_count
    if last_at:
        summary["last_duplicate_intake_at"] = last_at
    if outcome:
        summary["outcome"] = outcome
    return summary


def stamp_duplicate_prior_v1(normalized: dict[str, Any], candidate: Any) -> None:
    """Durable prior-candidate snapshot (survives duplicate_match_v1 clear)."""
    prior = build_duplicate_prior_summary(candidate)
    if not prior:
        return
    normalized["duplicate_prior_v1"] = dict(prior)


def preserve_duplicate_prior_from_match(normalized: dict[str, Any], match_block: Any) -> None:
    """Copy ``match.prior`` onto ``duplicate_prior_v1`` before the match stamp is dropped."""
    if not isinstance(normalized, dict) or not isinstance(match_block, Mapping):
        return
    existing = normalized.get("duplicate_prior_v1")
    if isinstance(existing, Mapping) and existing.get("candidate_id"):
        return
    prior = match_block.get("prior")
    if isinstance(prior, Mapping) and prior.get("candidate_id"):
        normalized["duplicate_prior_v1"] = dict(prior)


def stamp_duplicate_review_normalized_v1(
    normalized: dict[str, Any],
    *,
    match: LeadDuplicateMatch,
    error_code: str,
) -> None:
    """Persist duplicate-review hints for UI / re-process (no merge)."""
    suggested: Optional[str] = None
    if match.candidate is not None:
        suggested = str(match.candidate.id)
    stamp: dict[str, Any] = {
        "level": match.level,
        "suggested_candidate_id": suggested,
        "reasons": list(match.reasons),
        "hr_blockers": list(match.hr_blockers),
        "error_code": error_code,
        "stamped_at": datetime.now(timezone.utc).isoformat(),
    }
    prior = build_duplicate_prior_summary(match.candidate)
    if prior:
        stamp["prior"] = prior
        normalized["duplicate_prior_v1"] = dict(prior)
    normalized["duplicate_match_v1"] = stamp


async def record_exact_duplicate_lead_intake(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    candidate: Candidate,
    normalized: dict[str, Any],
    match_reasons: list[str],
) -> None:
    """Append structured intake + notify (operational trail on existing candidate)."""
    origin = dict(candidate.origin or {}) if isinstance(candidate.origin, dict) else {}
    intakes = origin.get("lead_duplicate_intakes_v1")
    if not isinstance(intakes, list):
        intakes = []

    vacancy_interest: Optional[str] = None
    lid = str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None
    cid = str(candidate.vacancy_id).strip() if getattr(candidate, "vacancy_id", None) else None
    if lid and lid != cid:
        vacancy_interest = lid

    intakes.append(
        {
            "lead_id": str(lead.id),
            "source": lead.source,
            "external_id": lead.external_id,
            "ad_id": getattr(lead, "ad_id", None),
            "vacancy_id": lid,
            "vacancy_interest_vacancy_id": vacancy_interest,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "match_reasons": list(match_reasons),
            "campaign": normalized.get("campaign") or normalized.get("utm_campaign"),
            "recruiter_id": getattr(candidate, "recruiter_id", None),
            "contact": {
                "email": normalized.get("email"),
                "phone": normalized.get("phone"),
            },
        }
    )
    origin["lead_duplicate_intakes_v1"] = intakes[-120:]
    candidate.origin = origin

    payload = {
        "lead_id": str(lead.id),
        "candidate_id": str(candidate.id),
        "source": lead.source,
        "vacancy_id": lid,
        "match_reasons": list(match_reasons),
    }
    recruiter_id = getattr(candidate, "recruiter_id", None)
    audience_roles = [UserRole.administrator, UserRole.employee]
    user_ids = [str(recruiter_id)] if recruiter_id else []
    await events.emit_event(
        db,
        tenant_id=tenant_id,
        event_type="candidate.duplicate_lead_intake",
        payload=payload,
        entity_type="candidate",
        entity_id=str(candidate.id),
        audience=EventAudience(roles=audience_roles, user_ids=user_ids),
    )
