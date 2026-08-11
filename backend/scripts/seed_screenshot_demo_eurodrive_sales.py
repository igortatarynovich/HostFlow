#!/usr/bin/env python3
"""Seed sales/commercial demo for EuroDrive screenshot tenant.

Adds clients, vacancies, client accounts, B2B sales inquiries,
services catalog, service orders, sales orders (+ lines / billables),
and invoices — so Sales / Orders / Invoices screens are not empty.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from backend.app.models import Company, Lead, OwnCompany, Tenant, Vacancy
from backend.app.models.additional_service import Service, ServiceItem, ServiceOrder
from backend.app.models.client_account import ClientAccount
from backend.app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, Payment, PaymentMethod, PaymentStatus
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.models.sales_order import SalesBillableItem, SalesOrder, SalesOrderLine
from backend.app.services.recruitment_funnel_bootstrap import resolve_company_default_funnel_id

TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"
OWN_COMPANY_ID = "e332a0b9-fe66-468d-b683-7829150f2780"
IGOR_ID = "ced40564-e7e8-4acb-b7a1-305edeefcb85"

OPERATING_ID = "b2222222-2222-4222-8222-222222222201"
CLIENT_TL_ID = "b2222222-2222-4222-8222-222222222202"  # TransLogistik
CLIENT_BH_ID = "b2222222-2222-4222-8222-222222222203"  # Baltic Haulage

PACK = "eurodrive_sales_v1"

DB_URL = (
    os.environ.get("ASYNC_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
)


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


def money(n: float | int | str) -> Decimal:
    return Decimal(str(n)).quantize(Decimal("0.01"))


NEW_CLIENTS = [
    {
        "id": "b2222222-2222-4222-8222-222222222204",
        "name": "Nordic Fleet AB",
        "legal": "Nordic Fleet Aktiebolag",
        "tax_id": "SE556012345601",
        "phone": "+46 8 555 2100",
        "email": "procurement@nordicfleet.example",
        "country_code": "SE",
        "country": "Sweden",
        "city": "Stockholm",
        "address": "Hamngatan 4, 111 47 Stockholm",
        "contact": {"name": "Erik Lindqvist", "email": "erik.lindqvist@nordicfleet.example"},
        "stage": "active",
        "source": "linkedin",
    },
    {
        "id": "b2222222-2222-4222-8222-222222222205",
        "name": "RhineCargo BV",
        "legal": "RhineCargo B.V.",
        "tax_id": "NL812345678B01",
        "phone": "+31 10 400 8800",
        "email": "hr@rhinecargo.example",
        "country_code": "NL",
        "country": "Netherlands",
        "city": "Rotterdam",
        "address": "Waalhaven Z.z. 18, 3088 HH Rotterdam",
        "contact": {"name": "Sanne de Vries", "email": "sanne.devries@rhinecargo.example"},
        "stage": "qualified",
        "source": "referral",
    },
    {
        "id": "b2222222-2222-4222-8222-222222222206",
        "name": "Alpina Logistics AG",
        "legal": "Alpina Logistics AG",
        "tax_id": "CHE123456789",
        "phone": "+41 44 200 3300",
        "email": "talent@alpina-logistics.example",
        "country_code": "CH",
        "country": "Switzerland",
        "city": "Zürich",
        "address": "Hardstrasse 201, 8005 Zürich",
        "contact": {"name": "Marco Keller", "email": "marco.keller@alpina-logistics.example"},
        "stage": "negotiation",
        "source": "meta",
    },
    {
        "id": "b2222222-2222-4222-8222-222222222207",
        "name": "Polska Trasa Sp. z o.o.",
        "legal": "Polska Trasa Spółka z o.o.",
        "tax_id": "PL7740001111",
        "phone": "+48 22 600 4500",
        "email": "rekrutacja@polskatrasa.example",
        "country_code": "PL",
        "country": "Poland",
        "city": "Warszawa",
        "address": "ul. Łopuszańska 32, 02-220 Warszawa",
        "contact": {"name": "Anna Zielińska", "email": "a.zielinska@polskatrasa.example"},
        "stage": "prospect",
        "source": "website",
    },
]

VACANCIES = [
    {
        "id": "c3333333-3333-4333-8333-333333333302",
        "company_id": CLIENT_BH_ID,
        "title": "C+E Drivers PL–DE",
        "location": "Gdańsk / Hamburg corridor",
        "salary_from": "1600",
        "salary_to": "2100",
        "headcount": 12,
        "desc": "Domestic and DE shuttle CE drivers. Code 95, ADR preferred.",
    },
    {
        "id": "c3333333-3333-4333-8333-333333333303",
        "company_id": "b2222222-2222-4222-8222-222222222204",
        "title": "CE Drivers Nordics",
        "location": "SE / NO / DK",
        "salary_from": "2000",
        "salary_to": "2600",
        "headcount": 8,
        "desc": "Nordic long-haul CE drivers. Scandinavian language bonus.",
    },
    {
        "id": "c3333333-3333-4333-8333-333333333304",
        "company_id": "b2222222-2222-4222-8222-222222222205",
        "title": "Warehouse Operators — Rotterdam",
        "location": "Rotterdam",
        "salary_from": "1400",
        "salary_to": "1800",
        "headcount": 20,
        "desc": "Forklift + picking. EU work authorization required.",
    },
    {
        "id": "c3333333-3333-4333-8333-333333333305",
        "company_id": CLIENT_TL_ID,
        "title": "ADR Tank Drivers",
        "location": "EU / DE base",
        "salary_from": "1900",
        "salary_to": "2500",
        "headcount": 6,
        "desc": "ADR certified tank drivers for chemical / fuel runs.",
    },
]


async def _wipe_pack(db: AsyncSession) -> None:
    """Remove previous sales pack rows for this tenant (idempotent re-run)."""
    # Invoices referencing service orders / companies
    inv_ids = [
        r[0]
        for r in (
            await db.execute(
                select(Invoice.id).where(
                    Invoice.tenant_id == TENANT_ID,
                    Invoice.notes.contains(PACK),
                )
            )
        ).all()
    ]
    if not inv_ids:
        # also wipe by invoice_number prefix
        inv_ids = [
            r[0]
            for r in (
                await db.execute(
                    select(Invoice.id).where(
                        Invoice.tenant_id == TENANT_ID,
                        Invoice.invoice_number.like("ED-DEMO-%"),
                    )
                )
            ).all()
        ]
    if inv_ids:
        await db.execute(delete(Payment).where(Payment.invoice_id.in_(inv_ids)))
        await db.execute(delete(InvoiceItem).where(InvoiceItem.invoice_id.in_(inv_ids)))
        await db.execute(delete(Invoice).where(Invoice.id.in_(inv_ids)))

    so_ids = [
        r[0]
        for r in (
            await db.execute(select(SalesOrder.id).where(SalesOrder.tenant_id == TENANT_ID))
        ).all()
    ]
    if so_ids:
        await db.execute(delete(SalesBillableItem).where(SalesBillableItem.sales_order_id.in_(so_ids)))
        await db.execute(delete(SalesOrderLine).where(SalesOrderLine.sales_order_id.in_(so_ids)))
        await db.execute(delete(SalesOrder).where(SalesOrder.id.in_(so_ids)))

    svc_order_ids = [
        r[0]
        for r in (
            await db.execute(select(ServiceOrder.id).where(ServiceOrder.tenant_id == TENANT_ID))
        ).all()
    ]
    if svc_order_ids:
        await db.execute(delete(ServiceItem).where(ServiceItem.order_id.in_(svc_order_ids)))
        await db.execute(delete(ServiceOrder).where(ServiceOrder.id.in_(svc_order_ids)))

    await db.execute(delete(Service).where(Service.tenant_id == TENANT_ID, Service.code.like("ED-%")))

    # Client leads + sales inquiries from pack
    client_leads = (
        await db.execute(
            select(Lead).where(
                Lead.tenant_id == TENANT_ID,
                Lead.lead_type == "client",
                Lead.lead_target_type == "client_lead",
            )
        )
    ).scalars().all()
    lead_ids = [str(l.id) for l in client_leads]
    if lead_ids:
        await db.execute(delete(SalesInquiry).where(SalesInquiry.lead_id.in_(lead_ids)))
        await db.execute(delete(Lead).where(Lead.id.in_(lead_ids)))

    await db.execute(
        text("DELETE FROM client_accounts WHERE tenant_id = :t"),
        {"t": TENANT_ID},
    )

    # Extra vacancies from this pack
    vac_ids = [v["id"] for v in VACANCIES]
    await db.execute(delete(Vacancy).where(Vacancy.id.in_(vac_ids)))

    # Extra client companies from this pack
    for c in NEW_CLIENTS:
        existing = await db.get(Company, c["id"])
        if existing is not None:
            await db.delete(existing)

    await db.flush()


async def main() -> None:
    engine = create_async_engine(DB_URL, future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": TENANT_ID})

        tenant = (await db.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one()
        settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
        modules = dict(settings.get("modules") or {})
        for key in (
            "leads",
            "services",
            "companies",
            "documents",
            "vacancies",
            "candidates",
            "recruitment",
            "client_portal",
            "sales",
            "billing",
            "invoices",
            "orders",
        ):
            modules[key] = True
        settings["modules"] = modules
        ob = dict(settings.get("onboarding") or {})
        ob["screenshot_pack_sales"] = PACK
        settings["onboarding"] = ob
        tenant.settings = settings
        db.add(tenant)

        own = (await db.execute(select(OwnCompany).where(OwnCompany.id == OWN_COMPANY_ID))).scalar_one()
        # Ensure operating + two original clients still exist
        for required_id, label in (
            (OPERATING_ID, "operating"),
            (CLIENT_TL_ID, "TransLogistik"),
            (CLIENT_BH_ID, "Baltic Haulage"),
        ):
            row = await db.get(Company, required_id)
            if row is None:
                raise RuntimeError(f"Missing base company {label} ({required_id}). Run eurodrive seed first.")

        await _wipe_pack(db)

        funnel_id = await resolve_company_default_funnel_id(
            db, tenant_id=TENANT_ID, company_id=OPERATING_ID, funnel_type="candidate"
        )

        # --- Extra clients ---
        for c in NEW_CLIENTS:
            db.add(
                Company(
                    id=c["id"],
                    tenant_id=TENANT_ID,
                    name=c["name"],
                    legal_name=c["legal"],
                    tax_id=c["tax_id"],
                    phone=c["phone"],
                    email=c["email"],
                    country_code=c["country_code"],
                    country=c["country"],
                    city=c["city"],
                    address=c["address"],
                    contacts={"primary": c["contact"]},
                    party_entity_type="company",
                    party_business_roles="employer",
                    client_stage=(
                        c["stage"]
                        if c["stage"]
                        in {"prospect", "qualified", "active", "negotiation", "on_hold", "churned"}
                        else "prospect"
                    ),
                    client_source=c["source"],
                    extra={
                        "company_role": "client",
                        "company_type": "employer",
                        "screenshot_pack": PACK,
                    },
                )
            )
        await db.flush()

        # --- Client accounts (commercial SoT) ---
        account_by_company: dict[str, str] = {}
        account_specs = [
            (CLIENT_TL_ID, "TransLogistik GmbH", "active"),
            (CLIENT_BH_ID, "Baltic Haulage Sp. z o.o.", "active"),
            ("b2222222-2222-4222-8222-222222222204", "Nordic Fleet AB", "active"),
            ("b2222222-2222-4222-8222-222222222205", "RhineCargo BV", "prospect"),
            ("b2222222-2222-4222-8222-222222222206", "Alpina Logistics AG", "prospect"),
            ("b2222222-2222-4222-8222-222222222207", "Polska Trasa Sp. z o.o.", "prospect"),
        ]
        for company_id, display, status in account_specs:
            aid = uid()
            account_by_company[company_id] = aid
            db.add(
                ClientAccount(
                    id=aid,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    display_name=display,
                    status=status,
                    owner_user_id=IGOR_ID,
                    primary_company_id=company_id,
                    origin_type="manual_seed",
                    creation_ref=company_id,  # varchar(36) unique per tenant
                    commercial_defaults={
                        "currency": "EUR",
                        "payment_term_days": 14,
                        "vat_rate": 23,
                        "payment_model": "per_hire",
                    },
                )
            )
        await db.flush()

        # --- Extra vacancies ---
        for v in VACANCIES:
            db.add(
                Vacancy(
                    id=v["id"],
                    tenant_id=TENANT_ID,
                    company_id=v["company_id"],
                    own_company_id=OWN_COMPANY_ID,
                    title=v["title"],
                    description=v["desc"],
                    location=v["location"],
                    salary_from=v["salary_from"],
                    salary_to=v["salary_to"],
                    currency="EUR",
                    status="open",
                    is_active=True,
                    is_archived=False,
                    employment_type="full_time",
                    headcount_target=v["headcount"],
                    funnel_id=funnel_id,
                    manager=IGOR_ID,
                    extra=json.dumps({"screenshot_pack": PACK}),
                    settings_json={"priority": "medium"},
                )
            )
        await db.flush()

        # --- B2B sales inquiries (client leads — powers /app/sales) ---
        inquiries = [
            {
                "company": "GreenLine Transport Sp. z o.o.",
                "contact": "Tomasz Lewandowski",
                "email": "t.lewandowski@greenline.example",
                "phone": "+48 601 220 110",
                "need": "podbor kierowcow CE na trasy PL-DE",
                "stage": "new",
                "source": "meta",
                "hours": 3,
            },
            {
                "company": "CargoPeak GmbH",
                "contact": "Julia Hartmann",
                "email": "j.hartmann@cargopeak.example",
                "phone": "+49 30 887 4410",
                "need": "recruitment of CE drivers for DE fleet",
                "stage": "contacted",
                "source": "linkedin",
                "hours": 18,
            },
            {
                "company": "BlueBox Warehousing",
                "contact": "Piotr Kamiński",
                "email": "piotr.k@bluebox.example",
                "phone": "+48 512 300 880",
                "need": "targeting ads for warehouse hiring campaign",
                "stage": "waiting_for_response",
                "source": "website",
                "hours": 40,
            },
            {
                "company": "Alpina Logistics AG",
                "contact": "Marco Keller",
                "email": "marco.keller@alpina-logistics.example",
                "phone": "+41 44 200 3300",
                "need": "podbor personalu — CE + ADR",
                "stage": "qualified",
                "source": "referral",
                "hours": 72,
                "converted_company_id": "b2222222-2222-4222-8222-222222222206",
            },
            {
                "company": "FastMile Express",
                "contact": "Olga Nowak",
                "email": "o.nowak@fastmile.example",
                "phone": "+48 600 111 222",
                "need": "outsourcing drivers for peak season",
                "stage": "new",
                "source": "google",
                "hours": 6,
            },
            {
                "company": "RhineCargo BV",
                "contact": "Sanne de Vries",
                "email": "sanne.devries@rhinecargo.example",
                "phone": "+31 10 400 8800",
                "need": "driver recruitment + legalization support",
                "stage": "contacted",
                "source": "meta",
                "hours": 28,
                "client_account_id": account_by_company["b2222222-2222-4222-8222-222222222205"],
            },
        ]
        for i, row in enumerate(inquiries):
            lid = uid()
            created = now() - timedelta(hours=row["hours"])
            fn, _, ln = row["contact"].partition(" ")
            normalized = {
                "full_name": row["contact"],
                "first_name": fn,
                "last_name": ln or fn,
                "email": row["email"],
                "phone": row["phone"],
                "company_name": row["company"],
                "contact_person": {
                    "full_name": row["contact"],
                    "first_name": fn,
                    "last_name": ln or fn,
                    "email": row["email"],
                    "phone": row["phone"],
                },
                "need": {"what_needed": row["need"], "summary": row["need"]},
                "b2b": {"company_name": row["company"]},
                "screenshot_pack": PACK,
            }
            lead = Lead(
                id=lid,
                tenant_id=TENANT_ID,
                own_company_id=OWN_COMPANY_ID,
                lead_type="client",
                lead_target_type="client_lead",
                company_id=OPERATING_ID,
                source=row["source"],
                payload={
                    "screenshot_pack": PACK,
                    "company_name": row["company"],
                    "contact": row["contact"],
                    "need": row["need"],
                },
                normalized=normalized,
                status="new" if row["stage"] == "new" else "processed",
                stage=row["stage"],
                converted_client_id=row.get("converted_company_id"),
                client_account_id=row.get("client_account_id"),
                created_at=created,
            )
            db.add(lead)
            await db.flush()
            db.add(
                SalesInquiry(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    lead_id=lid,
                    status="received" if row["stage"] == "new" else "in_progress",
                    source=row["source"],
                    own_company_id=OWN_COMPANY_ID,
                    assignee_id=IGOR_ID,
                    meta={"screenshot_pack": PACK, "company_name": row["company"]},
                    notes=f"Demo inquiry #{i + 1}",
                )
            )
        await db.flush()

        # --- Services catalog ---
        services_spec = [
            ("ED-RECRUIT-CE", "CE Driver Recruitment", "recruitment", 1200.0, "person"),
            ("ED-RECRUIT-WH", "Warehouse Staff Recruitment", "recruitment", 650.0, "person"),
            ("ED-LEGAL-PL", "Work Permit / Legalization PL", "legalization", 450.0, "person"),
            ("ED-TARGET-META", "Meta Lead Ads — Hiring Campaign", "marketing", 900.0, "package"),
        ]
        service_ids: dict[str, str] = {}
        for code, name, category, price, unit in services_spec:
            sid = uid()
            service_ids[code] = sid
            db.add(
                Service(
                    id=sid,
                    tenant_id=TENANT_ID,
                    code=code,
                    name=name,
                    description=f"EuroDrive demo service — {name}",
                    category=category,
                    unit=unit,
                    base_price=price,
                    estimated_cost=price * 0.35,
                    cost_currency="EUR",
                    currency="EUR",
                    vat_rate=23,
                    requires_schedule=False,
                    requires_candidate=category == "legalization",
                    is_active=True,
                    meta={"screenshot_pack": PACK},
                )
            )
        await db.flush()

        # --- Service orders (/app/orders) ---
        # Constraint: exactly one of candidate_id / vacancy_id / company_id
        svc_orders = [
            {
                "id": "d4444444-4444-4444-8444-444444444401",
                "company_id": CLIENT_TL_ID,
                "status": "in_progress",
                "service": "ED-RECRUIT-CE",
                "qty": 10,
                "notes": "TransLogistik — CE batch hire Q3",
            },
            {
                "id": "d4444444-4444-4444-8444-444444444402",
                "company_id": CLIENT_BH_ID,
                "status": "confirmed",
                "service": "ED-RECRUIT-CE",
                "qty": 5,
                "notes": "Baltic Haulage — PL–DE corridor",
            },
            {
                "id": "d4444444-4444-4444-8444-444444444403",
                "company_id": "b2222222-2222-4222-8222-222222222204",
                "status": "completed",
                "service": "ED-RECRUIT-CE",
                "qty": 4,
                "notes": "Nordic Fleet — completed placement",
            },
            {
                "id": "d4444444-4444-4444-8444-444444444404",
                "company_id": "b2222222-2222-4222-8222-222222222205",
                "status": "draft",
                "service": "ED-RECRUIT-WH",
                "qty": 15,
                "notes": "RhineCargo warehouse staffing draft",
            },
            {
                "id": "d4444444-4444-4444-8444-444444444405",
                "company_id": CLIENT_TL_ID,
                "status": "in_progress",
                "service": "ED-TARGET-META",
                "qty": 1,
                "notes": "Meta ads package for CE Drivers EU vacancy",
            },
        ]
        for so in svc_orders:
            code = so["service"]
            svc_id = service_ids[code]
            base = float(next(s[3] for s in services_spec if s[0] == code))
            qty = float(so["qty"])
            net = base * qty
            vat = round(net * 0.23, 2)
            order = ServiceOrder(
                id=so["id"],
                tenant_id=TENANT_ID,
                own_company_id=OWN_COMPANY_ID,
                company_id=so.get("company_id"),
                vacancy_id=so.get("vacancy_id"),
                status=so["status"],
                total_amount=net + vat,
                vat_total=vat,
                currency="EUR",
                requested_by=IGOR_ID,
                assigned_to=IGOR_ID,
                start_date=date.today() - timedelta(days=14),
                end_date=date.today() + timedelta(days=45) if so["status"] != "completed" else date.today() - timedelta(days=2),
                notes=f"{so['notes']} [{PACK}]",
                audit={"screenshot_pack": PACK},
            )
            db.add(order)
            db.add(
                ServiceItem(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    order_id=so["id"],
                    service_id=svc_id,
                    qty=qty,
                    unit_price=base,
                    estimated_cost=base * 0.35 * qty,
                    cost_currency="EUR",
                    cost_status="estimated",
                    vat_rate=23,
                    amount=net + vat,
                    status="delivered" if so["status"] == "completed" else "in_progress" if so["status"] == "in_progress" else "pending",
                    meta={"screenshot_pack": PACK},
                )
            )
        await db.flush()

        # --- Sales orders (/app/sales/orders) ---
        sales_specs = [
            {
                "id": "e5555555-5555-4555-8555-555555555501",
                "company_id": CLIENT_TL_ID,
                "title": "TransLogistik — CE Drivers retainer",
                "status": "in_progress",
                "lines": [
                    ("CE Drivers EU — placement", "CE Driver", "EU", 10, 1200, "candidate_hired"),
                    ("Guarantee cover (90 days)", "Guarantee", "EU", 10, 150, "guarantee_period_passed"),
                ],
            },
            {
                "id": "e5555555-5555-4555-8555-555555555502",
                "company_id": CLIENT_BH_ID,
                "title": "Baltic Haulage — PL–DE staffing",
                "status": "open",
                "lines": [
                    ("C+E Drivers PL–DE", "CE Driver", "PL/DE", 8, 1100, "candidate_started_work"),
                ],
            },
            {
                "id": "e5555555-5555-4555-8555-555555555503",
                "company_id": "b2222222-2222-4222-8222-222222222204",
                "title": "Nordic Fleet — completed placements",
                "status": "completed",
                "lines": [
                    ("CE Drivers Nordics", "CE Driver", "SE/NO", 4, 1400, "headcount_completed"),
                ],
            },
            {
                "id": "e5555555-5555-4555-8555-555555555504",
                "company_id": "b2222222-2222-4222-8222-222222222206",
                "title": "Alpina Logistics — ADR tank drivers",
                "status": "open",
                "lines": [
                    ("ADR Tank Drivers", "ADR Driver", "CH/DE", 6, 1600, "candidate_hired"),
                ],
            },
        ]
        for spec in sales_specs:
            db.add(
                SalesOrder(
                    id=spec["id"],
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    client_account_id=account_by_company.get(spec["company_id"]),
                    company_id=spec["company_id"],
                    payer_company_id=spec["company_id"],
                    title=spec["title"],
                    status=spec["status"],
                    currency="EUR",
                    payment_term_days=14,
                    payment_model="per_hire",
                    vat_rate=money(23),
                    guarantee_days=90,
                    invoice_right_policy="on_trigger",
                    billing_notes=f"Demo sales order [{PACK}]",
                    commercial_snapshot={"screenshot_pack": PACK},
                )
            )
        await db.flush()
        for spec in sales_specs:
            for idx, (title, role, loc, qty, rate, trigger) in enumerate(spec["lines"]):
                line_id = uid()
                db.add(
                    SalesOrderLine(
                        id=line_id,
                        tenant_id=TENANT_ID,
                        sales_order_id=spec["id"],
                        title=title,
                        role_label=role,
                        location=loc,
                        quantity_needed=qty,
                        unit_rate=money(rate),
                        charge_unit="person",
                        billing_trigger=trigger,
                        guarantee_days=90,
                        status="completed" if spec["status"] == "completed" else "in_progress" if spec["status"] == "in_progress" else "open",
                        sort_order=idx,
                    )
                )
        await db.flush()
        for spec in sales_specs:
            # Billables after orders+lines exist (FK order).
            for idx, (_title, _role, _loc, qty, rate, trigger) in enumerate(spec["lines"]):
                line_rows = (
                    await db.execute(
                        select(SalesOrderLine.id).where(
                            SalesOrderLine.sales_order_id == spec["id"],
                            SalesOrderLine.sort_order == idx,
                        )
                    )
                ).all()
                line_id = line_rows[0][0] if line_rows else None
                bill_status = "invoiced" if spec["status"] == "completed" else "pending"
                db.add(
                    SalesBillableItem(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        sales_order_id=spec["id"],
                        sales_order_line_id=line_id,
                        trigger_code=trigger,
                        amount=money(rate * min(qty, 2)),
                        currency="EUR",
                        quantity=money(min(qty, 2)),
                        source_entity_type="company",
                        source_entity_id=spec["company_id"],
                        status=bill_status,
                        notes=f"Demo billable [{PACK}]",
                    )
                )
        await db.flush()

        # --- Invoices (/app/invoices) ---
        invoice_specs = [
            {
                "number": "ED-DEMO-2026/001",
                "company_id": CLIENT_TL_ID,
                "service_order_id": "d4444444-4444-4444-8444-444444444401",
                "status": InvoiceStatus.sent.value,
                "days_ago": 12,
                "due_in": 2,
                "lines": [("CE Driver Recruitment × 5 placements", 5, 1200)],
                "paid": False,
            },
            {
                "number": "ED-DEMO-2026/002",
                "company_id": "b2222222-2222-4222-8222-222222222204",
                "service_order_id": "d4444444-4444-4444-8444-444444444403",
                "status": InvoiceStatus.paid.value,
                "days_ago": 35,
                "due_in": -10,
                "lines": [("CE Drivers Nordics — 4 hires", 4, 1400)],
                "paid": True,
            },
            {
                "number": "ED-DEMO-2026/003",
                "company_id": CLIENT_BH_ID,
                "service_order_id": "d4444444-4444-4444-8444-444444444402",
                "status": InvoiceStatus.overdue.value,
                "days_ago": 40,
                "due_in": -12,
                "lines": [("C+E Drivers PL–DE × 3", 3, 1100), ("Legalization support", 3, 450)],
                "paid": False,
            },
            {
                "number": "ED-DEMO-2026/004",
                "company_id": CLIENT_TL_ID,
                "service_order_id": None,
                "status": InvoiceStatus.draft.value,
                "days_ago": 1,
                "due_in": 14,
                "lines": [("Meta Lead Ads — Hiring Campaign", 1, 900)],
                "paid": False,
            },
            {
                "number": "ED-DEMO-2026/005",
                "company_id": "b2222222-2222-4222-8222-222222222206",
                "service_order_id": None,
                "status": InvoiceStatus.issued.value,
                "days_ago": 5,
                "due_in": 9,
                "lines": [("ADR Tank Drivers — retainer deposit", 1, 4800)],
                "paid": False,
            },
        ]
        for inv in invoice_specs:
            subtotal = money(0)
            for _, qty, price in inv["lines"]:
                subtotal += money(qty * price)
            vat_total = (subtotal * money("0.23")).quantize(Decimal("0.01"))
            total = subtotal + vat_total
            issue = date.today() - timedelta(days=inv["days_ago"])
            due = date.today() + timedelta(days=inv["due_in"])
            paid_amount = total if inv["paid"] else money(0)
            invoice_id = uid()
            db.add(
                Invoice(
                    id=invoice_id,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    company_id=inv["company_id"],
                    service_order_id=inv["service_order_id"],
                    invoice_number=inv["number"],
                    issue_date=issue,
                    due_date=due,
                    currency="EUR",
                    subtotal=subtotal,
                    vat_total=vat_total,
                    total_amount=total,
                    paid_amount=paid_amount,
                    status=inv["status"],
                    payment_date=issue + timedelta(days=7) if inv["paid"] else None,
                    created_by=IGOR_ID,
                    notes=f"EuroDrive screenshot invoice [{PACK}]",
                    billing_details={
                        "screenshot_pack": PACK,
                        "issuer_name": own.legal_name or own.name,
                        "issuer_tax_id": own.tax_id,
                    },
                )
            )
            for line_no, (desc, qty, price) in enumerate(inv["lines"], start=1):
                db.add(
                    InvoiceItem(
                        id=uid(),
                        invoice_id=invoice_id,
                        line_no=line_no,
                        description=desc,
                        qty=money(qty),
                        unit_price=money(price),
                        vat_rate=money(23),
                    )
                )
            if inv["paid"]:
                db.add(
                    Payment(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        invoice_id=invoice_id,
                        amount=total,
                        currency="EUR",
                        method=PaymentMethod.bank_transfer.value,
                        status=PaymentStatus.confirmed.value,
                        payment_date=issue + timedelta(days=7),
                        reference_number=f"PAY-{inv['number']}",
                    )
                )

        await db.commit()

        # Counts
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": TENANT_ID})
        counts = {
            "companies": (
                await db.execute(text("SELECT count(*) FROM companies WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "vacancies": (
                await db.execute(text("SELECT count(*) FROM vacancies WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "client_accounts": (
                await db.execute(text("SELECT count(*) FROM client_accounts WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "sales_inquiries_leads": (
                await db.execute(
                    text(
                        "SELECT count(*) FROM leads WHERE tenant_id=:t "
                        "AND lead_type='client' AND lead_target_type='client_lead'"
                    ),
                    {"t": TENANT_ID},
                )
            ).scalar(),
            "sales_orders": (
                await db.execute(text("SELECT count(*) FROM sales_orders WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "service_orders": (
                await db.execute(text("SELECT count(*) FROM service_orders WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "invoices": (
                await db.execute(text("SELECT count(*) FROM invoices WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
            "services": (
                await db.execute(text("SELECT count(*) FROM services WHERE tenant_id=:t"), {"t": TENANT_ID})
            ).scalar(),
        }
        print(json.dumps({"ok": True, "pack": PACK, **counts}, indent=2, ensure_ascii=False))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
