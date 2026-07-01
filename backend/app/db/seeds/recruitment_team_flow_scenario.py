"""
Dev/Test seed: tenant + company + admin/supervisor/2 recruiters/HR + vacancy + 4 candidates + 1 workforce row (HR-readonly fixture).

Idempotent (stable UUIDs via uuid5). Candidates tagged with email `*@scenario-lead.local` for optional reset.

Run (from repo root, HostFlow as cwd):

    PYTHONPATH=. python3 backend/scripts/seed_recruitment_team_scenario.py

Environment:

    RECRUIT_FLOW_SCENARIO_PASSWORD   (default: RecruitFlow123!)
    RECRUIT_FLOW_SCENARIO_TENANT_ID    (default: fixed demo UUID below)
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password
from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.recruiter_availability_state import RecruiterAvailabilityStateRow
from backend.app.models.tenant import Tenant, TenantLicense, TenantStatus, TenantType
from backend.app.models.user import Role as UserRole, User
from backend.app.models.vacancy import Vacancy
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.constants.spa_paths import CANDIDATES
from backend.app.services.workforce_employees import ensure_hr_profiles_bundle

# Namespace for deterministic ids (v5)
_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace — arbitrary fixed

DEFAULT_SCENARIO_TENANT_ID = "22222222-2222-2222-2222-222222222222"

SCENARIO_SLUG = "recruit-flow-scenario-2222"
SCENARIO_NAME = "Recruitment Flow Scenario (seed 2222)"
SOURCE_TAG = "recruit_flow_scenario_v1"


def _u(name: str) -> str:
    return str(uuid.uuid5(_NS, f"hostflow:{DEFAULT_SCENARIO_TENANT_ID}:{name}"))


@dataclass(frozen=True)
class ScenarioEmails:
    admin: str = "scenario.admin@recruit-flow.local"
    supervisor: str = "scenario.supervisor@recruit-flow.local"
    recruiter_a: str = "scenario.recruiter-a@recruit-flow.local"
    recruiter_b: str = "scenario.recruiter-b@recruit-flow.local"
    hr: str = "scenario.hr@recruit-flow.local"


EMAILS = ScenarioEmails()

COMPANY_ID = _u("company")
VACANCY_ID = _u("vacancy")

USER_IDS = {
    "admin": _u("user:admin"),
    "supervisor": _u("user:supervisor"),
    "recruiter_a": _u("user:recruiter_a"),
    "recruiter_b": _u("user:recruiter_b"),
    "hr": _u("user:hr"),
}

CANDIDATE_IDS = {
    "auto_assigned": _u("candidate:auto"),
    "unassigned": _u("candidate:unassigned"),
    "claimed": _u("candidate:claimed"),
    "hr_readonly": _u("candidate:hr_readonly"),
}

WORKFORCE_IDS = {
    "hr_readonly": _u("workforce:hr_readonly"),
}


async def _set_rls_tenant(session: AsyncSession, tenant_id: str) -> None:
    try:
        await session.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": tenant_id})
    except Exception:
        pass


async def _ensure_membership(session: AsyncSession, *, user_id: str, tenant_id: str, role: str) -> None:
    await session.execute(
        sa.text(
            """
            INSERT INTO user_memberships (id, user_id, tenant_id, role)
            VALUES (:id, :user_id, :tenant_id, :role)
            ON CONFLICT(user_id, tenant_id)
            DO UPDATE SET role = excluded.role
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
        },
    )


async def _ensure_user_company_access(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    company_id: str,
    can_edit: bool,
) -> None:
    await session.execute(
        sa.text(
            """
            INSERT INTO user_company_access (id, tenant_id, user_id, company_id, can_edit)
            VALUES (:id, :tenant_id, :user_id, :company_id, :can_edit)
            ON CONFLICT(tenant_id, user_id, company_id)
            DO UPDATE SET can_edit = excluded.can_edit
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "company_id": company_id,
            "can_edit": can_edit,
        },
    )


async def _upsert_availability(session: AsyncSession, *, tenant_id: str, user_id: str, state: str) -> None:
    row = await session.scalar(
        select(RecruiterAvailabilityStateRow).where(
            RecruiterAvailabilityStateRow.tenant_id == tenant_id,
            RecruiterAvailabilityStateRow.user_id == user_id,
        )
    )
    now = datetime.now(timezone.utc)
    if row is None:
        session.add(
            RecruiterAvailabilityStateRow(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                state=state,
                updated_at=now,
            )
        )
    else:
        row.state = state
        row.updated_at = now


async def reset_scenario_candidates(session: AsyncSession, *, tenant_id: str) -> int:
    """Delete seed candidates only (by email domain), for re-run with fresh leads."""
    await _set_rls_tenant(session, tenant_id)
    r = await session.execute(
        sa.text("DELETE FROM candidates WHERE tenant_id = :tid AND email LIKE :pat"),
        {"tid": tenant_id, "pat": "%@scenario-lead.local"},
    )
    await session.commit()
    return r.rowcount or 0


async def run_recruitment_team_flow_scenario(
    session: AsyncSession,
    *,
    password: str | None = None,
    tenant_id: str | None = None,
    reset_candidates: bool = False,
) -> dict[str, Any]:
    """
    Create or update the full scenario. Commits once at end.
    """
    tid = (tenant_id or os.environ.get("RECRUIT_FLOW_SCENARIO_TENANT_ID") or DEFAULT_SCENARIO_TENANT_ID).strip()
    pwd = (password or os.environ.get("RECRUIT_FLOW_SCENARIO_PASSWORD") or "RecruitFlow123!").strip()

    await _set_rls_tenant(session, tid)
    ph = hash_password(pwd)
    now_naive = datetime.utcnow()

    if reset_candidates:
        await session.execute(
            sa.text("DELETE FROM candidates WHERE tenant_id = :tid AND email LIKE :pat"),
            {"tid": tid, "pat": "%@scenario-lead.local"},
        )

    # --- Tenant ---
    existing_tenant = await session.get(Tenant, tid)
    api_key = str(uuid.uuid5(_NS, f"api:{tid}")).replace("-", "")[:64]
    if existing_tenant is None:
        session.add(
            Tenant(
                id=tid,
                name=SCENARIO_NAME,
                slug=SCENARIO_SLUG,
                api_key=api_key,
                is_active=True,
                settings={},
                type=TenantType.agency,
                status=TenantStatus.active,
            )
        )
    else:
        existing_tenant.name = SCENARIO_NAME
        existing_tenant.slug = SCENARIO_SLUG
        existing_tenant.is_active = True
        existing_tenant.status = TenantStatus.active

    await session.flush()

    # --- License (generous dev caps) ---
    lic = await session.scalar(select(TenantLicense).where(TenantLicense.tenant_id == tid))
    if lic is None:
        session.add(
            TenantLicense(
                id=str(uuid.uuid4()),
                tenant_id=tid,
                plan="scenario_dev",
                max_recruiters=50,
                max_supervisors=20,
                max_fleet_managers=20,
                max_client_managers=20,
                max_viewers=50,
                max_storage_gb=100,
                max_companies=100,
                max_candidates_active=500,
                max_vacancies_active=200,
                max_documents=10000,
                max_public_portal_links=100,
            )
        )
    else:
        lic.plan = lic.plan or "scenario_dev"
        lic.max_recruiters = max(lic.max_recruiters, 50)
        lic.max_supervisors = max(lic.max_supervisors, 20)
        lic.max_candidates_active = max(lic.max_candidates_active, 500)
        lic.max_vacancies_active = max(lic.max_vacancies_active, 200)
        lic.max_companies = max(lic.max_companies, 100)

    async def ensure_user(
        preferred_id: str,
        email: str,
        role: UserRole,
        full_name: str,
        *,
        supervisor_id: str | None = None,
    ) -> User:
        u = await session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if u is None:
            u = User(
                id=preferred_id,
                email=email,
                password_hash=ph,
                role=role,
                tenant_id=tid,
                is_active=True,
                full_name=full_name,
                short_id=None,
                supervisor_id=supervisor_id,
            )
            session.add(u)
        else:
            u.password_hash = ph
            u.role = role
            u.tenant_id = tid
            u.is_active = True
            u.full_name = full_name
            u.supervisor_id = supervisor_id
        return u

    sup = await ensure_user(
        USER_IDS["supervisor"],
        EMAILS.supervisor,
        UserRole.supervisor,
        "Scenario Supervisor",
    )
    adm = await ensure_user(
        USER_IDS["admin"],
        EMAILS.admin,
        UserRole.administrator,
        "Scenario Admin",
    )
    rec_a = await ensure_user(
        USER_IDS["recruiter_a"],
        EMAILS.recruiter_a,
        UserRole.recruiter,
        "Scenario Recruiter A",
        supervisor_id=sup.id,
    )
    rec_b = await ensure_user(
        USER_IDS["recruiter_b"],
        EMAILS.recruiter_b,
        UserRole.recruiter,
        "Scenario Recruiter B",
        supervisor_id=sup.id,
    )
    hr = await ensure_user(
        USER_IDS["hr"],
        EMAILS.hr,
        UserRole.hr_officer,
        "Scenario HR Officer",
    )

    await session.flush()

    role_by_user = {
        adm.id: "administrator",
        sup.id: "supervisor",
        rec_a.id: "recruiter",
        rec_b.id: "recruiter",
        hr.id: "hr_officer",
    }
    for uid, r in role_by_user.items():
        await _ensure_membership(session, user_id=uid, tenant_id=tid, role=r)

    # --- Company ---
    co = await session.get(Company, COMPANY_ID)
    if co is None:
        session.add(
            Company(
                id=COMPANY_ID,
                tenant_id=tid,
                name="Scenario Logistics Sp. z o.o.",
                owner_user_id=adm.id,
                manager_user_id=sup.id,
            )
        )
    else:
        co.tenant_id = tid
        co.name = "Scenario Logistics Sp. z o.o."
        co.owner_user_id = adm.id
        co.manager_user_id = sup.id

    await session.flush()

    for uid in (adm.id, sup.id, rec_a.id, rec_b.id, hr.id):
        await _ensure_user_company_access(session, tenant_id=tid, user_id=uid, company_id=COMPANY_ID, can_edit=True)

    # --- Vacancy ---
    vac = await session.get(Vacancy, VACANCY_ID)
    if vac is None:
        session.add(
            Vacancy(
                id=VACANCY_ID,
                tenant_id=tid,
                company_id=COMPANY_ID,
                title="Scenario — Long-haul driver",
                description="Seed vacancy for recruitment flow manual testing.",
                manager=sup.id,
                status="open",
                is_active=True,
            )
        )
    else:
        vac.tenant_id = tid
        vac.company_id = COMPANY_ID
        vac.title = "Scenario — Long-haul driver"
        vac.manager = sup.id
        vac.status = "open"
        vac.is_active = True

    await session.flush()

    # --- Availability: A = available, B = paused ---
    await _upsert_availability(session, tenant_id=tid, user_id=rec_a.id, state="available")
    await _upsert_availability(session, tenant_id=tid, user_id=rec_b.id, state="paused")

    # --- Candidates ---
    async def upsert_candidate(
        cid: str,
        *,
        first: str,
        last: str,
        email: str,
        assignment_state: str,
        manager_uid: str | None,
        recruiter_uid: str | None,
    ) -> None:
        c = await session.get(Candidate, cid)
        common = dict(
            tenant_id=tid,
            first_name=first,
            last_name=last,
            email=email,
            company_id=COMPANY_ID,
            vacancy_id=VACANCY_ID,
            stage="new",
            source=SOURCE_TAG,
            assignment_state=assignment_state,
            manager=manager_uid,
            recruiter_id=recruiter_uid,
            created_at=now_naive,
            updated_at=now_naive,
        )
        if c is None:
            session.add(Candidate(id=cid, **common))
        else:
            for k, v in common.items():
                setattr(c, k, v)

    await upsert_candidate(
        CANDIDATE_IDS["auto_assigned"],
        first="Auto",
        last="Assigned Lead",
        email="auto@scenario-lead.local",
        assignment_state="assigned",
        manager_uid=rec_a.id,
        recruiter_uid=rec_a.id,
    )
    await upsert_candidate(
        CANDIDATE_IDS["unassigned"],
        first="Queue",
        last="Unassigned Lead",
        email="unassigned@scenario-lead.local",
        assignment_state="unassigned",
        manager_uid=None,
        recruiter_uid=None,
    )
    await upsert_candidate(
        CANDIDATE_IDS["claimed"],
        first="Manual",
        last="Claimed Lead",
        email="claimed@scenario-lead.local",
        assignment_state="claimed",
        manager_uid=rec_b.id,
        recruiter_uid=rec_b.id,
    )
    await upsert_candidate(
        CANDIDATE_IDS["hr_readonly"],
        first="HR",
        last="Readonly Lead",
        email="hr-readonly@scenario-lead.local",
        assignment_state="assigned",
        manager_uid=rec_a.id,
        recruiter_uid=rec_a.id,
    )
    await session.flush()

    wf_id = WORKFORCE_IDS["hr_readonly"]
    wf = await session.get(WorkforceEmployee, wf_id)
    if wf is None:
        wf = WorkforceEmployee(
            id=wf_id,
            tenant_id=tid,
            candidate_id=CANDIDATE_IDS["hr_readonly"],
            company_id=COMPANY_ID,
            vacancy_id=VACANCY_ID,
            recruiter_user_id=rec_a.id,
            display_name="Scenario HR Readonly Hiree",
            status="onboarding",
            notes="recruit_flow_scenario: workforce stub for e2e readonly",
        )
        session.add(wf)
    else:
        wf.tenant_id = tid
        wf.candidate_id = CANDIDATE_IDS["hr_readonly"]
        wf.company_id = COMPANY_ID
        wf.vacancy_id = VACANCY_ID
        wf.recruiter_user_id = rec_a.id
        wf.display_name = "Scenario HR Readonly Hiree"
        wf.status = "onboarding"
        wf.notes = "recruit_flow_scenario: workforce stub for e2e readonly"
    await session.flush()
    await ensure_hr_profiles_bundle(session, tid, wf_id)

    await session.commit()

    return {
        "tenant_id": tid,
        "company_id": COMPANY_ID,
        "vacancy_id": VACANCY_ID,
        "password": pwd,
        "users": {
            "admin": {"id": adm.id, "email": EMAILS.admin},
            "supervisor": {"id": sup.id, "email": EMAILS.supervisor},
            "recruiter_a": {"id": rec_a.id, "email": EMAILS.recruiter_a, "availability": "available"},
            "recruiter_b": {"id": rec_b.id, "email": EMAILS.recruiter_b, "availability": "paused"},
            "hr_officer": {"id": hr.id, "email": EMAILS.hr},
        },
        "candidates": {
            "auto_assigned": CANDIDATE_IDS["auto_assigned"],
            "unassigned": CANDIDATE_IDS["unassigned"],
            "claimed": CANDIDATE_IDS["claimed"],
            "hr_readonly": CANDIDATE_IDS["hr_readonly"],
        },
        "workforce": {
            "hr_readonly": WORKFORCE_IDS["hr_readonly"],
        },
        "ui": {
            "candidates_unassigned_filter": f"{CANDIDATES}?assignment_state=unassigned",
            "login_hint": "Log in as scenario.recruiter-a@recruit-flow.local or scenario.supervisor@recruit-flow.local",
        },
    }


__all__ = [
    "run_recruitment_team_flow_scenario",
    "reset_scenario_candidates",
    "DEFAULT_SCENARIO_TENANT_ID",
    "EMAILS",
    "SOURCE_TAG",
    "WORKFORCE_IDS",
]
