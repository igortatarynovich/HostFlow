"""One-time demo seed after first own-company onboarding — fills pipeline so the dashboard is not empty."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.models import Candidate, Company, Funnel, Lead, Reminder, Tenant
from backend.app.models.reminder import ReminderStatus


def _extra_dict(extra: Any) -> dict[str, Any]:
    if isinstance(extra, dict):
        return extra
    if isinstance(extra, str):
        try:
            parsed = json.loads(extra)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def onboarding_demo_still_active(tenant: Tenant | None) -> bool:
    """True when onboarding demo was seeded and the user has not cleared it yet."""
    if tenant is None or not isinstance(tenant.settings, dict):
        return False
    ob = tenant.settings.get("onboarding")
    if not isinstance(ob, dict):
        return False
    return bool(ob.get("demo_seeded")) and not bool(ob.get("demo_data_cleared_at"))


def _is_demo_candidate_extra(extra: Any) -> bool:
    return bool(_extra_dict(extra).get("onboarding_demo"))


def _is_demo_company_extra(extra: Any) -> bool:
    return bool(_extra_dict(extra).get("onboarding_demo"))


def _is_demo_lead(*, source: str | None, payload: Any) -> bool:
    if (source or "").strip() == "onboarding_demo":
        return True
    pl = payload if isinstance(payload, dict) else _extra_dict(payload)
    return bool(pl.get("demo"))


def _extra_demo() -> str:
    return json.dumps({"onboarding_demo": True, "source": "onboarding_seed_v1"})


async def _default_funnel_id(db: AsyncSession, tenant_id: str, funnel_type: str) -> str | None:
    row = await db.execute(
        select(Funnel.id)
        .where(Funnel.tenant_id == tenant_id, Funnel.type == funnel_type, Funnel.is_default.is_(True))
        .limit(1)
    )
    fid = row.scalar_one_or_none()
    if fid:
        return str(fid)
    row2 = await db.execute(
        select(Funnel.id).where(Funnel.tenant_id == tenant_id, Funnel.type == funnel_type).order_by(Funnel.created_at.asc()).limit(1)
    )
    fid2 = row2.scalar_one_or_none()
    return str(fid2) if fid2 else None


async def _mark_demo_seeded(db: AsyncSession, tenant_id: str) -> None:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))).scalar_one_or_none()
    if tenant is None:
        return
    settings: dict[str, Any] = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    ob = dict(settings.get("onboarding") or {}) if isinstance(settings.get("onboarding"), dict) else {}
    ob["demo_seeded"] = True
    ob["demo_seed_version"] = 1
    settings["onboarding"] = ob
    tenant.settings = settings
    db.add(tenant)
    await db.flush()


async def _seed_candidates_pack(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    funnel_id: str | None,
    assignee_id: str | None,
    specs: list[dict[str, Any]],
) -> None:
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    cand_ids: list[str] = []

    for spec in specs:
        cid = str(uuid.uuid4())
        cand_ids.append(cid)
        st = spec["stage"]
        old = bool(spec.get("old"))
        base_time = now - timedelta(days=14) if old else now
        c = Candidate(
            id=cid,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            first_name=str(spec.get("first_name", "Demo")),
            last_name=str(spec.get("last_name", "Candidate")),
            stage=st,
            funnel_id=funnel_id,
            extra=_extra_demo(),
            created_at=base_time,
            updated_at=base_time,
        )
        db.add(c)

    await db.flush()

    if assignee_id:
        due = datetime.now(timezone.utc) + timedelta(days=2)
        for i, spec in enumerate(specs):
            if not spec.get("reminder"):
                continue
            cid = cand_ids[i]
            db.add(
                Reminder(
                    tenant_id=tenant_id,
                    type="onboarding_demo_followup",
                    entity_type="candidate",
                    entity_id=cid,
                    assignee_id=assignee_id,
                    due_at=due,
                    status=ReminderStatus.pending,
                    title="Follow up",
                    channel="internal",
                )
            )
    await db.flush()

    # Touch 5 "active today" (first five with reminders)
    touched = 0
    for i, spec in enumerate(specs):
        if touched >= 5:
            break
        if spec.get("reminder"):
            await db.execute(update(Candidate).where(Candidate.id == cand_ids[i]).values(updated_at=now))
            touched += 1


async def _seed_leads_pack(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    company_id: str,
    funnel_id: str | None,
    assignee_id: str | None,
    specs: list[dict[str, Any]],
) -> None:
    now_aware = datetime.now(timezone.utc)
    lead_ids: list[str] = []

    for spec in specs:
        lid = str(uuid.uuid4())
        lead_ids.append(lid)
        old = bool(spec.get("old"))
        base_time = now_aware - timedelta(days=10) if old else now_aware
        db.add(
            Lead(
                id=lid,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                lead_type="client",
                company_id=company_id,
                vacancy_id=None,
                source="onboarding_demo",
                payload={"demo": True, "company_name": spec.get("label", "Demo client")},
                normalized={"company": spec.get("label", "Demo client")},
                status="processed",
                stage=str(spec["stage"]),
                funnel_id=funnel_id,
                created_at=base_time,
            )
        )

    await db.flush()

    if assignee_id:
        due = datetime.now(timezone.utc) + timedelta(days=1)
        for i, spec in enumerate(specs):
            if not spec.get("reminder"):
                continue
            db.add(
                Reminder(
                    tenant_id=tenant_id,
                    type="onboarding_demo_followup",
                    entity_type="lead",
                    entity_id=lead_ids[i],
                    assignee_id=assignee_id,
                    due_at=due,
                    status=ReminderStatus.pending,
                    title="Follow up",
                    channel="internal",
                )
            )
    await db.flush()

    touched = 0
    for i, spec in enumerate(specs):
        if touched >= 5:
            break
        if spec.get("reminder"):
            await db.execute(
                update(Lead).where(Lead.id == lead_ids[i]).values(created_at=datetime.now(timezone.utc))
            )
            touched += 1


async def seed_onboarding_demo_if_needed(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    business_type: str,
    assignee_user_id: str | None,
) -> dict[str, Any]:
    """
    Idempotent per tenant: skips if settings.onboarding.demo_seeded is truthy.
    Returns summary counts for the onboarding "ready" screen.
    """
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))).scalar_one_or_none()
    if tenant is None:
        return {}

    settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    ob = settings.get("onboarding") if isinstance(settings.get("onboarding"), dict) else {}
    if ob.get("demo_seeded"):
        return {}

    bt = str(business_type or "agency").strip().lower()
    summary: dict[str, Any] = {"entity": "candidates", "pipeline_total": 0, "need_action": 0, "stuck": 0, "active_today": 0}

    if bt == "services":
        demo_company = Company(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Demo client (sample)",
            contacts={},
            extra={"company_role": "client", "onboarding_demo": True},
        )
        db.add(demo_company)
        await db.flush()

        fid = await _default_funnel_id(db, tenant_id, "lead")
        # 12 leads, 3 without reminders, 2 "stuck" in negotiation, rest with reminders
        specs: list[dict[str, Any]] = [
            {"stage": "new", "reminder": True, "old": False, "label": "North Logistics"},
            {"stage": "new", "reminder": True, "old": True, "label": "FastFreight"},
            {"stage": "contacted", "reminder": False, "old": False, "label": "BlueRiver"},
            {"stage": "contacted", "reminder": False, "old": False, "label": "EuroHaul"},
            {"stage": "contacted", "reminder": False, "old": False, "label": "CityBuild"},
            {"stage": "proposal", "reminder": True, "old": False, "label": "GreenMart"},
            {"stage": "proposal", "reminder": True, "old": True, "label": "SunFood"},
            {"stage": "negotiation", "reminder": True, "old": True, "label": "Stuck A"},
            {"stage": "negotiation", "reminder": True, "old": True, "label": "Stuck B"},
            {"stage": "negotiation", "reminder": True, "old": False, "label": "Mid deal"},
            {"stage": "contacted", "reminder": True, "old": False, "label": "FreshCo"},
            {"stage": "proposal", "reminder": True, "old": False, "label": "PrimeServe"},
        ]
        await _seed_leads_pack(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            company_id=str(demo_company.id),
            funnel_id=fid,
            assignee_id=assignee_user_id,
            specs=specs,
        )
        summary["entity"] = "leads"
        summary["pipeline_total"] = len(specs)
        summary["need_action"] = 3
        summary["stuck"] = 2
        summary["active_today"] = 5
    else:
        fid = await _default_funnel_id(db, tenant_id, "candidate")
        if bt == "employer":
            specs = [
                {"stage": "new", "reminder": True, "old": False, "first_name": "Anna", "last_name": "Kowalski"},
                {"stage": "new", "reminder": True, "old": True, "first_name": "Jan", "last_name": "Nowak"},
                {"stage": "questionnaire_submitted", "reminder": False, "old": False, "first_name": "Maria", "last_name": "Wiśniewska"},
                {"stage": "questionnaire_submitted", "reminder": False, "old": False, "first_name": "Piotr", "last_name": "Lewandowski"},
                {"stage": "questionnaire_submitted", "reminder": False, "old": False, "first_name": "Ewa", "last_name": "Zielińska"},
                {"stage": "docs_got", "reminder": True, "old": True, "first_name": "Stuck", "last_name": "Interview A"},
                {"stage": "docs_got", "reminder": True, "old": True, "first_name": "Stuck", "last_name": "Interview B"},
                {"stage": "employment_pending", "reminder": True, "old": False, "first_name": "Tomasz", "last_name": "Kamiński"},
                {"stage": "employment_pending", "reminder": True, "old": False, "first_name": "Katarzyna", "last_name": "Szymańska"},
                {"stage": "questionnaire_submitted", "reminder": True, "old": False, "first_name": "Michał", "last_name": "Woźniak"},
                {"stage": "docs_got", "reminder": True, "old": False, "first_name": "Agnieszka", "last_name": "Dąbrowska"},
                {"stage": "new", "reminder": True, "old": False, "first_name": "Paweł", "last_name": "Kozłowski"},
            ]
            summary["stuck"] = 2
        else:
            # agency — document queue + handoff-ready mix
            specs = [
                {"stage": "new", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Alpha"},
                {"stage": "new", "reminder": True, "old": True, "first_name": "Demo", "last_name": "Bravo"},
                {"stage": "contacted", "reminder": False, "old": False, "first_name": "No", "last_name": "Action One"},
                {"stage": "contacted", "reminder": False, "old": False, "first_name": "No", "last_name": "Action Two"},
                {"stage": "contacted", "reminder": False, "old": False, "first_name": "No", "last_name": "Action Three"},
                {"stage": "docs_wait", "reminder": True, "old": True, "first_name": "Docs", "last_name": "Stuck A"},
                {"stage": "docs_wait", "reminder": True, "old": True, "first_name": "Docs", "last_name": "Stuck B"},
                {"stage": "docs_got", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Charlie"},
                {"stage": "docs_got", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Delta"},
                {"stage": "ready_for_handoff", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Echo"},
                {"stage": "ready_for_handoff", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Foxtrot"},
                {"stage": "processing_by_client", "reminder": True, "old": False, "first_name": "Demo", "last_name": "Golf"},
            ]
            summary["stuck"] = 2

        await _seed_candidates_pack(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            funnel_id=fid,
            assignee_id=assignee_user_id,
            specs=specs,
        )
        summary["entity"] = "candidates"
        summary["pipeline_total"] = len([s for s in specs if s["stage"] not in PIPELINE_COMPLETED_STAGE_CODES])
        summary["need_action"] = 3
        summary["active_today"] = 5

    await _mark_demo_seeded(db, tenant_id)
    return summary


async def clear_onboarding_demo_data(db: AsyncSession, *, tenant_id: str) -> dict[str, int]:
    """
    Remove rows created by onboarding demo seed for this tenant.
    Idempotent: if already cleared (demo_data_cleared_at), returns zeros without deleting again.
    """
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))).scalar_one_or_none()
    if tenant is None:
        return {"reminders": 0, "leads": 0, "candidates": 0, "companies": 0}

    settings: dict[str, Any] = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    ob = dict(settings.get("onboarding") or {}) if isinstance(settings.get("onboarding"), dict) else {}
    if ob.get("demo_data_cleared_at"):
        return {"reminders": 0, "leads": 0, "candidates": 0, "companies": 0}

    cand_rows = (await db.execute(select(Candidate.id, Candidate.extra).where(Candidate.tenant_id == tenant_id))).all()
    demo_cand_ids = [str(r[0]) for r in cand_rows if _is_demo_candidate_extra(r[1])]

    lead_rows = (
        await db.execute(select(Lead.id, Lead.source, Lead.payload).where(Lead.tenant_id == tenant_id))
    ).all()
    demo_lead_ids = [str(r[0]) for r in lead_rows if _is_demo_lead(source=r[1], payload=r[2])]

    comp_rows = (await db.execute(select(Company.id, Company.extra).where(Company.tenant_id == tenant_id))).all()
    demo_company_ids = [str(r[0]) for r in comp_rows if _is_demo_company_extra(r[1])]

    n_rem = 0
    if demo_cand_ids or demo_lead_ids:
        rdel = await db.execute(
            delete(Reminder).where(
                Reminder.tenant_id == tenant_id,
                Reminder.type == "onboarding_demo_followup",
                Reminder.entity_id.in_(demo_cand_ids + demo_lead_ids),
            )
        )
        n_rem = int(rdel.rowcount or 0)
    else:
        rdel2 = await db.execute(
            delete(Reminder).where(
                Reminder.tenant_id == tenant_id,
                Reminder.type == "onboarding_demo_followup",
            )
        )
        n_rem = int(rdel2.rowcount or 0)

    n_leads = 0
    if demo_lead_ids:
        ldel = await db.execute(delete(Lead).where(Lead.id.in_(demo_lead_ids)))
        n_leads = int(ldel.rowcount or 0)

    n_cand = 0
    if demo_cand_ids:
        cdel = await db.execute(delete(Candidate).where(Candidate.id.in_(demo_cand_ids)))
        n_cand = int(cdel.rowcount or 0)

    n_comp = 0
    if demo_company_ids:
        codel = await db.execute(delete(Company).where(Company.id.in_(demo_company_ids)))
        n_comp = int(codel.rowcount or 0)

    ob["demo_data_cleared_at"] = datetime.now(timezone.utc).isoformat()
    settings["onboarding"] = ob
    tenant.settings = settings
    tenant.updated_at = datetime.now(timezone.utc)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return {"reminders": n_rem, "leads": n_leads, "candidates": n_cand, "companies": n_comp}
