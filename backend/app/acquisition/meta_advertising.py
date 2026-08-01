"""Meta Advertising preview + connect-all for Marketing Flight ops."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.binding_service import (
    attach_ad,
    attach_intake_source,
)
from backend.app.acquisition.campaign_service import (
    CampaignServiceError,
    get_campaign,
)
from backend.app.acquisition.ensure_meta_intake_source import ensure_meta_form_intake_source
from backend.app.acquisition.flights.runtime_commands import get_flight
from backend.app.models.campaign import Campaign, CampaignRunIntakeSource, FlightAdBinding
from backend.app.models.lead import Lead

logger = logging.getLogger(__name__)


@dataclass
class MetaAdPreview:
    ad_id: str
    ad_name: Optional[str] = None
    form_id: Optional[str] = None
    adset_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ad_id": self.ad_id,
            "ad_name": self.ad_name,
            "form_id": self.form_id,
            "adset_id": self.adset_id,
        }


@dataclass
class MetaFormPreview:
    form_id: str
    form_name: Optional[str] = None
    ad_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "form_name": self.form_name,
            "ad_ids": list(self.ad_ids),
        }


@dataclass
class MetaAdvertisingPreview:
    meta_campaign_id: str
    meta_campaign_name: Optional[str]
    meta_adset_id: Optional[str]
    forms: list[MetaFormPreview]
    ads: list[MetaAdPreview]
    source: str  # graph | leads_fallback
    warning: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_campaign_id": self.meta_campaign_id,
            "meta_campaign_name": self.meta_campaign_name,
            "meta_adset_id": self.meta_adset_id,
            "forms": [f.to_dict() for f in self.forms],
            "ads": [a.to_dict() for a in self.ads],
            "source": self.source,
            "warning": self.warning,
        }


@dataclass
class MetaAdvertisingConnectResult:
    campaign: Campaign
    forms_attached: list[str]
    forms_skipped: list[str]
    ads_attached: list[str]
    ads_skipped: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "forms_attached": self.forms_attached,
            "forms_skipped": self.forms_skipped,
            "ads_attached": self.ads_attached,
            "ads_skipped": self.ads_skipped,
        }


async def _marketing_access_token(db: AsyncSession, *, tenant_id: str) -> Optional[str]:
    from backend.app.core.crypto import decrypt_secret
    from backend.app.modules.leads import crud as leads_crud

    entries = await leads_crud.list_meta_credentials(db, tenant_id=str(tenant_id))
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
        tok = decrypt_secret(entry.encrypted_access_token)
        if tok:
            return tok
    return None


def _compose_forms_from_ads(ads: list[MetaAdPreview]) -> list[MetaFormPreview]:
    by_form: dict[str, MetaFormPreview] = {}
    for ad in ads:
        fid = str(ad.form_id or "").strip()
        if not fid:
            continue
        row = by_form.get(fid)
        if row is None:
            row = MetaFormPreview(form_id=fid, form_name=None, ad_ids=[])
            by_form[fid] = row
        if ad.ad_id not in row.ad_ids:
            row.ad_ids.append(ad.ad_id)
    return list(by_form.values())


async def _preview_from_graph(
    *,
    access_token: str,
    meta_campaign_id: str,
    meta_adset_id: Optional[str],
) -> MetaAdvertisingPreview:
    from backend.app.modules.leads.meta_marketing_graph import (
        fetch_campaign_lead_ads,
        fetch_campaign_node,
    )

    camp_name: Optional[str] = None
    try:
        node = await fetch_campaign_node(meta_campaign_id, access_token)
        camp_name = str(node.get("name") or "").strip() or None
    except Exception as exc:
        logger.info("meta campaign node failed id=%s: %s", meta_campaign_id, exc)

    raw_ads = await fetch_campaign_lead_ads(meta_campaign_id, access_token, limit=200)
    ads: list[MetaAdPreview] = []
    adset_filter = str(meta_adset_id or "").strip() or None
    for row in raw_ads:
        ad_id = str(row.get("ad_id") or "").strip()
        if not ad_id:
            continue
        adset_id = str(row.get("adset_id") or "").strip() or None
        if adset_filter and adset_id != adset_filter:
            continue
        ads.append(
            MetaAdPreview(
                ad_id=ad_id,
                ad_name=str(row.get("ad_name") or "").strip() or None,
                form_id=str(row.get("lead_gen_form_id") or "").strip() or None,
                adset_id=adset_id,
            )
        )
    forms = _compose_forms_from_ads(ads)
    for form in forms:
        for row in raw_ads:
            if str(row.get("lead_gen_form_id") or "").strip() == form.form_id:
                name = str(row.get("form_name") or "").strip()
                if name:
                    form.form_name = name
                    break
    return MetaAdvertisingPreview(
        meta_campaign_id=meta_campaign_id,
        meta_campaign_name=camp_name,
        meta_adset_id=adset_filter,
        forms=forms,
        ads=ads,
        source="graph",
    )


async def _preview_from_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    meta_campaign_id: str,
    meta_adset_id: Optional[str],
) -> MetaAdvertisingPreview:
    """Fallback: recent Meta leads with form_id/ad_id (campaign filter unavailable in payload)."""
    rows = (
        await db.execute(
            select(Lead.ad_id, Lead.payload, Lead.normalized)
            .where(Lead.tenant_id == str(tenant_id), Lead.source == "meta")
            .order_by(Lead.created_at.desc())
            .limit(500)
        )
    ).all()
    ads_map: dict[str, MetaAdPreview] = {}
    for ad_id_raw, payload, normalized in rows:
        aid = str(ad_id_raw or "").strip()
        form_id = ""
        adset_id = None
        ad_name = None
        try:
            entry = (payload or {}).get("entry") or []
            if entry:
                changes = (entry[0] or {}).get("changes") or []
                if changes:
                    value = (changes[0] or {}).get("value") or {}
                    form_id = str(value.get("form_id") or "").strip()
                    camp = str(value.get("campaign_id") or "").strip()
                    adset_id = str(value.get("adset_id") or "").strip() or None
                    if camp and camp != str(meta_campaign_id):
                        continue
        except Exception:
            form_id = ""
        if not form_id and isinstance(normalized, dict):
            form_id = str(normalized.get("form_id") or "").strip()
        if not aid or not form_id:
            continue
        if meta_adset_id and adset_id and adset_id != str(meta_adset_id):
            continue
        if aid not in ads_map:
            ads_map[aid] = MetaAdPreview(
                ad_id=aid,
                ad_name=ad_name,
                form_id=form_id,
                adset_id=adset_id,
            )
    ads = list(ads_map.values())
    return MetaAdvertisingPreview(
        meta_campaign_id=str(meta_campaign_id),
        meta_campaign_name=None,
        meta_adset_id=str(meta_adset_id).strip() if meta_adset_id else None,
        forms=_compose_forms_from_ads(ads),
        ads=ads,
        source="leads_fallback",
        warning=(
            "Meta Graph unavailable — showing recent Lead Forms/Ads from inbox. "
            "Confirm selection matches your Meta Campaign."
        ),
    )


async def preview_meta_advertising(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    meta_campaign_id: str,
    meta_adset_id: Optional[str] = None,
    own_company_id: Optional[str] = None,
) -> MetaAdvertisingPreview:
    await get_campaign(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        own_company_id=own_company_id,
    )
    cid = str(meta_campaign_id or "").strip()
    if not cid:
        raise CampaignServiceError("meta_campaign_id is required", status_code=422)
    adset = str(meta_adset_id or "").strip() or None

    token = await _marketing_access_token(db, tenant_id=str(tenant_id))
    if token:
        try:
            return await _preview_from_graph(
                access_token=token,
                meta_campaign_id=cid,
                meta_adset_id=adset,
            )
        except Exception as exc:
            logger.info("meta advertising graph preview failed: %s", exc)

    return await _preview_from_leads(
        db,
        tenant_id=str(tenant_id),
        meta_campaign_id=cid,
        meta_adset_id=adset,
    )


async def _flight_has_primary_intake(
    db: AsyncSession, *, tenant_id: str, flight_id: str
) -> bool:
    row = await db.execute(
        select(CampaignRunIntakeSource.id).where(
            CampaignRunIntakeSource.tenant_id == str(tenant_id),
            CampaignRunIntakeSource.campaign_run_id == str(flight_id),
            CampaignRunIntakeSource.role == "primary",
            CampaignRunIntakeSource.is_active.is_(True),
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _intake_already_linked(
    db: AsyncSession, *, flight_id: str, profile_id: str
) -> bool:
    row = await db.execute(
        select(CampaignRunIntakeSource.id).where(
            CampaignRunIntakeSource.campaign_run_id == str(flight_id),
            CampaignRunIntakeSource.intake_source_profile_id == str(profile_id),
        ).limit(1)
    )
    return row.scalar_one_or_none() is not None


async def _ad_already_bound(
    db: AsyncSession, *, tenant_id: str, provider_ad_id: str
) -> Optional[FlightAdBinding]:
    row = await db.execute(
        select(FlightAdBinding).where(
            FlightAdBinding.tenant_id == str(tenant_id),
            FlightAdBinding.provider == "meta",
            FlightAdBinding.provider_ad_id == str(provider_ad_id),
            FlightAdBinding.is_active.is_(True),
        ).limit(1)
    )
    return row.scalar_one_or_none()


async def connect_meta_advertising(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    meta_campaign_id: str,
    form_ids: list[str],
    ad_ids: list[str],
    meta_adset_id: Optional[str] = None,
    own_company_id: Optional[str] = None,
    actor_type: str = "user",
    actor_id: Optional[str] = None,
) -> MetaAdvertisingConnectResult:
    """Ensure forms + attach primary/secondary + bind ads (idempotent skips)."""
    _ = meta_campaign_id, meta_adset_id  # reserved for future SoT / audit
    clean_forms = [str(f).strip() for f in form_ids if str(f or "").strip()]
    clean_ads = [str(a).strip() for a in ad_ids if str(a or "").strip()]
    if not clean_forms and not clean_ads:
        raise CampaignServiceError(
            "form_ids or ad_ids is required",
            status_code=422,
        )
    campaign = await get_campaign(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        own_company_id=own_company_id,
    )
    flight_id = str(campaign.current_flight_id or "").strip()
    if not flight_id:
        current = next((f for f in (campaign.flights or []) if getattr(f, "is_current", False)), None)
        if current is None and campaign.flights:
            current = campaign.flights[0]
        if current is None:
            raise CampaignServiceError("Campaign has no Flight", status_code=422)
        flight_id = str(current.id)
    _, flight = await get_flight(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=flight_id,
        own_company_id=own_company_id,
    )
    oid = str(own_company_id or campaign.own_company_id)
    route_intent = "candidate_application"
    primary = next(
        (
            t
            for t in (campaign.targets or [])
            if str(getattr(t, "role", "") or "").strip().lower() == "primary"
        ),
        None,
    )
    if primary is not None and getattr(primary, "route_intent", None):
        route_intent = str(primary.route_intent)

    forms_attached: list[str] = []
    forms_skipped: list[str] = []
    has_primary = await _flight_has_primary_intake(
        db, tenant_id=str(tenant_id), flight_id=str(flight.id)
    )

    for fid in clean_forms:
        profile = await ensure_meta_form_intake_source(
            db,
            tenant_id=str(tenant_id),
            own_company_id=oid,
            form_id=fid,
            route_intent=route_intent,
        )
        if await _intake_already_linked(db, flight_id=str(flight.id), profile_id=str(profile.id)):
            forms_skipped.append(fid)
            continue
        role = "secondary" if has_primary else "primary"
        try:
            campaign = await attach_intake_source(
                db,
                tenant_id=str(tenant_id),
                campaign_id=str(campaign_id),
                intake_source_profile_id=str(profile.id),
                own_company_id=oid,
                flight_id=str(flight.id),
                role=role,
                actor_type=actor_type,
                actor_id=actor_id,
            )
            forms_attached.append(fid)
            if role == "primary":
                has_primary = True
        except CampaignServiceError as exc:
            if exc.status_code == 422 and "already linked" in str(exc.detail).lower():
                forms_skipped.append(fid)
                continue
            raise

    ads_attached: list[str] = []
    ads_skipped: list[str] = []
    for aid in clean_ads:
        existing = await _ad_already_bound(db, tenant_id=str(tenant_id), provider_ad_id=aid)
        if existing is not None:
            if str(existing.campaign_run_id) == str(flight.id):
                ads_skipped.append(aid)
                continue
            raise CampaignServiceError(
                f"Ad {aid} is already bound to another Flight",
                status_code=422,
            )
        try:
            campaign = await attach_ad(
                db,
                tenant_id=str(tenant_id),
                campaign_id=str(campaign_id),
                provider_ad_id=aid,
                provider="meta",
                own_company_id=oid,
                flight_id=str(flight.id),
                actor_type=actor_type,
                actor_id=actor_id,
            )
            ads_attached.append(aid)
        except CampaignServiceError as exc:
            if exc.status_code == 422 and "already exists" in str(exc.detail).lower():
                ads_skipped.append(aid)
                continue
            raise

    campaign = await get_campaign(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        own_company_id=own_company_id,
    )
    return MetaAdvertisingConnectResult(
        campaign=campaign,
        forms_attached=forms_attached,
        forms_skipped=forms_skipped,
        ads_attached=ads_attached,
        ads_skipped=ads_skipped,
    )


__all__ = [
    "MetaAdvertisingConnectResult",
    "MetaAdvertisingPreview",
    "connect_meta_advertising",
    "preview_meta_advertising",
]
