"""Manual lead re-routing flow.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
step 7/N): ``reroute_lead_manual`` — admin-driven re-assignment of a lead
to a different vacancy / recruiter / company, with validation, candidate
creation hand-off, audit, and event emission.

Re-exported via ``service/__init__.py`` so callers (router endpoint /
tests) keep using ``service.reroute_lead_manual``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.models import Vacancy
from backend.app.modules.leads import crud
from backend.app.modules.leads.recruiter_validation import validate_tenant_recruiter_id

from ._helpers import (
    LeadProcessingError,
    MetaLeadResult,
    _load_settings,
    _rule_recruiter_id_from_normalized,
    _validate_company_id,
    _validate_recruiter_id,
)


async def reroute_lead_manual(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    vacancy_id: Optional[str],
    company_id: Optional[str],
    force_process: bool,
) -> MetaLeadResult:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if not lead:
        raise LeadProcessingError("not_found", "LEAD_NOT_FOUND")

    settings_row = await _load_settings(db, tenant_id)
    fallback_recruiter_hint = settings_row.fallback_recruiter_id

    target_company_id = company_id or lead.company_id
    target_company_id = await _validate_company_id(db, tenant_id, target_company_id)
    if not target_company_id:
        raise LeadProcessingError("needs_routing", "COMPANY_NOT_RESOLVED")

    target_vacancy: Optional[Vacancy] = None
    vacancy_candidate = vacancy_id or lead.vacancy_id
    if vacancy_candidate:
        target_vacancy = await crud.resolve_vacancy_by_id(
            db,
            tenant_id,
            str(vacancy_candidate),
            scoped_own_company_id=str(getattr(lead, "own_company_id", None) or "").strip()
            or None,
        )

    normalized = dict(lead.normalized or {})
    normalized["company_id"] = target_company_id
    if target_vacancy:
        normalized["vacancy_id"] = str(target_vacancy.id)
        normalized["resolved_vacancy_id"] = target_vacancy.id
    else:
        normalized["resolved_vacancy_id"] = None

    lead.company_id = target_company_id
    lead.vacancy_id = str(target_vacancy.id) if target_vacancy else None
    lead.normalized = normalized

    email = normalized.get("email")
    phone = normalized.get("phone")
    now_marker = datetime.now(timezone.utc)

    if not email and not phone:
        fields = normalized.get("raw_field_names") or []
        diagnostic = "NO_CONTACTS"
        if fields:
            diagnostic = f"NO_CONTACTS (fields={'/'.join(fields)})"
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=diagnostic,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="failed",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            error=diagnostic,
        )

    if not target_vacancy and not force_process:
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=None,
            normalized=normalized,
            error="VACANCY_NOT_RESOLVED",
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=None,
            candidate_id=None,
            recruiter_id=None,
            error="VACANCY_NOT_RESOLVED",
        )

    duplicate = await crud.find_duplicate_candidate(
        db,
        tenant_id=tenant_id,
        company_id=target_company_id,
        email=email,
        phone=phone,
    )
    if duplicate:
        duplicate_recruiter_id = getattr(duplicate, "recruiter_id", None)
        await crud.update_lead(
            db,
            lead,
            status="duplicated",
            candidate_id=str(duplicate.id),
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="duplicated",
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            candidate_id=str(duplicate.id),
            recruiter_id=duplicate_recruiter_id,
            error=None,
        )

    if not force_process:
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            error=None,
        )

    extra_fields: Dict[str, Any] = {}
    preferred_contact = normalized.get("preferred_contact")
    if isinstance(preferred_contact, str) and preferred_contact.strip():
        extra_fields["preferred_contact"] = preferred_contact.strip()
    in_poland_value = normalized.get("in_poland")
    if isinstance(in_poland_value, bool):
        extra_fields["in_poland"] = in_poland_value
    elif isinstance(in_poland_value, str):
        lowered = in_poland_value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            extra_fields["in_poland"] = True
        elif lowered in {"false", "no", "0"}:
            extra_fields["in_poland"] = False
    poland_basis = normalized.get("poland_stay_basis")
    if isinstance(poland_basis, str) and poland_basis.strip():
        extra_fields["poland_stay_basis"] = poland_basis.strip()
    # Handle driving experience - save both raw string and normalized number
    driving_experience = normalized.get("driving_experience_in_europe")
    if isinstance(driving_experience, str) and driving_experience.strip():
        extra_fields["driving_experience_in_europe"] = driving_experience.strip()
    # Also save normalized number of years if available (опыт по ЕС)
    experience_eu_years = normalized.get("experience_eu_years")
    if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
        extra_fields["experience_eu_years"] = experience_eu_years

    # Capture values BEFORE create_candidate_full().
    # That function may internally commit/flush which can expire ORM instances.
    # Accessing expired attributes later can cause MissingGreenlet in async SQLAlchemy.
    vacancy_id_for_lead: Optional[str] = str(target_vacancy.id) if target_vacancy else None
    vacancy_recruiter_id: Optional[str] = getattr(target_vacancy, "recruiter_id", None) if target_vacancy else None
    own_company_id_for_lead: Optional[str] = getattr(lead, "own_company_id", None)

    candidate_payload: Dict[str, Any] = {
        "first_name": (normalized.get("first_name") or "Meta").strip() or "Meta",
        "last_name": (normalized.get("last_name") or normalized.get("full_name") or "Lead").strip() or "Lead",
        "email": email,
        "phone": phone,
        "phone_country_code": normalized.get("phone_country_code"),
        "own_company_id": own_company_id_for_lead,
        "company_id": target_company_id,
        "vacancy_id": str(target_vacancy.id) if target_vacancy else None,
        "contacts": {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "phone_country_code": normalized.get("phone_country_code"),
            }.items()
            if value
        },
        "source": "meta",
        "origin": {
            "meta": normalized,
        },
    }
    if extra_fields:
        candidate_payload["extra"] = extra_fields

    try:
        candidate = await create_candidate_full(
            db=db,
            tenant_id=tenant_id,
            payload=candidate_payload,
            actor_id=None,
            acl=None,
        )
    except HTTPException as exc:
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc.detail),
            last_routed_at=now_marker,
        )
        await db.commit()
        raise
    except Exception as exc:  # pragma: no cover
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc),
            last_routed_at=now_marker,
        )
        await db.commit()
        raise

    candidate_id_for_lead: Optional[str] = None
    identity = sa_inspect(candidate).identity
    if identity and identity[0]:
        candidate_id_for_lead = str(identity[0])
    if not candidate_id_for_lead:
        # Defensive fallback: candidate primary key must exist.
        raise LeadProcessingError("candidate_id_missing", "CANDIDATE_ID_MISSING_AFTER_CREATE")

    stamp_rid = _rule_recruiter_id_from_normalized(normalized)
    rule_rid = await validate_tenant_recruiter_id(db, tenant_id, stamp_rid) if stamp_rid else None
    recruiter_id = vacancy_recruiter_id
    if rule_rid:
        candidate.recruiter_id = rule_rid
        recruiter_id = rule_rid
        await db.flush()
    if not recruiter_id:
        # If we don't have vacancy/recruiter from vacancy, fall back to the tenant-level hint.
        # Avoid reading candidate.recruiter_id here: create_candidate_full() may have expired it.
        fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)
        if fallback_recruiter:
            candidate.recruiter_id = fallback_recruiter
            recruiter_id = fallback_recruiter
            await db.flush()

    if recruiter_id and not getattr(candidate, "manager", None):
        candidate.manager = recruiter_id
        await db.flush()

    await crud.update_lead(
        db,
        lead,
        status="processed",
        candidate_id=candidate_id_for_lead,
        vacancy_id=vacancy_id_for_lead,
        normalized=normalized,
        error=None,
        last_routed_at=now_marker,
    )
    await db.commit()

    return MetaLeadResult(
        lead_id=lead.id,
        status="processed",
        vacancy_id=vacancy_id_for_lead,
        candidate_id=candidate_id_for_lead,
        recruiter_id=recruiter_id,
        error=None,
    )
