#!/usr/bin/env python3
"""One-off: seed screenshot-ready demo for igor.tatarynovich@gmail.com tenant.

Renames jokey workspace names and fills companies, vacancy, Meta leads,
pipeline candidates, recruiters, and documents.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from backend.app.models import Candidate, Company, Lead, MetaLeadSettings, OwnCompany, Tenant, User, Vacancy
from backend.app.models.document import Document
from backend.app.models.enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.models.user import Role
from backend.app.services.recruitment_funnel_bootstrap import (
    bootstrap_recruitment_funnels_for_company,
)

TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"
OWN_COMPANY_ID = "e332a0b9-fe66-468d-b683-7829150f2780"
IGOR_ID = "ced40564-e7e8-4acb-b7a1-305edeefcb85"

TENANT_NAME = "EuroDrive Recruiting"
OWN_COMPANY_NAME = "EuroDrive Sp. z o.o."
OWN_LEGAL = "EuroDrive Spółka z ograniczoną odpowiedzialnością"
CLIENT_NAME = "TransLogistik GmbH"
CLIENT2_NAME = "Baltic Haulage Sp. z o.o."
VACANCY_TITLE = "CE Drivers EU"

DB_URL = (
    os.environ.get("ASYNC_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
)


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


async def main() -> None:
    engine = create_async_engine(DB_URL, future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": TENANT_ID})

        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == TENANT_ID).limit(1))
        ).scalar_one()
        tenant.name = TENANT_NAME
        tenant.slug = "eurodrive-recruiting"
        tenant.workspace_label = TENANT_NAME
        tenant.description = "EU CE driver recruitment agency — B2B HostFlow demo workspace"
        settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
        settings["business_type"] = "agency"
        ob = dict(settings.get("onboarding") or {})
        ob["workspace_name"] = OWN_COMPANY_NAME
        ob["industry"] = "transport_logistics"
        ob["demo_seeded"] = True
        ob["screenshot_pack"] = "eurodrive_v1"
        settings["onboarding"] = ob
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
        ):
            modules[key] = True
        settings["modules"] = modules
        tenant.settings = settings
        db.add(tenant)

        own = (
            await db.execute(select(OwnCompany).where(OwnCompany.id == OWN_COMPANY_ID).limit(1))
        ).scalar_one()
        own.name = OWN_COMPANY_NAME
        own.legal_name = OWN_LEGAL
        own.tax_id = "7872153072"
        own.phone = "+48 61 222 10 40"
        own.email = "ops@eurodrive.example"
        own.website = "https://hostflow.cc"
        own.country_code = "PL"
        own.country = "Poland"
        own.city = "Poznań"
        own.address = "ul. Głogowska 41, 60-736 Poznań"
        own.extra = {
            **(own.extra if isinstance(own.extra, dict) else {}),
            "company_role": "operating",
            "company_type": "agency",
            "business_type": "agency",
            "business_model": "recruitment_agency",
            "platform_identity": "recruitment_agency",
            "industry": "transport_logistics",
            "workspace_name": OWN_COMPANY_NAME,
            "screenshot_pack": "eurodrive_v1",
        }
        db.add(own)

        igor = (await db.execute(select(User).where(User.id == IGOR_ID).limit(1))).scalar_one()
        igor.full_name = "Igor Tatarynovich"
        db.add(igor)

        # Teammate recruiters (for ownership column on screenshots)
        pw = igor.password_hash  # reuse hash — avoid slow bcrypt in seed script
        anna_id = "a1111111-1111-4111-8111-111111111101"
        maria_id = "a1111111-1111-4111-8111-111111111102"
        for user_id, email, name, short in (
            (anna_id, "anna.kowalska@eurodrive.example", "Anna Kowalska", "ANNA"),
            (maria_id, "maria.nowak@eurodrive.example", "Maria Nowak", "MARIA"),
        ):
            existing = (
                await db.execute(select(User).where(User.id == user_id).limit(1))
            ).scalar_one_or_none()
            if existing is None:
                by_email = (
                    await db.execute(select(User).where(User.email == email).limit(1))
                ).scalar_one_or_none()
                if by_email is not None:
                    user_id = by_email.id
                    if name.startswith("Anna"):
                        anna_id = user_id
                    else:
                        maria_id = user_id
                    by_email.full_name = name
                    by_email.tenant_id = TENANT_ID
                    by_email.role = Role.employee
                    by_email.is_active = True
                    db.add(by_email)
                else:
                    db.add(
                        User(
                            id=user_id,
                            email=email,
                            password_hash=pw,
                            role=Role.employee,
                            tenant_id=TENANT_ID,
                            full_name=name,
                            short_id=short,
                            is_active=True,
                            preferences={},
                            extra={"screenshot_pack": "eurodrive_v1"},
                        )
                    )
            else:
                existing.full_name = name
                existing.tenant_id = TENANT_ID
                existing.role = Role.employee
                existing.is_active = True
                db.add(existing)

        await db.flush()

        # Wipe previous junk candidates/leads/docs for this tenant (keep structure clean)
        cand_ids = [
            r[0]
            for r in (
                await db.execute(select(Candidate.id).where(Candidate.tenant_id == TENANT_ID))
            ).all()
        ]
        if cand_ids:
            await db.execute(delete(Document).where(Document.candidate_id.in_(cand_ids)))
        await db.execute(delete(Candidate).where(Candidate.tenant_id == TENANT_ID))
        await db.execute(delete(Lead).where(Lead.tenant_id == TENANT_ID))
        await db.execute(delete(Vacancy).where(Vacancy.tenant_id == TENANT_ID))
        # Keep non-demo companies if any; remove previous screenshot pack companies
        old_cos = (
            await db.execute(select(Company).where(Company.tenant_id == TENANT_ID))
        ).scalars().all()
        for co in old_cos:
            extra = co.extra if isinstance(co.extra, dict) else {}
            if extra.get("screenshot_pack") == "eurodrive_v1" or co.name in {
                "Demo client (sample)",
                CLIENT_NAME,
                CLIENT2_NAME,
                OWN_COMPANY_NAME,
            }:
                await db.delete(co)
        await db.flush()

        operating_id = "b2222222-2222-4222-8222-222222222201"
        client_id = "b2222222-2222-4222-8222-222222222202"
        client2_id = "b2222222-2222-4222-8222-222222222203"

        operating = Company(
            id=operating_id,
            tenant_id=TENANT_ID,
            name=OWN_COMPANY_NAME,
            legal_name=OWN_LEGAL,
            tax_id="7872153072",
            phone="+48 61 222 10 40",
            email="ops@eurodrive.example",
            website="https://hostflow.cc",
            country_code="PL",
            country="Poland",
            city="Poznań",
            address="ul. Głogowska 41, 60-736 Poznań",
            contacts={"primary": {"name": "Igor Tatarynovich", "email": "igor.tatarynovich@gmail.com"}},
            party_entity_type="company",
            party_business_roles=None,
            extra={
                "company_role": "operating",
                "company_type": "agency",
                "business_type": "agency",
                "screenshot_pack": "eurodrive_v1",
                "linked_own_company_id": OWN_COMPANY_ID,
            },
        )
        client = Company(
            id=client_id,
            tenant_id=TENANT_ID,
            name=CLIENT_NAME,
            legal_name="TransLogistik Gesellschaft mit beschränkter Haftung",
            tax_id="DE812345678",
            phone="+49 40 555 1200",
            email="hr@translogistik.example",
            website="https://translogistik.example",
            country_code="DE",
            country="Germany",
            city="Hamburg",
            address="Hafenstraße 12, 20457 Hamburg",
            contacts={"primary": {"name": "Klaus Meier", "email": "klaus.meier@translogistik.example"}},
            party_entity_type="company",
            party_business_roles="employer",
            client_stage="active",
            client_source="referral",
            extra={
                "company_role": "client",
                "company_type": "employer",
                "screenshot_pack": "eurodrive_v1",
            },
        )
        client2 = Company(
            id=client2_id,
            tenant_id=TENANT_ID,
            name=CLIENT2_NAME,
            legal_name=CLIENT2_NAME,
            tax_id="PL5250000000",
            phone="+48 58 300 2200",
            email="fleet@baltichaulage.example",
            country_code="PL",
            country="Poland",
            city="Gdańsk",
            address="ul. Portowa 8, 80-855 Gdańsk",
            contacts={},
            party_entity_type="company",
            party_business_roles="employer",
            client_stage="qualified",
            client_source="meta",
            extra={
                "company_role": "client",
                "company_type": "employer",
                "screenshot_pack": "eurodrive_v1",
            },
        )
        db.add_all([operating, client, client2])
        await db.flush()

        await bootstrap_recruitment_funnels_for_company(
            db,
            tenant=tenant,
            company=operating,
            company_type="agency",
            tenant_modules=modules,
        )
        await db.flush()

        from backend.app.services.recruitment_funnel_bootstrap import resolve_company_default_funnel_id

        funnel_id = await resolve_company_default_funnel_id(
            db, tenant_id=TENANT_ID, company_id=operating_id, funnel_type="candidate"
        )

        vacancy_id = "c3333333-3333-4333-8333-333333333301"
        vacancy = Vacancy(
            id=vacancy_id,
            tenant_id=TENANT_ID,
            company_id=client_id,
            own_company_id=OWN_COMPANY_ID,
            title=VACANCY_TITLE,
            description=(
                "International CE drivers for EU routes (DE/NL/BE). "
                "Full-time, Code 95 required, housing support available."
            ),
            location="EU / based DE–PL",
            salary_from="1800",
            salary_to="2400",
            currency="EUR",
            status="open",
            is_active=True,
            is_archived=False,
            employment_type="full_time",
            headcount_target=25,
            funnel_id=funnel_id,
            manager=IGOR_ID,
            extra=json.dumps({"screenshot_pack": "eurodrive_v1", "routes": ["DE", "NL", "BE"]}),
            settings_json={"priority": "high"},
        )
        db.add(vacancy)
        await db.flush()

        # Pipeline candidates matching screenshot storyboard
        specs = [
            ("Andrei", "Kovalenko", "new", "meta", anna_id, "Anna", False),
            ("Ivan", "Romanov", "new", "meta", anna_id, "Anna", False),
            ("Piotr", "Wójcik", "contacted", "meta", IGOR_ID, "Igor", False),
            ("Olena", "Tkachuk", "contacted", "whatsapp", maria_id, "Maria", False),
            ("Sergey", "Morozov", "docs_wait", "whatsapp", maria_id, "Maria", True),
            ("Maria", "Lewandowska", "docs_wait", "meta", anna_id, "Anna", False),
            ("Dmytro", "Shevchenko", "hired", "meta", IGOR_ID, "Igor", False),
            ("Viktor", "Petrenko", "docs_got", "meta", anna_id, "Anna", False),
            ("Natalia", "Horban", "ready_for_handoff", "form", maria_id, "Maria", False),
            ("Alex", "Bondar", "contacted", "meta", IGOR_ID, "Igor", False),
            ("Taras", "Melnyk", "new", "meta", anna_id, "Anna", False),
            ("Yulia", "Savchuk", "processing_by_client", "meta", maria_id, "Maria", False),
        ]
        now_naive = datetime.utcnow()
        cand_by_key: dict[str, str] = {}
        for i, (fn, ln, stage, source, recruiter, manager, docs) in enumerate(specs):
            cid = uid()
            cand_by_key[f"{fn}_{ln}"] = cid
            created = now_naive - timedelta(hours=2 + i * 3)
            c = Candidate(
                id=cid,
                tenant_id=TENANT_ID,
                own_company_id=OWN_COMPANY_ID,
                company_id=client_id,
                vacancy_id=vacancy_id,
                funnel_id=funnel_id,
                first_name=fn,
                last_name=ln,
                first_name_latin=fn,
                last_name_latin=ln,
                email=f"{fn.lower()}.{ln.lower()}@example.com",
                phone=f"+48 500 10{i:02d} {20+i:02d}",
                phone_country_code="+48",
                stage=stage,
                lifecycle_status="active",
                status="active",
                source=source,
                recruiter_id=recruiter,
                manager=manager,
                tags=["CE", "EU routes"] if stage != "new" else ["CE"],
                note="Screenshot demo candidate — EuroDrive pack",
                extra=json.dumps(
                    {
                        "screenshot_pack": "eurodrive_v1",
                        "citizenship": "UA" if fn in {"Andrei", "Olena", "Sergey", "Dmytro", "Viktor", "Natalia", "Taras", "Yulia"} else "PL",
                        "role": "CE driver",
                    }
                ),
                created_at=created,
                updated_at=created if stage == "new" else now_naive - timedelta(minutes=30),
            )
            db.add(c)

        await db.flush()

        # Documents for Sergey (docs checklist screenshot)
        sergey_id = cand_by_key["Sergey_Morozov"]
        doc_specs = [
            ("passport", DocumentStatus.approved, "passport_sergey.pdf"),
            ("driver_license", DocumentStatus.approved, "ce_licence_sergey.pdf"),
            ("code95", DocumentStatus.in_progress, "code95_sergey.pdf"),
            ("residence_permit", DocumentStatus.missing, None),
            ("medical_certificate", DocumentStatus.received, "medical_sergey.pdf"),
        ]
        type_ids = {
            "passport": "8468f68c-983e-4b19-b0a7-de92bc70cac3",
            "driver_license": "428bcb16-eae7-48d2-987b-d8be2054eba8",
            "medical_certificate": "8c64ff6c-9b14-4c47-9a40-6832f0e269fd",
            "code95": "ebd42296-66ce-45d0-8376-033581e17449",
            "residence_permit": "c540049e-e87a-4ea4-b025-b0a6716e41f1",
        }
        for doc_type, status, filename in doc_specs:
            mapped_type = "code_95" if doc_type == "code95" else (
                "residence_card" if doc_type == "residence_permit" else doc_type
            )
            db.add(
                Document(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    candidate_id=sergey_id,
                    company_id=client_id,
                    kind=DocumentKind.driver,
                    doc_type=mapped_type,
                    document_type_id=type_ids.get(doc_type),
                    status=status,
                    filename=filename,
                    path=f"/demo/{filename}" if filename else None,
                    reminder_days_before=30,
                    requested_from=DocumentRequestedFrom.driver,
                    process_type=DocumentProcessType.none,
                    verified_at=now() if status == DocumentStatus.approved else None,
                    meta={"screenshot_pack": "eurodrive_v1"},
                )
            )

        # Meta leads inbox
        meta_leads = [
            ("Andrei", "Kovalenko", "new", 2, "CE Drivers PL"),
            ("Piotr", "Wójcik", "processed", 11, "CE Drivers DE"),
            ("Olena", "Tkachuk", "new", 28, "CE Drivers NL"),
            ("Taras", "Melnyk", "needs_routing", 45, "CE Drivers PL"),
            ("Ivan", "Romanov", "processed", 90, "CE Drivers DE"),
        ]
        for fn, ln, status, mins, form_name in meta_leads:
            lid = uid()
            created = now() - timedelta(minutes=mins)
            payload = {
                "id": f"meta_lead_{fn.lower()}",
                "created_time": created.isoformat(),
                "form_id": "form_ce_drivers",
                "form_name": form_name,
                "page_id": "page_eu_drivers_jobs",
                "page_name": "EU Drivers Jobs — EuroDrive",
                "field_data": [
                    {"name": "full_name", "values": [f"{fn} {ln}"]},
                    {"name": "email", "values": [f"{fn.lower()}.{ln.lower()}@example.com"]},
                    {"name": "phone_number", "values": ["+48500100200"]},
                    {"name": "job_title", "values": ["CE driver"]},
                ],
                "screenshot_pack": "eurodrive_v1",
            }
            db.add(
                Lead(
                    id=lid,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    lead_type="candidate",
                    lead_target_type="candidate",
                    company_id=client_id,
                    vacancy_id=vacancy_id,
                    source="meta",
                    ad_id=120330000000000001,
                    external_id=f"ext_{fn.lower()}_{mins}",
                    payload=payload,
                    normalized={
                        "first_name": fn,
                        "last_name": ln,
                        "email": f"{fn.lower()}.{ln.lower()}@example.com",
                        "phone": "+48500100200",
                        "form_name": form_name,
                    },
                    status=status,
                    stage="new" if status == "new" else "contacted",
                    funnel_id=funnel_id,
                    candidate_id=cand_by_key.get(f"{fn}_{ln}"),
                    created_at=created,
                )
            )

        # Open Applications inbox rows (no candidate_id) — New / In progress for screenshots.
        open_apps = [
            ("Viktor", "Petrenko", "new", 25, "+48500100301"),
            ("Natalia", "Koval", "new", 40, "+48500100302"),
            ("Bohdan", "Lysenko", "needs_routing", 120, "+48500100303"),
            ("Iryna", "Bondar", "processed", 180, "+48500100304"),
        ]
        for fn, ln, status, mins, phone in open_apps:
            ext = f"eurodrive_open_app_{fn.lower()}"
            existing_open = (
                await db.execute(
                    select(Lead).where(
                        Lead.tenant_id == TENANT_ID,
                        Lead.external_id == ext,
                    )
                )
            ).scalar_one_or_none()
            created = now() - timedelta(minutes=mins)
            payload = {
                "id": f"meta_lead_open_{fn.lower()}",
                "created_time": created.isoformat(),
                "form_id": "form_ce_drivers",
                "form_name": "CE Drivers PL",
                "page_id": "page_eu_drivers_jobs",
                "page_name": "EU Drivers Jobs — EuroDrive",
                "field_data": [
                    {"name": "full_name", "values": [f"{fn} {ln}"]},
                    {"name": "email", "values": [f"{fn.lower()}.{ln.lower()}@example.com"]},
                    {"name": "phone_number", "values": [phone]},
                    {"name": "job_title", "values": ["CE driver"]},
                ],
                "screenshot_pack": "eurodrive_v1",
            }
            if existing_open:
                existing_open.status = status
                existing_open.candidate_id = None
                existing_open.payload = payload
                existing_open.normalized = {
                    "first_name": fn,
                    "last_name": ln,
                    "email": f"{fn.lower()}.{ln.lower()}@example.com",
                    "phone": phone,
                    "form_name": "CE Drivers PL",
                }
                existing_open.vacancy_id = vacancy_id
                existing_open.lead_target_type = "candidate_application"
            else:
                db.add(
                    Lead(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        own_company_id=OWN_COMPANY_ID,
                        lead_type="candidate",
                        lead_target_type="candidate_application",
                        company_id=client_id,
                        vacancy_id=vacancy_id,
                        source="meta",
                        ad_id=120330000000000001,
                        external_id=ext,
                        payload=payload,
                        normalized={
                            "first_name": fn,
                            "last_name": ln,
                            "email": f"{fn.lower()}.{ln.lower()}@example.com",
                            "phone": phone,
                            "form_name": "CE Drivers PL",
                        },
                        status=status,
                        stage="new",
                        funnel_id=funnel_id,
                        candidate_id=None,
                        created_at=created,
                    )
                )

        # Meta connection settings (UI shows connected Page)
        existing_meta = (
            await db.execute(
                select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == TENANT_ID).limit(1)
            )
        ).scalar_one_or_none()
        meta_row = existing_meta or MetaLeadSettings(tenant_id=TENANT_ID)
        meta_row.default_company_id = client_id
        meta_row.fallback_recruiter_id = IGOR_ID
        meta_row.auto_create_enabled = True
        meta_row.reroute_after_hours = 4
        meta_row.mask_pii_in_logs = True
        meta_row.webhook_url = "https://hostflow.cc/api/v1/meta/webhook"
        meta_row.webhook_verify_token = "eurodrive-demo-verify"
        meta_row.last_webhook_check_at = now()
        meta_row.last_signature_status = "ok"
        meta_row.pull_field_data_from_graph = True
        meta_row.field_mapping = [
            {"from": "full_name", "to": "full_name"},
            {"from": "email", "to": "email"},
            {"from": "phone_number", "to": "phone"},
        ]
        meta_row.leads_processing_mode_v1 = "auto"
        db.add(meta_row)

        await db.commit()
        print(
            json.dumps(
                {
                    "ok": True,
                    "tenant": TENANT_NAME,
                    "own_company": OWN_COMPANY_NAME,
                    "client": CLIENT_NAME,
                    "vacancy": VACANCY_TITLE,
                    "candidates": len(specs),
                    "meta_leads": len(meta_leads),
                    "recruiters": ["Igor Tatarynovich", "Anna Kowalska", "Maria Nowak"],
                    "login": "igor.tatarynovich@gmail.com",
                    "funnel_id": funnel_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
