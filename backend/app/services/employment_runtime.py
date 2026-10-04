"""Open Employment(preparing) when an internal_hr handoff is accepted.

This module does not run the HR Legal Eligibility Gate, the kwestionariusz,
requirements, or Ready to Start. It does not move an Employment to active.
A contract card is not created here, and a contract card does not create
an Employment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_handoff_snapshot import CandidateHandoffSnapshot
from backend.app.models.hr_employment import Employment
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.workforce_employees import find_employee_by_candidate

_PREPARING = "preparing"


def _text(value: Any) -> str | None:
    raw = str(value or "").strip()
    return raw or None


async def _employment_for_handoff(
    db: AsyncSession,
    tenant_id: str,
    handoff_id: str,
) -> Employment | None:
    res = await db.execute(
        select(Employment).where(
            Employment.tenant_id == tenant_id,
            Employment.handoff_id == handoff_id,
        )
    )
    return res.scalar_one_or_none()


async def _handoff_snapshot_payload(
    db: AsyncSession,
    handoff_id: str,
) -> dict[str, Any] | None:
    """The snapshot already stored for this handoff. No new person or evidence copy."""

    res = await db.execute(
        select(CandidateHandoffSnapshot.payload).where(
            CandidateHandoffSnapshot.handoff_id == handoff_id
        )
    )
    payload = res.scalar_one_or_none()
    if isinstance(payload, dict):
        return dict(payload)
    return None


async def open_preparing_employment_for_accepted_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    handoff: CandidateHandoff,
    candidate: Candidate,
    employee: WorkforceEmployee | None = None,
) -> Employment | None:
    """One new preparing Employment for this accepted handoff.

    The Employee context must already exist for the Candidate in the tenant.
    This function does not insert a WorkforceEmployee. A second call for the
    same handoff returns the existing row and does not rewrite it. A later
    handoff for the same Employee inserts another row.
    """

    tid = str(tenant_id).strip()
    hid = str(handoff.id).strip()
    found = await _employment_for_handoff(db, tid, hid)
    if found is not None:
        return found

    if employee is None:
        employee = await find_employee_by_candidate(db, tid, str(candidate.id))
    if employee is None:
        return None

    accepted_at = getattr(handoff, "accepted_at", None)
    handoff_at = accepted_at if isinstance(accepted_at, datetime) else None
    actor = _text(getattr(handoff, "accepted_by_user_id", None)) or _text(
        getattr(handoff, "reviewed_by_user_id", None)
    )
    client_company_id = _text(getattr(handoff, "client_company_id", None)) or _text(
        getattr(candidate, "company_id", None)
    )
    row = Employment(
        id=str(uuid4()),
        tenant_id=tid,
        employee_id=str(employee.id),
        state=_PREPARING,
        client_company_id=client_company_id,
        started_on=None,
        ended_on=None,
        vacancy_id=_text(getattr(candidate, "vacancy_id", None)),
        recruiter_user_id=_text(getattr(candidate, "recruiter_id", None)),
        handoff_at=handoff_at,
        handoff_by_user_id=actor,
        handoff_id=hid,
        candidate_snapshot=await _handoff_snapshot_payload(db, hid),
    )
    db.add(row)
    await db.flush()
    return row
