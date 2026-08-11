#!/usr/bin/env python3
"""Extend EuroDrive screenshot tenant: campaigns, Meta stats, calls, integrations, inbox."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from backend.app.core.crypto import encrypt_secret
from backend.app.models import Candidate, Lead, MetaLeadCredential, MetaLeadSettings, Tenant, Vacancy
from backend.app.models.campaign import (
    Campaign,
    CampaignFlightSpendEntry,
    CampaignResultAttribution,
    CampaignRun,
    CampaignRunIntakeSource,
    CampaignTarget,
    FlightAdBinding,
)
from backend.app.models.calendar_integration import CalendarConnection
from backend.app.models.communication import (
    CommunicationChannelAccount,
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.models.contact_attempt import ContactAttempt
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import MetaAdsMap
from backend.app.models.tenant_integration_installation import TenantIntegrationInstallation

TENANT_ID = "6f83284f-3b77-4ef4-b8eb-5acdedf26d60"
OWN_COMPANY_ID = "e332a0b9-fe66-468d-b683-7829150f2780"
IGOR_ID = "ced40564-e7e8-4acb-b7a1-305edeefcb85"
ANNA_ID = "a1111111-1111-4111-8111-111111111101"
MARIA_ID = "a1111111-1111-4111-8111-111111111102"
VACANCY_ID = "c3333333-3333-4333-8333-333333333301"
CLIENT_ID = "b2222222-2222-4222-8222-222222222202"
OPERATING_ID = "b2222222-2222-4222-8222-222222222201"

# Deterministic IDs for re-runs
CAMPAIGN_META_ID = "d4444444-4444-4444-8444-444444444401"
FLIGHT_META_ID = "d4444444-4444-4444-8444-444444444402"
CAMPAIGN_TT_ID = "d4444444-4444-4444-8444-444444444403"
FLIGHT_TT_ID = "d4444444-4444-4444-8444-444444444404"
CAMPAIGN_GG_ID = "d4444444-4444-4444-8444-444444444405"
FLIGHT_GG_ID = "d4444444-4444-4444-8444-444444444406"

PROFILE_META_ID = "e5555555-5555-4555-8555-555555555501"
PROFILE_TT_ID = "e5555555-5555-4555-8555-555555555502"
PROFILE_GG_ID = "e5555555-5555-4555-8555-555555555503"
BIND_META_ID = "e5555555-5555-4555-8555-555555555511"
BIND_TT_ID = "e5555555-5555-4555-8555-555555555512"
BIND_GG_ID = "e5555555-5555-4555-8555-555555555513"

ACCT_EMAIL_ID = "f6666666-6666-4666-8666-666666666601"
ACCT_WA_ID = "f6666666-6666-4666-8666-666666666602"
ACCT_TG_ID = "f6666666-6666-4666-8666-666666666603"
ACCT_FB_ID = "f6666666-6666-4666-8666-666666666604"

CRED_META_ID = "f6666666-6666-4666-8666-666666666610"
CAL_GOOGLE_ID = "f6666666-6666-4666-8666-666666666620"

PACK = "eurodrive_v2"

DB_URL = (
    os.environ.get("ASYNC_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or "postgresql+asyncpg://hostflow:hostflow@localhost:5432/hostflow"
)


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


def connected_settings(provider_block: dict) -> dict:
    ts = now().isoformat()
    return {
        **provider_block,
        "connection": {"status": "ok", "last_test_at": ts, "last_ok_at": ts},
        "sync": {"status": "ok", "last_sync_at": ts},
        "screenshot_pack": PACK,
    }


async def main() -> None:
    engine = create_async_engine(DB_URL, future=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": TENANT_ID})

        tenant = (await db.execute(select(Tenant).where(Tenant.id == TENANT_ID))).scalar_one()
        settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
        modules = dict(settings.get("modules") or {})
        modules.update(
            {
                "leads": True,
                "recruitment": True,
                "candidates": True,
                "vacancies": True,
                "documents": True,
                "companies": True,
                "communications": True,
                "marketing": True,
                "client_portal": True,
            }
        )
        settings["modules"] = modules
        # Enable communications entitlements so inbox is usable
        comm = dict(settings.get("communications") or {})
        entitlements = dict(comm.get("entitlements") or {})
        ent_modules = dict(entitlements.get("modules") or {})
        for key in ("messages", "email", "calendar", "planner", "communicationsAdmin"):
            ent_modules[key] = {"enabled": True, "planRequired": None, "seatScoped": False}
        entitlements["modules"] = ent_modules
        comm["entitlements"] = entitlements
        settings["communications"] = comm
        settings["screenshot_pack_v2"] = True
        tenant.settings = settings
        db.add(tenant)

        # --- wipe previous v2 demo rows (idempotent) ---
        await db.execute(delete(CampaignFlightSpendEntry).where(CampaignFlightSpendEntry.tenant_id == TENANT_ID))
        await db.execute(delete(CampaignResultAttribution).where(CampaignResultAttribution.tenant_id == TENANT_ID))
        await db.execute(delete(FlightAdBinding).where(FlightAdBinding.tenant_id == TENANT_ID))
        await db.execute(delete(CampaignRunIntakeSource).where(CampaignRunIntakeSource.tenant_id == TENANT_ID))
        await db.execute(delete(CampaignTarget).where(CampaignTarget.tenant_id == TENANT_ID))
        await db.execute(delete(CampaignRun).where(CampaignRun.tenant_id == TENANT_ID))
        await db.execute(delete(Campaign).where(Campaign.tenant_id == TENANT_ID))
        await db.execute(delete(IntakeSourceBinding).where(IntakeSourceBinding.tenant_id == TENANT_ID))
        await db.execute(delete(IntakeSourceProfile).where(IntakeSourceProfile.tenant_id == TENANT_ID))
        await db.execute(delete(CommunicationMessage).where(CommunicationMessage.tenant_id == TENANT_ID))
        await db.execute(delete(CommunicationThread).where(CommunicationThread.tenant_id == TENANT_ID))
        await db.execute(delete(CommunicationChannelAccount).where(CommunicationChannelAccount.tenant_id == TENANT_ID))
        await db.execute(delete(MetaLeadCredential).where(MetaLeadCredential.tenant_id == TENANT_ID))
        await db.execute(delete(MetaAdsMap).where(MetaAdsMap.tenant_id == TENANT_ID))
        await db.execute(delete(CalendarConnection).where(CalendarConnection.tenant_id == TENANT_ID))
        # contact attempts via candidates of this tenant
        cand_ids = [
            r[0]
            for r in (
                await db.execute(select(Candidate.id).where(Candidate.tenant_id == TENANT_ID))
            ).all()
        ]
        if cand_ids:
            await db.execute(delete(ContactAttempt).where(ContactAttempt.candidate_id.in_(cand_ids)))
        await db.execute(
            delete(TenantIntegrationInstallation).where(
                TenantIntegrationInstallation.tenant_id == TENANT_ID
            )
        )
        await db.flush()

        # --- Meta credential (hub Active) ---
        db.add(
            MetaLeadCredential(
                id=CRED_META_ID,
                tenant_id=TENANT_ID,
                label="EuroDrive Meta — EU Drivers Jobs",
                status="active",
                encrypted_secret=encrypt_secret("demo-app-secret"),
                encrypted_access_token=encrypt_secret("EAAG-demo-page-token"),
                encrypted_ad_account_id=encrypt_secret("act_120330000000000001"),
                encrypted_page_id=encrypt_secret("page_eu_drivers_jobs"),
                last_verified_at=now() - timedelta(hours=2),
                last_rotation_at=now() - timedelta(days=14),
            )
        )
        meta_settings = (
            await db.execute(select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == TENANT_ID))
        ).scalar_one_or_none()
        if meta_settings is None:
            meta_settings = MetaLeadSettings(tenant_id=TENANT_ID)
        meta_settings.default_company_id = CLIENT_ID
        meta_settings.fallback_recruiter_id = IGOR_ID
        meta_settings.auto_create_enabled = True
        meta_settings.last_signature_status = "ok"
        meta_settings.last_webhook_check_at = now() - timedelta(minutes=12)
        meta_settings.webhook_url = "https://hostflow.cc/api/v1/meta/webhook"
        meta_settings.webhook_verify_token = "eurodrive-demo-verify"
        meta_settings.pull_field_data_from_graph = True
        meta_settings.leads_processing_mode_v1 = "auto"
        meta_settings.leads_auto_convert_on_fit_v1 = True
        db.add(meta_settings)

        # --- Intake sources: Meta / TikTok / Google Ads stand-in ---
        profiles = [
            (
                PROFILE_META_ID,
                "meta_ce_drivers",
                "Meta Lead Ads — CE Drivers PL/DE",
                "meta",
                "paid",
                "form_ce_drivers",
                "CE Drivers Lead Form",
                BIND_META_ID,
            ),
            (
                PROFILE_TT_ID,
                "tiktok_ce_drivers",
                "TikTok Lead Gen — CE Drivers EU",
                "tiktok",
                "paid",
                "tt_form_ce_eu",
                "TikTok Instant Form CE",
                BIND_TT_ID,
            ),
            (
                PROFILE_GG_ID,
                "google_ce_drivers",
                "Google Ads Lead Form — CE Drivers",
                "api",
                "paid",
                "gads_form_ce",
                "Google Lead Form CE",
                BIND_GG_ID,
            ),
        ]
        for pid, code, name, provider, channel, ext_key, label, bind_id in profiles:
            db.add(
                IntakeSourceProfile(
                    id=pid,
                    tenant_id=TENANT_ID,
                    code=code,
                    name=name,
                    provider=provider,
                    channel=channel,
                    own_company_id=OWN_COMPANY_ID,
                    route_intent="candidate_application",
                    pipeline_preset="candidate",
                    form_type="lead_form",
                    lead_type="candidate",
                    lead_target_type="candidate",
                    is_active=True,
                    default_assignee_id=IGOR_ID,
                    default_language="en",
                    mapping_rules=[
                        {"from": "full_name", "to": "full_name"},
                        {"from": "email", "to": "email"},
                        {"from": "phone_number", "to": "phone"},
                    ],
                    notes=f"Screenshot pack {PACK}",
                    publication_config_v1={"screenshot_pack": PACK},
                )
            )
        await db.flush()
        for pid, code, name, provider, channel, ext_key, label, bind_id in profiles:
            db.add(
                IntakeSourceBinding(
                    id=bind_id,
                    tenant_id=TENANT_ID,
                    intake_source_profile_id=pid,
                    provider=provider if provider != "api" else "website",
                    external_key=ext_key,
                    external_key_secondary="page_eu_drivers_jobs" if provider == "meta" else "",
                    label=label,
                    is_active=True,
                    priority=10,
                )
            )
        await db.flush()

        # --- Campaigns + flights ---
        campaigns_spec = [
            (
                CAMPAIGN_META_ID,
                FLIGHT_META_ID,
                "CE Drivers EU — Meta Lead Ads",
                "hiring",
                "applications",
                "meta",
                "120330000000000001",
                PROFILE_META_ID,
                Decimal("1840.50"),
            ),
            (
                CAMPAIGN_TT_ID,
                FLIGHT_TT_ID,
                "CE Drivers EU — TikTok Lead Gen",
                "lead_generation",
                "qualified_leads",
                "tiktok",
                "tt_ad_77881234",
                PROFILE_TT_ID,
                Decimal("620.00"),
            ),
            (
                CAMPAIGN_GG_ID,
                FLIGHT_GG_ID,
                "CE Drivers EU — Google Ads Leads",
                "lead_generation",
                "cost_per_lead",
                "google",
                "gads_ad_99001122",
                PROFILE_GG_ID,
                Decimal("940.75"),
            ),
        ]
        for camp_id, flight_id, name, goal, kpi, provider, ad_id, profile_id, spend in campaigns_spec:
            db.add(
                Campaign(
                    id=camp_id,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    name=name,
                    description=f"Active acquisition campaign for {VACANCY_ID}",
                    status="active",
                    goal_type=goal,
                    primary_kpi=kpi,
                    current_flight_id=flight_id,
                    created_by_user_id=IGOR_ID,
                )
            )
            db.add(
                CampaignRun(
                    id=flight_id,
                    tenant_id=TENANT_ID,
                    campaign_id=camp_id,
                    code="flight_1",
                    name="Flight 1 — August",
                    status="active",
                    starts_at=now() - timedelta(days=18),
                    ends_at=now() + timedelta(days=12),
                )
            )
            db.add(
                CampaignTarget(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    campaign_id=camp_id,
                    target_type="vacancy",
                    target_id=VACANCY_ID,
                    target_module="recruitment",
                    route_intent="candidate_application",
                    role="primary",
                    sort_order=0,
                )
            )
            db.add(
                CampaignRunIntakeSource(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    campaign_run_id=flight_id,
                    intake_source_profile_id=profile_id,
                    role="primary",
                    is_active=True,
                )
            )
            db.add(
                FlightAdBinding(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    provider=provider,
                    provider_ad_id=str(ad_id),
                    campaign_id=camp_id,
                    campaign_run_id=flight_id,
                    is_active=True,
                )
            )
            await db.flush()
            # Spend entries (stats)
            for days_ago, amount in ((14, spend * Decimal("0.35")), (7, spend * Decimal("0.40")), (1, spend * Decimal("0.25"))):
                db.add(
                    CampaignFlightSpendEntry(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        campaign_id=camp_id,
                        campaign_run_id=flight_id,
                        amount=amount.quantize(Decimal("0.01")),
                        currency="EUR",
                        note=f"Daily spend snapshot T-{days_ago}d",
                    )
                )

        # Attribute some leads/candidates to Meta campaign
        leads = (
            await db.execute(select(Lead).where(Lead.tenant_id == TENANT_ID, Lead.source == "meta"))
        ).scalars().all()
        for lead in leads[:4]:
            db.add(
                CampaignResultAttribution(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    campaign_id=CAMPAIGN_META_ID,
                    campaign_run_id=FLIGHT_META_ID,
                    result_type="lead",
                    result_id=lead.id,
                    submission_id=str(lead.external_id or lead.id)[:36],
                    lead_id=lead.id,
                    route_intent="candidate_application",
                    endpoint_intake_source_profile_id=PROFILE_META_ID,
                    routing_source="meta",
                )
            )

        db.add(
            MetaAdsMap(
                ad_id=120330000000000001,
                tenant_id=TENANT_ID,
                vacancy_id=VACANCY_ID,
                note="EuroDrive CE Drivers — Meta ad binding",
            )
        )

        # Vacancy acquisition extras (UI metrics block)
        vacancy = (await db.execute(select(Vacancy).where(Vacancy.id == VACANCY_ID))).scalar_one()
        extra = {}
        if vacancy.extra:
            try:
                extra = json.loads(vacancy.extra) if isinstance(vacancy.extra, str) else dict(vacancy.extra)
            except Exception:
                extra = {}
        extra["acquisition_v1"] = {
            "version": 2,
            "screenshot_pack": PACK,
            "insights": {
                "provider": "meta",
                "spend": 1840.5,
                "impressions": 128400,
                "clicks": 3120,
                "ctr": 2.43,
                "leads": 86,
                "cpl": 21.4,
                "currency": "EUR",
                "as_of": now().isoformat(),
                "status": "ok",
            },
            "activities": [
                {
                    "id": "act_meta_ce",
                    "channel_type": "meta",
                    "type": "meta",
                    "name": "CE Drivers Meta",
                    "lifecycle": "active",
                    "status": "active",
                    "campaign_id": CAMPAIGN_META_ID,
                    "flight_id": FLIGHT_META_ID,
                },
                {
                    "id": "act_tiktok_ce",
                    "channel_type": "tiktok",
                    "type": "tiktok",
                    "name": "CE Drivers TikTok",
                    "lifecycle": "active",
                    "status": "active",
                    "campaign_id": CAMPAIGN_TT_ID,
                    "flight_id": FLIGHT_TT_ID,
                },
                {
                    "id": "act_google_ce",
                    "channel_type": "google",
                    "type": "google",
                    "name": "CE Drivers Google Ads",
                    "lifecycle": "active",
                    "status": "active",
                    "campaign_id": CAMPAIGN_GG_ID,
                    "flight_id": FLIGHT_GG_ID,
                },
            ],
        }
        extra["acquisition_v1"]["channels"] = extra["acquisition_v1"]["activities"]
        vacancy.extra = json.dumps(extra, ensure_ascii=False)
        db.add(vacancy)

        # --- Integration installations (marketplace) ---
        for offer_key in (
            "meta_leads",
            "gmail",
            "google_workspace",
            "google_calendar",
            "google_drive",
            "google_contacts",
            "whatsapp",
            "telegram",
        ):
            db.add(
                TenantIntegrationInstallation(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    offer_key=offer_key,
                    offer_kind="core_integration",
                    status="active",
                    settings_json={
                        "connected": True,
                        "label": offer_key,
                        "screenshot_pack": PACK,
                        "last_ok_at": now().isoformat(),
                    },
                )
            )

        db.add(
            CalendarConnection(
                id=CAL_GOOGLE_ID,
                tenant_id=TENANT_ID,
                user_id=IGOR_ID,
                provider="google",
                account_ref="igor.tatarynovich@gmail.com",
                status="active",
                scopes_json=["calendar.events", "calendar.readonly"],
                token_meta_json={
                    "has_refresh_token": True,
                    "expires_at": (now() + timedelta(hours=1)).isoformat(),
                    "screenshot_pack": PACK,
                },
                last_error=None,
            )
        )

        # --- Channel accounts (all connected) ---
        tok = encrypt_secret("demo-token")
        db.add(
            CommunicationChannelAccount(
                id=ACCT_EMAIL_ID,
                tenant_id=TENANT_ID,
                channel="email",
                account_label="EuroDrive Ops Gmail",
                inbox_address="ops@eurodrive.example",
                external_account_ref="gmail:ops@eurodrive.example",
                is_active=True,
                settings_json=connected_settings(
                    {
                        "provider": "gmail",
                        "oauth": {
                            "provider": "gmail",
                            "client_id": "demo-google-client",
                            "redirect_uri": "https://hostflow.cc/app/settings/integrations/email",
                            "access_token_encrypted": tok,
                            "refresh_token_encrypted": tok,
                        },
                    }
                ),
            )
        )
        db.add(
            CommunicationChannelAccount(
                id=ACCT_WA_ID,
                tenant_id=TENANT_ID,
                channel="whatsapp",
                account_label="EuroDrive WhatsApp Business",
                inbox_address="+48601234567",
                external_account_ref="wa:48601234567",
                is_active=True,
                settings_json=connected_settings(
                    {
                        "provider": "whatsapp",
                        "whatsapp": {
                            "phone_number_id": "wa_phone_demo",
                            "business_account_id": "wa_biz_demo",
                            "access_token_encrypted": tok,
                        },
                    }
                ),
            )
        )
        db.add(
            CommunicationChannelAccount(
                id=ACCT_TG_ID,
                tenant_id=TENANT_ID,
                channel="telegram",
                account_label="EuroDrive Recruiting Bot",
                inbox_address="@eurodrive_recruit_bot",
                external_account_ref="tg:eurodrive_recruit_bot",
                is_active=True,
                settings_json=connected_settings(
                    {
                        "provider": "telegram",
                        "telegram": {"bot_token_encrypted": tok, "bot_username": "eurodrive_recruit_bot"},
                    }
                ),
            )
        )
        db.add(
            CommunicationChannelAccount(
                id=ACCT_FB_ID,
                tenant_id=TENANT_ID,
                channel="messenger",
                account_label="EU Drivers Jobs Messenger",
                inbox_address="page_eu_drivers_jobs",
                external_account_ref="fb:page_eu_drivers_jobs",
                is_active=True,
                settings_json=connected_settings(
                    {
                        "provider": "messenger",
                        "messenger": {"page_id": "page_eu_drivers_jobs", "access_token_encrypted": tok},
                    }
                ),
            )
        )

        await db.flush()

        # --- Inbox threads + inbound messages ---
        candidates = (
            await db.execute(select(Candidate).where(Candidate.tenant_id == TENANT_ID))
        ).scalars().all()
        by_name = {f"{c.first_name} {c.last_name}": c for c in candidates}

        inbox_specs = [
            (
                "whatsapp",
                ACCT_WA_ID,
                "Andrei Kovalenko",
                "+48500100020",
                "Cześć, aplikowałem na CE Drivers EU. Kiedy możecie oddzwonić?",
                ANNA_ID,
            ),
            (
                "whatsapp",
                ACCT_WA_ID,
                "Piotr Wójcik",
                "+48500100022",
                "Mam Code 95 ważny do 2028. Wysłać skan?",
                IGOR_ID,
            ),
            (
                "telegram",
                ACCT_TG_ID,
                "Olena Tkachuk",
                "@olena_tk",
                "Добрый день! Интересует вакансия CE Drivers EU.",
                MARIA_ID,
            ),
            (
                "messenger",
                ACCT_FB_ID,
                "Ivan Romanov",
                "fb_psid_ivan",
                "Hi, I filled your Facebook lead form today.",
                ANNA_ID,
            ),
            (
                "email",
                ACCT_EMAIL_ID,
                "Sergey Morozov",
                "sergey.morozov@example.com",
                "Please find attached my CE licence scan. When is the next step?",
                MARIA_ID,
            ),
            (
                "email",
                ACCT_EMAIL_ID,
                "Klaus Meier",
                "klaus.meier@translogistik.example",
                "Can you send 3 shortlisted CE drivers for Hamburg start next week?",
                IGOR_ID,
            ),
        ]

        for i, (channel, acct_id, who, address, body, assignee) in enumerate(inbox_specs):
            cand = by_name.get(who)
            thread_id = uid()
            msg_at = now() - timedelta(minutes=15 + i * 17)
            subject = None
            if channel == "email":
                subject = (
                    "Re: CE Drivers EU — documents"
                    if "Sergey" in who
                    else "Need shortlist for Hamburg — TransLogistik"
                )
            db.add(
                CommunicationThread(
                    id=thread_id,
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    channel=channel,
                    channel_account_id=acct_id,
                    channel_thread_ref=f"{channel}:{address}",
                    subject=subject,
                    status="open",
                    direction_hint="inbound",
                    entity_type="candidate" if cand else "company",
                    entity_id=cand.id if cand else CLIENT_ID,
                    linked_candidate_id=cand.id if cand else None,
                    linked_company_id=CLIENT_ID,
                    owner_id=IGOR_ID,
                    assignee_id=assignee,
                    queue_assigned_by="manual",
                    priority="high" if i < 2 else "normal",
                    sla_due_at=now() + timedelta(hours=4),
                    participants_json={
                        "external": [{"label": who, "address": address}],
                        "internal": [{"user_id": assignee}],
                    },
                    tags_json=["inbound", "screenshot", channel],
                    thread_meta={"screenshot_pack": PACK, "provider": channel},
                    last_message_at=msg_at,
                    last_inbound_at=msg_at,
                    last_message_preview=body[:180],
                    unread_count=1 if i < 4 else 0,
                    is_archived=False,
                    work_version=1,
                )
            )
            db.add(
                CommunicationMessage(
                    id=uid(),
                    tenant_id=TENANT_ID,
                    own_company_id=OWN_COMPANY_ID,
                    thread_id=thread_id,
                    channel=channel,
                    message_type="email" if channel == "email" else "text",
                    direction="inbound",
                    sender_type="candidate" if cand else "client",
                    sender_id=cand.id if cand else None,
                    sender_label=who,
                    sender_address=address,
                    recipient_type="user",
                    recipient_id=assignee,
                    recipient_label="EuroDrive",
                    recipient_address="ops@eurodrive.example" if channel == "email" else None,
                    subject=subject,
                    body_text=body,
                    body_html=f"<p>{body}</p>" if channel == "email" else None,
                    attachments_json=[],
                    payload={"screenshot_pack": PACK, "inbound": True},
                    external_message_ref=f"{channel}_msg_{i}",
                    delivery_status="delivered",
                    sent_at=msg_at,
                    delivered_at=msg_at,
                )
            )
            # one outbound reply on first email for mixed timeline
            if channel == "email" and i == 4:
                out_at = msg_at + timedelta(minutes=40)
                db.add(
                    CommunicationMessage(
                        id=uid(),
                        tenant_id=TENANT_ID,
                        own_company_id=OWN_COMPANY_ID,
                        thread_id=thread_id,
                        channel="email",
                        message_type="email",
                        direction="outbound",
                        sender_type="user",
                        sender_id=MARIA_ID,
                        sender_label="Maria Nowak",
                        sender_address="ops@eurodrive.example",
                        recipient_type="candidate",
                        recipient_id=cand.id if cand else None,
                        recipient_label=who,
                        recipient_address=address,
                        subject=subject,
                        body_text="Thanks Sergey — we received the licence. Please upload Code 95 when ready.",
                        body_html="<p>Thanks Sergey — we received the licence. Please upload Code 95 when ready.</p>",
                        attachments_json=[],
                        payload={"screenshot_pack": PACK},
                        external_message_ref=f"email_out_{i}",
                        delivery_status="sent",
                        sent_at=out_at,
                        delivered_at=out_at,
                    )
                )

        # --- Calls / contact attempts ---
        call_targets = [
            ("Andrei Kovalenko", ANNA_ID, "answered", "Interested, send vacancy details on WhatsApp"),
            ("Piotr Wójcik", IGOR_ID, "no_answer", "Left voicemail"),
            ("Olena Tkachuk", MARIA_ID, "answered", "Confirmed experience 3y CE"),
            ("Sergey Morozov", MARIA_ID, "answered", "Documents follow-up scheduled"),
            ("Ivan Romanov", ANNA_ID, "unavailable", "Busy — retry tomorrow"),
            ("Alex Bondar", IGOR_ID, "wrong_number", "Number changed"),
        ]
        for idx, (who, user_id, result, note) in enumerate(call_targets):
            cand = by_name.get(who)
            if not cand:
                continue
            attempted = now() - timedelta(hours=3 + idx)
            db.add(
                ContactAttempt(
                    id=uid(),
                    candidate_id=cand.id,
                    attempt_number=1,
                    attempted_at=attempted,
                    attempted_by_user_id=user_id,
                    channel="call",
                    result=result,
                    note=note,
                )
            )
            if result == "no_answer":
                db.add(
                    ContactAttempt(
                        id=uid(),
                        candidate_id=cand.id,
                        attempt_number=2,
                        attempted_at=attempted + timedelta(hours=5),
                        attempted_by_user_id=user_id,
                        channel="whatsapp",
                        result="answered",
                        note="Reached on WhatsApp after missed call",
                    )
                )

        await db.commit()
        print(
            json.dumps(
                {
                    "ok": True,
                    "campaigns": 3,
                    "flights": 3,
                    "intake_sources": ["meta", "tiktok", "google/api"],
                    "channel_accounts": ["email/gmail", "whatsapp", "telegram", "messenger"],
                    "inbox_threads": len(inbox_specs),
                    "calls": len(call_targets),
                    "integrations_active": [
                        "meta_leads",
                        "gmail",
                        "google_*",
                        "whatsapp",
                        "telegram",
                    ],
                    "meta_credential": True,
                    "login": "igor.tatarynovich@gmail.com",
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
