"""Search-scoped Meta binding: campaign picker UX, auto form/ad routing."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.crypto import decrypt_secret
from backend.app.modules.leads import crud
from backend.app.modules.leads import admin_service
from backend.app.modules.leads.meta_marketing_graph import (
    _campaign_has_lead_ads,
    fetch_ad_account_campaigns,
    fetch_campaign_lead_ads,
    fetch_campaign_node,
    fetch_page_node,
    fetch_user_ad_accounts,
)
from backend.app.modules.leads.schemas import MetaAdsMapCreate, MetaFormRouteUpdate
from backend.app.services.search_acquisition_service import get_vacancy_or_raise

logger = logging.getLogger(__name__)


async def _ensure_credential_user_token_column(db: AsyncSession) -> None:
    from sqlalchemy import text

    try:
        await db.execute(
            text(
                "ALTER TABLE meta_lead_credentials ADD COLUMN IF NOT EXISTS encrypted_user_access_token TEXT"
            )
        )
        await db.flush()
    except Exception:
        logger.debug("meta_lead_credentials.encrypted_user_access_token ensure skipped", exc_info=True)


async def _resolve_marketing_context(
    db: AsyncSession,
    tenant_id: str,
) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Return (user_token, page_token, page_id, ad_account_id)."""
    await _ensure_credential_user_token_column(db)
    entries = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
        page_token = decrypt_secret(entry.encrypted_access_token)
        page_id = decrypt_secret(entry.encrypted_page_id)
        user_token = decrypt_secret(getattr(entry, "encrypted_user_access_token", None))
        ad_account_id = decrypt_secret(entry.encrypted_ad_account_id)
        token_for_ads = user_token or page_token
        if token_for_ads:
            return user_token, page_token, page_id, ad_account_id
    return None, None, None, None


async def _pick_ad_account_id(user_access_token: str, preferred: Optional[str]) -> Optional[str]:
    """Marketing API ad accounts require a user access token (page token is not enough)."""
    if preferred and str(preferred).strip():
        return str(preferred).strip().replace("act_", "")
    try:
        accounts = await fetch_user_ad_accounts(user_access_token, limit=20)
    except Exception as exc:
        logger.warning("meta_inventory_ad_accounts_failed: %s", exc)
        return None
    for row in accounts:
        account_id = str(row.get("account_id") or row.get("id") or "").replace("act_", "").strip()
        if account_id:
            return account_id
    return None


async def build_meta_search_inventory(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
) -> dict[str, Any]:
    await get_vacancy_or_raise(db, tenant_id, vacancy_id)
    user_token, page_token, page_id, ad_account_id = await _resolve_marketing_context(db, tenant_id)
    if not page_token and not user_token:
        return {
            "connected": False,
            "needs_marketing_reconnect": False,
            "page_name": None,
            "ad_account_name": None,
            "campaigns": [],
            "bound_campaign_ids": [],
            "empty_message": "Подключите Meta, чтобы увидеть рекламные кампании.",
        }

    page_name: Optional[str] = None
    if page_id and page_token:
        try:
            page_node = await fetch_page_node(page_id, page_token)
            page_name = str(page_node.get("name") or "").strip() or None
        except Exception:
            page_name = None

    if not user_token:
        return {
            "connected": True,
            "needs_marketing_reconnect": True,
            "page_id": page_id,
            "page_name": page_name,
            "ad_account_name": None,
            "campaigns": [],
            "bound_campaign_ids": [],
            "empty_message": (
                "Подключена только Facebook-страница"
                + (f" «{page_name}»" if page_name else "")
                + ". Чтобы увидеть рекламные кабинеты и кампании, обновите доступ Meta "
                "(повторный вход через Facebook сохранит доступ к Ads Manager)."
            ),
        }

    ad_account_id = await _pick_ad_account_id(user_token, ad_account_id)
    if not ad_account_id:
        return {
            "connected": True,
            "needs_marketing_reconnect": True,
            "page_id": page_id,
            "page_name": page_name,
            "ad_account_name": None,
            "campaigns": [],
            "bound_campaign_ids": [],
            "empty_message": (
                "Не удалось получить рекламный кабинет. Обновите доступ Meta и убедитесь, "
                "что у приложения HostFlow Leads одобрено право ads_read (App Review)."
            ),
        }

    marketing_token = user_token

    ad_account_name: Optional[str] = None
    try:
        accounts = await fetch_user_ad_accounts(marketing_token, limit=20)
        for row in accounts:
            aid = str(row.get("account_id") or row.get("id") or "").replace("act_", "")
            if aid == str(ad_account_id).replace("act_", ""):
                ad_account_name = str(row.get("name") or "").strip() or None
                break
    except Exception:
        pass

    bound_ads = await crud.list_meta_ads_map(db, tenant_id=tenant_id, search=None, limit=500)
    bound_for_search = {str(row.ad_id) for row in bound_ads if str(row.vacancy_id) == vacancy_id}
    bound_campaign_ids: set[str] = set()

    campaigns_out: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        raw_campaigns = await fetch_ad_account_campaigns(ad_account_id, marketing_token, limit=100)
    except Exception as exc:
        logger.warning("meta_inventory_campaigns_failed tenant=%s: %s", tenant_id, exc)
        return {
            "connected": True,
            "needs_marketing_reconnect": False,
            "page_id": page_id,
            "page_name": page_name,
            "ad_account_name": ad_account_name,
            "campaigns": [],
            "bound_campaign_ids": [],
            "empty_message": "Не удалось загрузить кампании из Meta. Проверьте права ads_read.",
            "warnings": [str(exc)],
        }

    for camp in raw_campaigns:
        campaign_id = str(camp.get("id") or "").strip()
        if not campaign_id:
            continue
        name = str(camp.get("name") or campaign_id).strip()
        status = str(camp.get("effective_status") or camp.get("status") or "").strip()
        objective = str(camp.get("objective") or "").strip()
        try:
            lead_ads = await fetch_campaign_lead_ads(campaign_id, marketing_token, limit=50)
        except Exception as exc:
            warnings.append(f"{name}:{exc}")
            lead_ads = []
        if not lead_ads and not _campaign_has_lead_ads(camp):
            continue
        ad_ids = {row["ad_id"] for row in lead_ads if row.get("ad_id")}
        bound = bool(ad_ids) and ad_ids.issubset(bound_for_search)
        if bound:
            bound_campaign_ids.add(campaign_id)
        campaigns_out.append(
            {
                "id": campaign_id,
                "name": name,
                "status": status,
                "objective": objective,
                "ads_count": len(lead_ads),
                "bound_to_search": bound,
            }
        )

    campaigns_out.sort(key=lambda row: (not row.get("bound_to_search"), row.get("name") or ""))

    empty_message: Optional[str] = None
    if not campaigns_out:
        empty_message = (
            "Пока нет рекламы с лид-формами в этом кабинете. "
            "Создайте Lead Ad в Meta или выберите «Настроить позже»."
        )

    return {
        "connected": True,
        "needs_marketing_reconnect": False,
        "page_id": page_id,
        "page_name": page_name,
        "ad_account_id": ad_account_id,
        "ad_account_name": ad_account_name,
        "campaigns": campaigns_out,
        "bound_campaign_ids": sorted(bound_campaign_ids),
        "empty_message": empty_message,
        "warnings": warnings,
    }


async def bind_meta_campaigns_to_search(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    *,
    campaign_ids: list[str],
    user_sub: Optional[str] = None,
) -> dict[str, Any]:
    vacancy = await get_vacancy_or_raise(db, tenant_id, vacancy_id)
    own_company_id = str(getattr(vacancy, "own_company_id", None) or getattr(vacancy, "company_id", None) or "").strip()
    if not own_company_id:
        raise LookupError("vacancy_missing_company")

    user_token, page_token, page_id, ad_account_id = await _resolve_marketing_context(db, tenant_id)
    marketing_token = user_token or page_token
    if not marketing_token:
        raise LookupError("meta_not_connected")
    if not user_token:
        raise LookupError("meta_marketing_reconnect_required")
    ad_account_id = await _pick_ad_account_id(user_token, ad_account_id)
    if not ad_account_id:
        raise LookupError("meta_marketing_reconnect_required")

    bound_ads = 0
    bound_forms = 0
    skipped: list[str] = []

    for campaign_id in campaign_ids:
        cid = str(campaign_id or "").strip()
        if not cid:
            continue
        try:
            camp = await fetch_campaign_node(cid, marketing_token)
            camp_name = str((camp or {}).get("name") or cid)
        except Exception:
            camp_name = cid
        try:
            lead_ads = await fetch_campaign_lead_ads(cid, marketing_token, limit=100)
        except Exception as exc:
            skipped.append(f"{camp_name}: {exc}")
            continue
        if not lead_ads:
            skipped.append(f"{camp_name}: нет объявлений с лид-формами")
            continue
        for ad in lead_ads:
            ad_id = str(ad.get("ad_id") or "").strip()
            form_id = str(ad.get("lead_gen_form_id") or "").strip()
            if not ad_id:
                continue
            await admin_service.upsert_mapping(
                db,
                tenant_id,
                MetaAdsMapCreate(ad_id=ad_id, vacancy_id=UUID(vacancy_id), note=camp_name),
            )
            bound_ads += 1
            if form_id:
                await admin_service.upsert_meta_form_route(
                    db,
                    tenant_id,
                    form_id,
                    MetaFormRouteUpdate(
                        page_id=page_id,
                        own_company_id=UUID(own_company_id),
                        lead_target_type="candidate",
                        is_active=True,
                    ),
                    user_sub=user_sub,
                )
                bound_forms += 1

    return {
        "bound_ads": bound_ads,
        "bound_forms": bound_forms,
        "skipped": skipped,
        "inventory": await build_meta_search_inventory(db, tenant_id, vacancy_id),
    }
