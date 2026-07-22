"""PR-A: Legacy Search → Campaign/Flight migration."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.app.acquisition.legacy_search_migration import (
    SCRIPT_VERSION,
    STAMP_KEY,
    derive_desired_state,
    get_stamp,
    is_eligible,
    list_eligible_vacancies,
    migrate_all,
    migrate_one,
    rollback_all,
    vacancy_extra_dict,
)
from backend.app.db.session import async_session_maker
from backend.app.models.campaign import Campaign, CampaignRun, CampaignRunForm, CampaignTarget
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import MetaAdsMap
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data


def test_eligibility_requires_acquisition_signal():
    assert not is_eligible(signals=[])
    assert is_eligible(signals=["lead_form_id"])
    assert is_eligible(signals=["meta_ads_map"])
    assert is_eligible(signals=["launch_search"])


def test_derive_desired_state_matrix():
    vac = Vacancy(
        id=str(uuid4()),
        tenant_id="t",
        company_id="c",
        title="X",
        status="open",
        is_active=True,
    )
    assert derive_desired_state(vac, {}) == "active"

    vac.status = "on_hold"
    assert derive_desired_state(vac, {}) == "paused"

    vac.status = "closed"
    assert derive_desired_state(vac, {}) == "completed"

    vac.status = "open"
    vac.is_archived = True
    assert derive_desired_state(vac, {}) == "completed"

    vac.is_archived = False
    extra = {
        "acquisition_v1": {
            "activities": [
                {"id": "act_meta_1", "channel_type": "meta", "lifecycle": "paused", "status": "paused"}
            ]
        }
    }
    assert derive_desired_state(vac, extra) == "paused"

    extra["acquisition_v1"]["activities"][0]["lifecycle"] = "active"
    extra["acquisition_v1"]["activities"][0]["status"] = "active"
    assert derive_desired_state(vac, extra) == "active"


async def _oc(tenant_id: str) -> str:
    async with async_session_maker() as session:
        oc = (
            await session.execute(
                select(OwnCompany.id)
                .where(
                    OwnCompany.tenant_id == tenant_id,
                    OwnCompany.is_archived.is_(False),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        assert oc
        return str(oc)


async def _seed_form(tenant_id: str) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Mig form",
                public_slug=f"mig-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()
    return form_id


async def _seed_vacancy(
    *,
    tenant_id: str,
    own_company_id: str,
    company_id: str,
    title: str,
    extra: dict | None = None,
    status: str = "open",
) -> str:
    vac_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Vacancy(
                id=vac_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                company_id=company_id,
                title=title,
                status=status,
                is_active=True,
                is_archived=False,
                extra=json.dumps(extra or {}, ensure_ascii=False) if extra is not None else None,
            )
        )
        await session.commit()
    return vac_id


async def _seed_meta_profile(
    *,
    tenant_id: str,
    own_company_id: str,
    form_key: str,
) -> str:
    profile_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=f"meta-{profile_id[:8]}",
                name="Meta form",
                provider="meta",
                channel="paid",
                own_company_id=own_company_id,
                route_intent="candidate_application",
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                intake_source_profile_id=profile_id,
                provider="meta",
                external_key=form_key,
                external_key_secondary="",
                label="Meta",
                is_active=True,
                priority=10,
            )
        )
        await session.commit()
    return profile_id


@pytest.mark.asyncio
async def test_bare_vacancy_not_eligible():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _oc(tenant_id)
    title = f"Bare vacancy {uuid4().hex[:8]}"
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=oc,
        company_id=data["company_id"],
        title=title,
        extra={},
    )
    async with async_session_maker() as db:
        eligible = await list_eligible_vacancies(db, vacancy_id=vac_id)
        assert eligible == []
        report = await migrate_all(db, vacancy_id=vac_id, dry_run=False)
        assert report.found == 0
        bare = (
            await db.execute(select(Vacancy).where(Vacancy.id == vac_id))
        ).scalar_one()
        assert get_stamp(vacancy_extra_dict(bare)) is None
        await db.commit()


@pytest.mark.asyncio
async def test_migrate_form_and_meta_idempotent_rollback_keeps_stamp():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _oc(tenant_id)
    form_id = await _seed_form(tenant_id)
    form_key = f"meta-form-{uuid4().hex[:12]}"
    profile_id = await _seed_meta_profile(
        tenant_id=tenant_id, own_company_id=oc, form_key=form_key
    )
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=oc,
        company_id=data["company_id"],
        title="Drivers CE migrate",
        extra={
            "launch_search": True,
            "setup_source": "launch_search",
            "lead_form_id": form_id,
            "acquisition_v1": {
                "activities": [
                    {
                        "id": "act_meta_x",
                        "channel_type": "meta",
                        "lifecycle": "active",
                        "status": "active",
                        "provider": {"meta": {"form_id": form_key}},
                    }
                ]
            },
        },
    )

    async with async_session_maker() as db:
        vac = (
            await db.execute(select(Vacancy).where(Vacancy.id == vac_id))
        ).scalar_one()
        r1 = await migrate_one(
            db, vac, signals=["lead_form_id", "launch_search", "acquisition_v1_non_static_activity"], dry_run=False
        )
        await db.commit()

    assert r1.outcome == "migrated"
    assert r1.campaign_id
    assert r1.flight_id
    assert r1.form_id == form_id
    assert r1.intake_source_profile_id == profile_id

    async with async_session_maker() as db:
        campaign = (
            await db.execute(select(Campaign).where(Campaign.id == r1.campaign_id))
        ).scalar_one()
        assert campaign.status == "active"
        assert campaign.own_company_id == oc
        flight = (
            await db.execute(select(CampaignRun).where(CampaignRun.id == r1.flight_id))
        ).scalar_one()
        assert flight.status == "active"
        target = (
            await db.execute(
                select(CampaignTarget).where(CampaignTarget.campaign_id == campaign.id)
            )
        ).scalar_one()
        assert target.target_type == "vacancy"
        assert target.target_id == vac_id
        assert target.route_intent == "candidate_application"
        form_link = (
            await db.execute(
                select(CampaignRunForm).where(CampaignRunForm.campaign_run_id == flight.id)
            )
        ).scalar_one()
        assert form_link.form_id == form_id

        before_count = (
            await db.execute(select(func.count()).select_from(Campaign))
        ).scalar_one()

        vac = (await db.execute(select(Vacancy).where(Vacancy.id == vac_id))).scalar_one()
        r2 = await migrate_one(
            db, vac, signals=["lead_form_id"], dry_run=False
        )
        assert r2.outcome == "already_existed"
        assert r2.campaign_id == r1.campaign_id
        after_count = (
            await db.execute(select(func.count()).select_from(Campaign))
        ).scalar_one()
        assert after_count == before_count
        await db.commit()

    async with async_session_maker() as db:
        report = await rollback_all(db, vacancy_id=vac_id, dry_run=False)
        await db.commit()
    assert report.rolled_back == 1

    async with async_session_maker() as db:
        vac = (await db.execute(select(Vacancy).where(Vacancy.id == vac_id))).scalar_one()
        stamp = get_stamp(vacancy_extra_dict(vac))
        assert stamp is not None
        assert stamp.get("campaign_archived") is True
        assert stamp.get("rolled_back_at")
        assert stamp.get("campaign_id") == r1.campaign_id
        # legacy acquisition JSON untouched
        assert vacancy_extra_dict(vac).get("lead_form_id") == form_id
        assert SCRIPT_VERSION in str(stamp.get("rollback_version"))

        campaign = (
            await db.execute(select(Campaign).where(Campaign.id == r1.campaign_id))
        ).scalar_one()
        assert campaign.status == "archived"

        r3 = await migrate_one(db, vac, signals=["lead_form_id"], dry_run=False)
        assert r3.outcome == "already_existed_rolled_back"
        await db.commit()


@pytest.mark.asyncio
async def test_ambiguous_meta_needs_manual_no_fake_binding():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _oc(tenant_id)
    form_id = await _seed_form(tenant_id)
    await _seed_meta_profile(
        tenant_id=tenant_id, own_company_id=oc, form_key=f"form-a-{uuid4().hex[:8]}"
    )
    await _seed_meta_profile(
        tenant_id=tenant_id, own_company_id=oc, form_key=f"form-b-{uuid4().hex[:8]}"
    )
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=oc,
        company_id=data["company_id"],
        title="Ambiguous meta vac",
        extra={
            "lead_form_id": form_id,
            "acquisition_v1": {
                "activities": [{"id": "act_meta_1", "channel_type": "meta", "lifecycle": "active"}]
            },
        },
    )
    # eligibility via meta_ads_map as well
    async with async_session_maker() as session:
        session.add(
            MetaAdsMap(
                ad_id=int(uuid4().int % 10**12),
                tenant_id=tenant_id,
                vacancy_id=vac_id,
                note="test",
            )
        )
        await session.commit()

    async with async_session_maker() as db:
        vac = (await db.execute(select(Vacancy).where(Vacancy.id == vac_id))).scalar_one()
        row = await migrate_one(
            db,
            vac,
            signals=["lead_form_id", "meta_ads_map", "acquisition_v1_non_static_activity"],
            dry_run=False,
        )
        await db.commit()

    assert row.outcome == "needs_manual"
    assert "meta_source_ambiguous" in row.manual_reasons
    assert row.intake_source_profile_id is None
    assert row.campaign_id
    assert row.form_id == form_id


@pytest.mark.asyncio
async def test_completed_status_mapping():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _oc(tenant_id)
    form_id = await _seed_form(tenant_id)
    vac_id = await _seed_vacancy(
        tenant_id=tenant_id,
        own_company_id=oc,
        company_id=data["company_id"],
        title="Closed search",
        status="closed",
        extra={"lead_form_id": form_id, "launch_search": True},
    )
    async with async_session_maker() as db:
        vac = (await db.execute(select(Vacancy).where(Vacancy.id == vac_id))).scalar_one()
        row = await migrate_one(db, vac, signals=["lead_form_id", "launch_search"], dry_run=False)
        await db.commit()
    assert row.outcome == "migrated"
    async with async_session_maker() as db:
        campaign = (
            await db.execute(select(Campaign).where(Campaign.id == row.campaign_id))
        ).scalar_one()
        flight = (
            await db.execute(select(CampaignRun).where(CampaignRun.id == row.flight_id))
        ).scalar_one()
        assert flight.status == "completed"
        assert campaign.status == "completed"
