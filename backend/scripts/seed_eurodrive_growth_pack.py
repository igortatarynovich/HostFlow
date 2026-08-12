#!/usr/bin/env python3
"""EuroDrive growth pack — positive trends across recruitment / sales / marketing / vacancies.

Idempotent: removes previous ``eurodrive_growth_v1`` rows, then inserts backdated data
so module charts show upward movement over ~90 days and vacancies progress toward fill.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from backend.app.models import Candidate, Lead, Vacancy
from backend.app.models.additional_service import Service, ServiceItem, ServiceOrder
from backend.app.models.campaign import (
    CampaignFlightSpendEntry,
    CampaignOutcome,
    CampaignOutcomeResultLink,
    CampaignResultAttribution,
    CampaignResultQualification,
)
from backend.app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, Payment, PaymentMethod, PaymentStatus
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.models.sales_order import SalesBillableItem, SalesOrder, SalesOrderLine

TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"
OWN_COMPANY_ID = "e332a0b9-fe66-468d-b683-7829150f2780"
ADMIN_ID = "ced40564-e7e8-4acb-b7a1-305edeefcb85"
ANNA_ID = "a1111111-1111-4111-8111-111111111101"
MARIA_ID = "a1111111-1111-4111-8111-111111111102"

OPERATING_ID = "b2222222-2222-4222-8222-222222222201"
CLIENT_TL = "b2222222-2222-4222-8222-222222222202"
CLIENT_BH = "b2222222-2222-4222-8222-222222222203"
CLIENT_NF = "b2222222-2222-4222-8222-222222222204"
CLIENT_RC = "b2222222-2222-4222-8222-222222222205"
CLIENT_AL = "b2222222-2222-4222-8222-222222222206"
CLIENT_PT = "b2222222-2222-4222-8222-222222222207"

VAC_CE = "c3333333-3333-4333-8333-333333333301"
VAC_PLDE = "c3333333-3333-4333-8333-333333333302"
VAC_NORDICS = "c3333333-3333-4333-8333-333333333303"
VAC_WH = "c3333333-3333-4333-8333-333333333304"
VAC_ADR = "c3333333-3333-4333-8333-333333333305"

FUNNEL_ID = "a8a2dc96-c8f2-4309-a9a1-8d5260b40278"

CAMPAIGN_META = "d4444444-4444-4444-8444-444444444401"
FLIGHT_META = "d4444444-4444-4444-8444-444444444402"
CAMPAIGN_TT = "d4444444-4444-4444-8444-444444444403"
FLIGHT_TT = "d4444444-4444-4444-8444-444444444404"
CAMPAIGN_GG = "d4444444-4444-4444-8444-444444444405"
FLIGHT_GG = "d4444444-4444-4444-8444-444444444406"

PROFILE_META = "e5555555-5555-4555-8555-555555555501"

PACK = "eurodrive_growth_v1"

FIRST = [
    "Andriy", "Bohdan", "Oleksii", "Maksym", "Serhii", "Vitalii", "Pavlo", "Ihor",
    "Mykola", "Roman", "Taras", "Yaroslav", "Denys", "Artem", "Vadym", "Ostap",
    "Jakub", "Mateusz", "Piotr", "Krzysztof", "Tomasz", "Michał", "Łukasz", "Adam",
    "Olena", "Natalia", "Iryna", "Kateryna", "Anna", "Maria", "Julia", "Sofia",
]
LAST = [
    "Kovalenko", "Shevchenko", "Bondar", "Melnyk", "Kravchuk", "Tkachenko", "Moroz",
    "Lysenko", "Polishchuk", "Savchuk", "Horban", "Petrenko", "Rudenko", "Hrytsenko",
    "Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski", "Zieliński",
    "Szymański", "Woźniak", "Dąbrowski", "Kozłowski", "Jankowski", "Mazur", "Krawczyk",
]

DB_URL = (
    os.environ.get("ASYNC_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
)


def uid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def money(n: float | int | str) -> Decimal:
    return Decimal(str(n)).quantize(Decimal("0.01"))


def _db_url() -> str:
    url = DB_URL
    if url.startswith("postgresql+psycopg"):
        url = url.replace("postgresql+psycopg", "postgresql+asyncpg", 1)
    return url


async def _cleanup(db: AsyncSession) -> None:
    """Remove previous growth-pack rows (order respects FKs)."""
    # Marketing: outcomes → links → quals → attributions → spend (growth notes)
    await db.execute(
        text(
            """
            DELETE FROM acq_outcome_result_links
            WHERE tenant_id = :tid
              AND outcome_id IN (
                SELECT id FROM acq_outcomes
                WHERE tenant_id = :tid AND commercial_value_source = :pack
              )
            """
        ),
        {"tid": TENANT_ID, "pack": PACK},
    )
    await db.execute(
        text(
            "DELETE FROM acq_outcomes WHERE tenant_id = :tid AND commercial_value_source = :pack"
        ),
        {"tid": TENANT_ID, "pack": PACK},
    )
    await db.execute(
        text(
            """
            DELETE FROM acq_result_qualifications
            WHERE tenant_id = :tid
              AND attribution_id IN (
                SELECT id FROM acq_result_attributions
                WHERE tenant_id = :tid AND routing_source = :pack
              )
            """
        ),
        {"tid": TENANT_ID, "pack": PACK},
    )
    await db.execute(
        text(
            "DELETE FROM acq_result_attributions WHERE tenant_id = :tid AND routing_source = :pack"
        ),
        {"tid": TENANT_ID, "pack": PACK},
    )
    await db.execute(
        text(
            "DELETE FROM acq_flight_spend_entries WHERE tenant_id = :tid AND note LIKE :note"
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )

    # Sales / invoices tagged in notes/meta
    await db.execute(
        text(
            """
            DELETE FROM payments WHERE invoice_id IN (
              SELECT id FROM invoices WHERE tenant_id = :tid AND notes LIKE :note
            )
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM invoice_items WHERE invoice_id IN (
              SELECT id FROM invoices WHERE tenant_id = :tid AND notes LIKE :note
            )
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text("DELETE FROM invoices WHERE tenant_id = :tid AND notes LIKE :note"),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM sales_billable_items WHERE sales_order_id IN (
              SELECT id FROM sales_orders WHERE tenant_id = :tid AND title LIKE :note
            )
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM sales_order_lines WHERE sales_order_id IN (
              SELECT id FROM sales_orders WHERE tenant_id = :tid AND title LIKE :note
            )
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text("DELETE FROM sales_orders WHERE tenant_id = :tid AND title LIKE :note"),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM service_items WHERE order_id IN (
              SELECT id FROM service_orders WHERE tenant_id = :tid AND notes LIKE :note
            )
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text("DELETE FROM service_orders WHERE tenant_id = :tid AND notes LIKE :note"),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM sales_inquiries WHERE tenant_id = :tid AND notes LIKE :note
            """
        ),
        {"tid": TENANT_ID, "note": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM leads WHERE tenant_id = :tid
              AND (
                payload::text LIKE :pack
                OR normalized::text LIKE :pack
              )
            """
        ),
        {"tid": TENANT_ID, "pack": f"%{PACK}%"},
    )
    await db.execute(
        text(
            """
            DELETE FROM candidates WHERE tenant_id = :tid
              AND extra LIKE :pack
            """
        ),
        {"tid": TENANT_ID, "pack": f"%{PACK}%"},
    )
    await db.flush()


async def _tune_vacancies(db: AsyncSession) -> dict:
    """Adjust targets + status so UI shows healthy fill / closed wins."""
    specs = [
        # (id, headcount, status) — placed counts aligned for intermediate Vacancy Progress
        (VAC_CE, 20, "open"),  # ~12 employed → ~60%
        (VAC_PLDE, 12, "open"),  # ~7 hired → ~58%
        (VAC_NORDICS, 10, "open"),  # ~6 probation_ok → ~60%
        (VAC_WH, 15, "open"),  # ~6 employed → ~40%
        (VAC_ADR, 8, "open"),  # ~5 employed → ~62%
    ]
    out = {}
    for vid, hc, status in specs:
        v = (await db.execute(select(Vacancy).where(Vacancy.id == vid))).scalar_one_or_none()
        if not v:
            continue
        v.headcount_target = hc
        v.status = status
        if status == "filled":
            v.is_active = False
            v.is_archived = False
        else:
            v.is_active = True
        out[vid] = {"headcount_target": hc, "status": status}
    await db.flush()
    return out


async def _seed_candidates(db: AsyncSession) -> dict:
    """Backdated pipeline with rising volume and strong employed/hired outcomes."""
    now = utcnow()
    # Vacancy → company map
    vac_company = {
        VAC_CE: CLIENT_TL,
        VAC_PLDE: CLIENT_BH,
        VAC_NORDICS: CLIENT_NF,
        VAC_WH: CLIENT_RC,
        VAC_ADR: CLIENT_TL,
    }
    # Target employed counts per vacancy (aligned with headcount)
    employed_budget = {
        VAC_CE: 12,
        VAC_PLDE: 7,
        VAC_NORDICS: 6,
        VAC_WH: 6,
        VAC_ADR: 5,
    }
    managers = [("Adam", ADMIN_ID), ("Anna", ANNA_ID), ("Maria", MARIA_ID)]
    sources = ["meta", "tiktok", "google", "referral", "whatsapp", "form"]

    # Early funnel stages for recent inflow
    early = ["new", "contacted", "docs_wait", "docs_got", "ready_for_handoff", "processing_by_client"]
    success = ["employed", "hired", "probation_ok", "ready_for_hr", "employment_pending"]

    # Build ~85 candidates across 12 weeks with growing weekly volume
    weekly_volumes = [3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 10, 12]  # oldest → newest
    created_candidates: list[tuple[str, str, datetime, str]] = []  # id, stage, created, vac
    idx = 0
    employed_left = dict(employed_budget)

    for week_i, volume in enumerate(weekly_volumes):
        # week_i=0 is 11 weeks ago
        weeks_ago = 11 - week_i
        for j in range(volume):
            day_offset = weeks_ago * 7 + (j % 5)
            created = now - timedelta(days=day_offset, hours=3 + j)
            # Prefer success for older cohorts; newer still feed top of funnel
            success_ratio = 0.35 + week_i * 0.04  # rises over time but keep some early stages recently
            vac = [VAC_CE, VAC_PLDE, VAC_NORDICS, VAC_WH, VAC_ADR][idx % 5]
            # Force fill employed budgets first on older weeks
            if employed_left.get(vac, 0) > 0 and (weeks_ago >= 2 or success_ratio > 0.5):
                stage = success[idx % len(success)]
                if stage == "employment_pending" and weeks_ago >= 4:
                    stage = "employed"
                employed_left[vac] -= 1
            elif weeks_ago <= 1:
                stage = early[idx % len(early)]
            else:
                stage = success[idx % 3] if (idx % 3) else early[idx % len(early)]
                if stage in success and employed_left.get(vac, 0) > 0:
                    employed_left[vac] -= 1
                elif stage in ("employed", "hired", "probation_ok") and employed_left.get(vac, 0) <= 0:
                    stage = "ready_for_handoff"

            fn = FIRST[idx % len(FIRST)]
            ln = LAST[(idx * 3) % len(LAST)]
            # uniquify
            ln = f"{ln}{idx % 17}"
            mgr_name, recruiter = managers[idx % 3]
            cid = uid()
            company_id = vac_company[vac]
            lifecycle = "closed" if stage in ("employed", "hired", "probation_ok") else "active"
            c = Candidate(
                id=cid,
                tenant_id=TENANT_ID,
                own_company_id=OWN_COMPANY_ID,
                company_id=company_id,
                vacancy_id=vac,
                funnel_id=FUNNEL_ID,
                first_name=fn,
                last_name=ln,
                first_name_latin=fn,
                last_name_latin=ln,
                email=f"{fn.lower()}.{ln.lower()}{idx}@growth.example",
                phone=f"+48 51{idx % 10} {100 + idx:03d} {20 + (idx % 80):02d}",
                phone_country_code="+48",
                stage=stage,
                lifecycle_status=lifecycle,
                status="hired" if stage in ("employed", "hired", "probation_ok") else "active",
                source=sources[idx % len(sources)],
                recruiter_id=recruiter,
                manager=mgr_name,
                tags=["CE", "growth"] if vac != VAC_WH else ["warehouse", "growth"],
                note=f"Growth pack hire story — {PACK}",
                extra=json.dumps(
                    {
                        "screenshot_pack": PACK,
                        "growth_week": week_i,
                        "citizenship": "UA" if idx % 2 == 0 else "PL",
                        "role": "CE driver" if vac != VAC_WH else "warehouse",
                    }
                ),
                created_at=created.replace(tzinfo=None),
                updated_at=(created + timedelta(days=min(10, weeks_ago + 1))).replace(tzinfo=None),
            )
            db.add(c)
            created_candidates.append((cid, stage, created, vac))
            idx += 1

    # Drain remaining employed budget with extra placed candidates
    for vac, left in list(employed_left.items()):
        for k in range(max(0, left)):
            created = now - timedelta(days=20 + k * 3, hours=5)
            fn = FIRST[(idx + 5) % len(FIRST)]
            ln = f"{LAST[(idx * 5) % len(LAST)]}X{k}"
            cid = uid()
            mgr_name, recruiter = managers[idx % 3]
            db.add(
                Candidate(
                    id=cid,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    company_id=vac_company[vac],
                    vacancy_id=vac,
                    funnel_id=FUNNEL_ID,
                    first_name=fn,
                    last_name=ln,
                    email=f"placed.{fn.lower()}.{k}.{idx}@growth.example",
                    phone=f"+48 60{k} {200 + idx:03d} 11",
                    phone_country_code="+48",
                    stage="employed",
                    lifecycle_status="closed",
                    status="hired",
                    source="referral",
                    recruiter_id=recruiter,
                    manager=mgr_name,
                    tags=["CE", "placed", "growth"],
                    note=f"Placed — {PACK}",
                    extra=json.dumps({"screenshot_pack": PACK, "placed": True}),
                    created_at=created.replace(tzinfo=None),
                    updated_at=(created + timedelta(days=12)).replace(tzinfo=None),
                )
            )
            created_candidates.append((cid, "employed", created, vac))
            idx += 1
            employed_left[vac] -= 1

    # Lift a few existing storyboard candidates toward success
    await db.execute(
        text(
            """
            UPDATE candidates SET stage = 'employed', status = 'hired', lifecycle_status = 'closed',
              updated_at = NOW()
            WHERE tenant_id = :tid
              AND first_name = 'Dmytro' AND last_name = 'Shevchenko'
            """
        ),
        {"tid": TENANT_ID},
    )
    await db.execute(
        text(
            """
            UPDATE candidates SET stage = 'employed', status = 'hired', lifecycle_status = 'closed',
              updated_at = NOW()
            WHERE tenant_id = :tid
              AND first_name = 'Yulia' AND last_name = 'Savchuk'
            """
        ),
        {"tid": TENANT_ID},
    )
    await db.execute(
        text(
            """
            UPDATE candidates SET stage = 'ready_for_hr', updated_at = NOW()
            WHERE tenant_id = :tid
              AND first_name = 'Viktor' AND last_name = 'Petrenko'
            """
        ),
        {"tid": TENANT_ID},
    )

    # Ensure warehouse vacancy also shows fill progress
    await db.execute(
        text(
            """
            WITH pick AS (
              SELECT id FROM candidates
              WHERE tenant_id = :tid AND vacancy_id = :vac AND deleted_at IS NULL
                AND stage NOT IN ('employed','hired','probation_ok')
              ORDER BY created_at
              LIMIT 6
            )
            UPDATE candidates
            SET stage = 'employed', status = 'hired', lifecycle_status = 'closed', updated_at = NOW()
            WHERE id IN (SELECT id FROM pick)
            """
        ),
        {"tid": TENANT_ID, "vac": VAC_WH},
    )

    await db.flush()
    by_stage: dict[str, int] = {}
    for _, stage, _, _ in created_candidates:
        by_stage[stage] = by_stage.get(stage, 0) + 1
    return {"created": len(created_candidates), "by_stage": by_stage, "candidates": created_candidates}


async def _seed_sales(db: AsyncSession) -> dict:
    now = utcnow()
    # Resolve a recruitment service for orders
    svc = (
        await db.execute(
            select(Service).where(Service.tenant_id == TENANT_ID, Service.code == "ED-RECRUIT-CE").limit(1)
        )
    ).scalar_one_or_none()
    if svc is None:
        svc = (
            await db.execute(select(Service).where(Service.tenant_id == TENANT_ID).limit(1))
        ).scalar_one_or_none()
    svc_id = svc.id if svc else None
    base_price = float(svc.base_price) if svc and svc.base_price is not None else 1200.0

    # Client leads funnel: rising new → qualified → converted over 90d
    client_specs = [
        ("NorthStar Haulage", "Erik Bergman", "new", 5, "meta"),
        ("Vistula Cargo", "Anna Zielińska", "new", 3, "google"),
        ("Danube Freight", "Klaus Meyer", "contacted", 12, "linkedin"),
        ("Baltic Peak", "Jonas Petrauskas", "contacted", 18, "meta"),
        ("Helvetia Drivers AG", "Sophie Meier", "waiting_for_response", 25, "referral"),
        ("Oder Line Sp. z o.o.", "Marek Wiśniewski", "qualified", 32, "website"),
        ("Lowlands Logistics", "Eva Jansen", "qualified", 40, "meta"),
        ("TransLogistik GmbH — expand", "Hans Vogt", "converted", 48, "referral"),
        ("Nordic Fleet AB — batch 2", "Erik Lindqvist", "converted", 55, "linkedin"),
        ("RhineCargo BV — ADR", "Sanne de Vries", "converted", 62, "meta"),
        ("Polska Trasa — seasonal", "Piotr Nowak", "converted", 70, "google"),
        ("Alpina Logistics — retain", "Marco Keller", "converted", 80, "referral"),
    ]
    inquiry_count = 0
    for i, (company, contact, stage, days_ago, source) in enumerate(client_specs):
        created = now - timedelta(days=days_ago, hours=2)
        lid = uid()
        fn, _, ln = contact.partition(" ")
        converted_company = None
        if "TransLogistik" in company:
            converted_company = CLIENT_TL
        elif "Nordic Fleet" in company:
            converted_company = CLIENT_NF
        elif "RhineCargo" in company:
            converted_company = CLIENT_RC
        elif "Polska Trasa" in company:
            converted_company = CLIENT_PT
        elif "Alpina" in company:
            converted_company = CLIENT_AL

        lead = Lead(
            id=lid,
            tenant_id=TENANT_ID,
            own_company_id=OWN_COMPANY_ID,
            lead_type="client",
            lead_target_type="client_lead",
            company_id=OPERATING_ID,
            source=source,
            payload={
                "screenshot_pack": PACK,
                "company_name": company,
                "contact": contact,
                "need": "CE driver recruitment partnership",
            },
            normalized={
                "full_name": contact,
                "first_name": fn,
                "last_name": ln or fn,
                "company_name": company,
                "b2b": {"company_name": company},
                "screenshot_pack": PACK,
            },
            status="new" if stage == "new" else "processed",
            stage="qualified" if stage == "converted" else stage,
            converted_client_id=converted_company,
            created_at=created,
        )
        db.add(lead)
        await db.flush()
        inq_status = {
            "new": "received",
            "contacted": "in_progress",
            "waiting_for_response": "waiting_for_information",
            "qualified": "reviewing",
            "converted": "converted",
        }.get(stage, "in_progress")
        db.add(
            SalesInquiry(
                id=uid(),
                tenant_id=TENANT_ID,
                lead_id=lid,
                status=inq_status,
                source=source,
                own_company_id=OWN_COMPANY_ID,
                assignee_id=ADMIN_ID,
                meta={"screenshot_pack": PACK, "company_name": company},
                notes=f"Growth inquiry #{i + 1} [{PACK}]",
            )
        )
        inquiry_count += 1
        # Backdate inquiry created_at
        await db.flush()
        await db.execute(
            text(
                "UPDATE sales_inquiries SET created_at = :ts, updated_at = :ts "
                "WHERE tenant_id = :tid AND notes LIKE :note AND lead_id = :lid"
            ),
            {"ts": created, "tid": TENANT_ID, "note": f"%{PACK}%", "lid": lid},
        )

    # Sales orders — completed/in_progress with rising commercial activity
    sales_rows = [
        (CLIENT_TL, "TransLogistik — growth retainer Q2", "completed", 75, 8, 1200),
        (CLIENT_BH, "Baltic Haulage — corridor expansion", "completed", 60, 6, 1100),
        (CLIENT_NF, "Nordic Fleet — filled order", "completed", 45, 6, 1400),
        (CLIENT_AL, "Alpina — ADR placements", "completed", 35, 4, 1500),
        (CLIENT_RC, "RhineCargo — warehouse wave 1", "in_progress", 20, 10, 650),
        (CLIENT_PT, "Polska Trasa — seasonal CE", "in_progress", 12, 8, 1150),
        (CLIENT_TL, "TransLogistik — Q3 top-up", "open", 5, 5, 1200),
    ]
    so_count = 0
    for company_id, title, status, days_ago, qty, rate in sales_rows:
        created = now - timedelta(days=days_ago)
        so_id = uid()
        so = SalesOrder(
            id=so_id,
            tenant_id=TENANT_ID,
            own_company_id=OWN_COMPANY_ID,
            company_id=company_id,
            payer_company_id=company_id,
            title=f"{title} [{PACK}]",
            status=status,
            currency="EUR",
            payment_term_days=14,
            payment_model="per_hire",
            vat_rate=money(23),
            guarantee_days=90,
            invoice_right_policy="on_trigger",
            billing_notes=f"Growth pack commercial deal [{PACK}]",
            commercial_snapshot={"screenshot_pack": PACK},
        )
        db.add(so)
        await db.flush()
        line_id = uid()
        trigger = "headcount_completed" if status == "completed" else "candidate_hired"
        db.add(
            SalesOrderLine(
                id=line_id,
                tenant_id=TENANT_ID,
                sales_order_id=so_id,
                title=title,
                role_label="CE Driver" if "warehouse" not in title.lower() else "Warehouse",
                location="EU",
                quantity_needed=qty,
                unit_rate=money(rate),
                charge_unit="person",
                billing_trigger=trigger,
                guarantee_days=90,
                status="completed" if status == "completed" else "in_progress" if status == "in_progress" else "open",
                sort_order=0,
            )
        )
        await db.flush()
        if status == "completed":
            db.add(
                SalesBillableItem(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    sales_order_id=so_id,
                    sales_order_line_id=line_id,
                    trigger_code=trigger,
                    amount=money(qty * rate),
                    currency="EUR",
                    quantity=money(qty),
                    source_entity_type="company",
                    source_entity_id=company_id,
                    status="invoiced",
                    notes=f"Placements delivered [{PACK}]",
                )
            )
            await db.flush()
        await db.execute(
            text(
                "UPDATE sales_orders SET created_at = :ts, updated_at = :ts WHERE id = :id"
            ),
            {"ts": created, "id": so_id},
        )
        so_count += 1

        # Invoice for completed deals
        if status == "completed":
            inv_id = uid()
            net = money(qty * rate)
            vat = (net * money("0.23")).quantize(Decimal("0.01"))
            total = net + vat
            issue = (created + timedelta(days=3)).date()
            paid = days_ago > 40
            db.add(
                Invoice(
                    id=inv_id,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    company_id=company_id,
                    invoice_number=f"ED-G-2026/{1000 + so_count}",
                    status=InvoiceStatus.paid.value if paid else InvoiceStatus.issued.value,
                    issue_date=issue,
                    due_date=issue + timedelta(days=14),
                    currency="EUR",
                    subtotal=net,
                    vat_total=vat,
                    total_amount=total,
                    paid_amount=total if paid else money(0),
                    payment_date=issue + timedelta(days=7) if paid else None,
                    created_by=ADMIN_ID,
                    notes=f"Growth invoice [{PACK}]",
                    billing_details={"screenshot_pack": PACK},
                )
            )
            db.add(
                InvoiceItem(
                    id=uid(),
                    invoice_id=inv_id,
                    line_no=1,
                    description=title,
                    qty=money(qty),
                    unit_price=money(rate),
                    vat_rate=money(23),
                )
            )
            if paid:
                db.add(
                    Payment(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        invoice_id=inv_id,
                        amount=total,
                        currency="EUR",
                        method=PaymentMethod.bank_transfer.value,
                        status=PaymentStatus.confirmed.value,
                        payment_date=issue + timedelta(days=7),
                        reference_number=f"PAY-ED-G-{1000 + so_count}",
                    )
                )

    # Service orders trend (Sales Efficiency charts)
    svc_count = 0
    if svc_id:
        svc_specs = [
            (CLIENT_TL, "completed", 70, 5),
            (CLIENT_BH, "completed", 55, 4),
            (CLIENT_NF, "completed", 42, 6),
            (CLIENT_AL, "completed", 28, 3),
            (CLIENT_RC, "in_progress", 14, 8),
            (CLIENT_PT, "confirmed", 7, 5),
            (CLIENT_TL, "in_progress", 3, 6),
        ]
        for company_id, status, days_ago, qty in svc_specs:
            created = now - timedelta(days=days_ago)
            oid = uid()
            net = base_price * qty
            vat = round(net * 0.23, 2)
            db.add(
                ServiceOrder(
                    id=oid,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    company_id=company_id,
                    status=status,
                    total_amount=net + vat,
                    vat_total=vat,
                    currency="EUR",
                    requested_by=ADMIN_ID,
                    assigned_to=ADMIN_ID,
                    start_date=(created - timedelta(days=2)).date(),
                    end_date=(created + timedelta(days=30)).date() if status != "completed" else (created + timedelta(days=10)).date(),
                    notes=f"Growth service order [{PACK}]",
                    audit={"screenshot_pack": PACK},
                )
            )
            db.add(
                ServiceItem(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    order_id=oid,
                    service_id=svc_id,
                    qty=float(qty),
                    unit_price=base_price,
                    estimated_cost=base_price * 0.35 * qty,
                    cost_currency="EUR",
                    cost_status="estimated",
                    vat_rate=23,
                    amount=net + vat,
                    status="delivered" if status == "completed" else "in_progress",
                    meta={"screenshot_pack": PACK},
                )
            )
            await db.flush()
            await db.execute(
                text("UPDATE service_orders SET created_at = :ts, updated_at = :ts WHERE id = :id"),
                {"ts": created, "id": oid},
            )
            svc_count += 1

    await db.flush()
    return {"inquiries": inquiry_count, "sales_orders": so_count, "service_orders": svc_count}


async def _seed_marketing(db: AsyncSession, candidates: list[tuple[str, str, datetime, str]]) -> dict:
    """Daily spend + attributions/qualifications/outcomes with rising curve over 60 days."""
    now = utcnow()
    flights = [
        (CAMPAIGN_META, FLIGHT_META, 1.0),
        (CAMPAIGN_TT, FLIGHT_TT, 0.55),
        (CAMPAIGN_GG, FLIGHT_GG, 0.7),
    ]

    # Extend flight windows to cover full growth window
    start = now - timedelta(days=60)
    end = now + timedelta(days=14)
    for _, flight_id, _ in flights:
        await db.execute(
            text(
                "UPDATE acq_campaign_runs SET starts_at = :s, ends_at = :e, status = 'active' WHERE id = :id"
            ),
            {"s": start, "e": end, "id": flight_id},
        )

    spend_n = 0
    for day in range(60, -1, -1):
        day_dt = now - timedelta(days=day)
        # Rising daily spend base: ~40 EUR → ~180 EUR across channels
        base = 40 + (60 - day) * 2.3
        for campaign_id, flight_id, weight in flights:
            amount = money(round(base * weight * (0.92 + (day % 5) * 0.02), 2))
            sid = uid()
            db.add(
                CampaignFlightSpendEntry(
                    id=sid,
                    tenant_id=TENANT_ID,
                    campaign_id=campaign_id,
                    campaign_run_id=flight_id,
                    amount=amount,
                    currency="EUR",
                    note=f"daily growth spend d-{day} [{PACK}]",
                )
            )
            await db.flush()
            await db.execute(
                text("UPDATE acq_flight_spend_entries SET created_at = :ts, updated_at = :ts WHERE id = :id"),
                {"ts": day_dt.replace(hour=10, minute=15), "id": sid},
            )
            spend_n += 1

    # Create candidate leads + attributions for a rising subset of growth candidates
    # Prefer meta-sourced / older→newer mix
    attr_n = 0
    qual_n = 0
    outcome_n = 0
    # Take up to 48 candidates spread across time
    sample = candidates[:: max(1, len(candidates) // 48)][:48]
    for i, (cand_id, stage, created, vac) in enumerate(sample):
        campaign_id, flight_id, _ = flights[i % 3]
        lead_id = uid()
        submission_id = uid()
        lead = Lead(
            id=lead_id,
            tenant_id=TENANT_ID,
            own_company_id=OWN_COMPANY_ID,
            lead_type="candidate",
            lead_target_type="candidate",
            company_id=OPERATING_ID,
            vacancy_id=vac,
            source=["meta", "tiktok", "google"][i % 3],
            payload={"screenshot_pack": PACK, "candidate_id": cand_id},
            normalized={"screenshot_pack": PACK},
            status="processed",
            stage="contacted" if stage != "new" else "new",
            candidate_id=cand_id,
            created_at=created,
        )
        db.add(lead)
        await db.flush()
        attr_id = uid()
        db.add(
            CampaignResultAttribution(
                id=attr_id,
                tenant_id=TENANT_ID,
                campaign_id=campaign_id,
                campaign_run_id=flight_id,
                result_type="lead",
                result_id=lead_id,
                submission_id=submission_id,
                lead_id=lead_id,
                route_intent="candidate",
                endpoint_intake_source_profile_id=PROFILE_META if i % 3 == 0 else None,
                routing_source=PACK,
            )
        )
        await db.flush()
        await db.execute(
            text(
                "UPDATE acq_result_attributions SET created_at = :ts, updated_at = :ts WHERE id = :id"
            ),
            {"ts": created, "id": attr_id},
        )
        attr_n += 1

        # ~70% qualified
        if i % 10 < 7:
            q_at = created + timedelta(hours=6)
            db.add(
                CampaignResultQualification(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    attribution_id=attr_id,
                    qualified_at=q_at,
                )
            )
            qual_n += 1

            # ~50% of qualified become completed outcomes (hires)
            if stage in ("employed", "hired", "probation_ok", "ready_for_hr", "ready_for_handoff") or i % 3 == 0:
                completed_at = created + timedelta(days=min(14, 3 + (i % 8)))
                outcome_id = uid()
                value = money(1100 + (i % 5) * 80)
                db.add(
                    CampaignOutcome(
                        id=outcome_id,
                        tenant_id=TENANT_ID,
                        campaign_id=campaign_id,
                        campaign_run_id=flight_id,
                        status="completed",
                        progress_current=1,
                        progress_target=1,
                        activated_at=created + timedelta(days=1),
                        completed_at=completed_at,
                        commercial_value_amount=value,
                        commercial_value_currency="EUR",
                        commercial_value_source=PACK,
                        commercial_value_set_at=completed_at,
                    )
                )
                db.add(
                    CampaignOutcomeResultLink(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        outcome_id=outcome_id,
                        attribution_id=attr_id,
                        result_type="lead",
                        result_id=lead_id,
                        counted_at=completed_at,
                    )
                )
                await db.flush()
                await db.execute(
                    text(
                        "UPDATE acq_outcomes SET created_at = :ts, updated_at = :ts WHERE id = :id"
                    ),
                    {"ts": created + timedelta(days=1), "id": outcome_id},
                )
                outcome_n += 1

    await db.flush()
    return {"spend_entries": spend_n, "attributions": attr_n, "qualifications": qual_n, "outcomes": outcome_n}


async def main() -> None:
    engine = create_async_engine(_db_url(), future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        await _cleanup(db)
        vac = await _tune_vacancies(db)
        cand = await _seed_candidates(db)
        sales = await _seed_sales(db)
        mkt = await _seed_marketing(db, cand["candidates"])

        # Stamp tenant settings via ORM (avoid asyncpg cast+bind quirks)
        from backend.app.models import Tenant

        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == TENANT_ID).limit(1))
        ).scalar_one()
        settings = dict(tenant.settings or {})
        onboarding = dict(settings.get("onboarding") or {})
        onboarding["screenshot_pack_growth"] = PACK
        settings["onboarding"] = onboarding
        tenant.settings = settings
        await db.commit()

        # Verification snapshot
        stage_rows = (
            await db.execute(
                text(
                    """
                    SELECT stage, count(*) FROM candidates
                    WHERE tenant_id = :tid AND deleted_at IS NULL
                    GROUP BY 1 ORDER BY 2 DESC
                    """
                ),
                {"tid": TENANT_ID},
            )
        ).all()
        vac_rows = (
            await db.execute(
                text(
                    """
                    SELECT v.title, v.status, v.headcount_target,
                      (SELECT count(*) FROM candidates c
                       WHERE c.vacancy_id = v.id AND c.deleted_at IS NULL
                         AND c.stage IN ('employed','hired','probation_ok')) AS placed
                    FROM vacancies v WHERE v.tenant_id = :tid ORDER BY v.title
                    """
                ),
                {"tid": TENANT_ID},
            )
        ).all()

        print(
            json.dumps(
                {
                    "ok": True,
                    "pack": PACK,
                    "vacancies_tuned": vac,
                    "candidates_added": cand["created"],
                    "candidates_by_stage_added": cand["by_stage"],
                    "sales": sales,
                    "marketing": mkt,
                    "verify": {
                        "candidate_stages": {r[0]: r[1] for r in stage_rows},
                        "vacancy_fill": [
                            {
                                "title": r[0],
                                "status": r[1],
                                "target": r[2],
                                "placed": r[3],
                                "pct": round(100 * r[3] / r[2], 1) if r[2] else 0,
                            }
                            for r in vac_rows
                        ],
                    },
                    "login": "demo@hostflow.dev",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
