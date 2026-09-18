"""Absence payload for GET /candidates/{id} and recreate-from-application.

When a candidate is soft-deleted, Recruitment Applications (Отклики / Lead.candidate_id)
can remain. The card must tell the operator the dossier is gone and, if an
application still exists, offer an explicit recreate action.
"""

from __future__ import annotations

from typing import Any, Dict, NoReturn, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication

CODE_NOT_FOUND = "candidate_not_found"
CODE_DELETED = "candidate_deleted"
CODE_EXISTS = "candidate_exists"
CODE_NO_APPLICATION = "no_surviving_application"


def _absence_payload(
    *,
    code: str,
    message: str,
    application_id: Optional[str] = None,
    can_recreate: bool = False,
) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "application_id": application_id,
        "can_recreate": bool(can_recreate and application_id),
    }


def raise_candidate_absence(payload: Dict[str, Any], *, status_code: int = 404) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=payload)


async def find_surviving_application_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> Optional[str]:
    """Return the Отклик id (Lead.id) still pointing at this candidate, if any."""
    cid = str(candidate_id).strip()
    tid = str(tenant_id).strip()
    if not cid or not tid:
        return None

    lead_id = (
        await db.execute(
            select(Lead.id)
            .where(Lead.tenant_id == tid, Lead.candidate_id == cid)
            .order_by(Lead.created_at.desc(), Lead.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if lead_id:
        return str(lead_id)

    app_row = (
        await db.execute(
            select(RecruitmentApplication)
            .where(
                RecruitmentApplication.tenant_id == tid,
                RecruitmentApplication.candidate_id == cid,
            )
            .order_by(
                RecruitmentApplication.applied_at.desc(),
                RecruitmentApplication.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if app_row is None:
        return None
    lid = str(getattr(app_row, "lead_id", None) or "").strip()
    return lid or None


async def load_tenant_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> Optional[Candidate]:
    """Tenant-scoped lookup including soft-deleted rows (no visibility/ACL)."""
    res = await db.execute(
        select(Candidate).where(
            Candidate.id == str(candidate_id),
            Candidate.tenant_id == str(tenant_id),
        )
    )
    return res.scalar_one_or_none()


async def describe_candidate_absence(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> Dict[str, Any]:
    row = await load_tenant_candidate(db, tenant_id=tenant_id, candidate_id=candidate_id)
    if row is None:
        return _absence_payload(
            code=CODE_NOT_FOUND,
            message="Candidate not found",
        )
    if getattr(row, "deleted_at", None) is None:
        return _absence_payload(
            code=CODE_NOT_FOUND,
            message="Candidate not found",
        )
    application_id = await find_surviving_application_id(
        db, tenant_id=tenant_id, candidate_id=str(candidate_id)
    )
    return _absence_payload(
        code=CODE_DELETED,
        message="Candidate was deleted",
        application_id=application_id,
        can_recreate=bool(application_id),
    )


def _payload_from_deleted_and_lead(*, deleted: Candidate, lead: Lead) -> Dict[str, Any]:
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    first = str(norm.get("first_name") or deleted.first_name or "Candidate").strip() or "Candidate"
    last = str(norm.get("last_name") or deleted.last_name or "Restored").strip() or "Restored"
    email = str(norm.get("email") or deleted.email or "").strip() or None
    phone = str(norm.get("phone") or deleted.phone or "").strip() or None
    vacancy_id = str(getattr(lead, "vacancy_id", None) or deleted.vacancy_id or "").strip() or None
    company_id = str(getattr(lead, "company_id", None) or deleted.company_id or "").strip() or None
    own_company_id = (
        str(getattr(lead, "own_company_id", None) or deleted.own_company_id or "").strip() or None
    )
    source = str(getattr(lead, "source", None) or deleted.source or "meta").strip() or "meta"
    payload: Dict[str, Any] = {
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": phone,
        "phone_country_code": deleted.phone_country_code,
        "company_id": company_id,
        "vacancy_id": vacancy_id,
        "own_company_id": own_company_id,
        "source": source,
        "manager": deleted.manager,
        "recruiter_id": deleted.recruiter_id,
    }
    personal = deleted._get_personal_data()
    if personal:
        payload["personal_data"] = personal
    contacts = deleted._get_contacts()
    if contacts:
        payload["contacts"] = contacts
    extra = deleted._get_extra()
    if extra:
        payload["extra"] = extra
    origin = getattr(deleted, "origin", None)
    if isinstance(origin, dict) and origin:
        payload["origin"] = origin
    elif isinstance(norm, dict) and norm:
        payload["origin"] = {source: norm}
    return payload


async def recreate_candidate_from_application(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new live candidate from a surviving Отклик and re-link it.

    The deleted dossier stays deleted. The application (Lead + intent row)
    is re-pointed at the new candidate id.
    """
    from backend.app.modules.leads.lead_candidate_conversion import (
        create_candidate_from_lead_conversion,
        ensure_recruitment_application_for_converted_lead,
    )

    tid = str(tenant_id).strip()
    old_id = str(candidate_id).strip()
    deleted = await load_tenant_candidate(db, tenant_id=tid, candidate_id=old_id)
    if deleted is None:
        raise_candidate_absence(
            _absence_payload(code=CODE_NOT_FOUND, message="Candidate not found")
        )
    if getattr(deleted, "deleted_at", None) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_absence_payload(
                code=CODE_EXISTS,
                message="Candidate already exists",
            ),
        )

    application_id = await find_surviving_application_id(
        db, tenant_id=tid, candidate_id=old_id
    )
    if not application_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_absence_payload(
                code=CODE_NO_APPLICATION,
                message="No surviving application to recreate from",
            ),
        )

    lead = (
        await db.execute(select(Lead).where(Lead.id == application_id, Lead.tenant_id == tid))
    ).scalar_one_or_none()
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_absence_payload(
                code=CODE_NO_APPLICATION,
                message="No surviving application to recreate from",
            ),
        )

    payload = _payload_from_deleted_and_lead(deleted=deleted, lead=lead)
    source = str(payload.get("source") or getattr(lead, "source", None) or "meta")
    created = await create_candidate_from_lead_conversion(
        db,
        tenant_id=tid,
        lead=lead,
        candidate_payload=payload,
        source_channel=source,
        duplicate_match_level="none",
        conversion_reason="recreate_from_deleted_application",
    )
    new_id = str(created.id)

    await db.execute(
        update(Lead)
        .where(Lead.tenant_id == tid, Lead.candidate_id == old_id)
        .values(candidate_id=new_id)
    )
    await db.execute(
        update(RecruitmentApplication)
        .where(
            RecruitmentApplication.tenant_id == tid,
            RecruitmentApplication.candidate_id == old_id,
        )
        .values(candidate_id=new_id)
    )
    await ensure_recruitment_application_for_converted_lead(
        db,
        tenant_id=tid,
        lead=lead,
        candidate=created,
        vacancy_id=payload.get("vacancy_id"),
        recruiter_id=payload.get("recruiter_id"),
        source=source,
    )
    await db.commit()
    _ = actor_id  # reserved for audit; conversion already emits candidate_created
    return {"candidate_id": new_id, "application_id": application_id}
