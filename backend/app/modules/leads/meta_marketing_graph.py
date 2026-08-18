"""Meta Marketing API reads for search acquisition (ads, campaigns, insights)."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from backend.app.core.settings import settings

logger = logging.getLogger(__name__)


def _graph_version() -> str:
    return (settings.meta_graph_api_version or "v24.0").strip() or "v24.0"


async def _graph_get(path: str, *, access_token: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    gv = _graph_version()
    url = f"https://graph.facebook.com/{gv}/{path.lstrip('/')}"
    query = dict(params or {})
    query["access_token"] = access_token
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.get(url, params=query)
        data = response.json()
    if response.status_code != 200:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        code = str(error.get("code", "GRAPH_ERROR"))
        message = str(error.get("message", "Graph API error"))
        raise RuntimeError(f"{code}:{message}")
    if not isinstance(data, dict):
        raise RuntimeError("GRAPH_INVALID_RESPONSE")
    return data


async def fetch_page_node(page_id: str, access_token: str) -> dict[str, Any]:
    return await _graph_get(str(page_id), access_token=access_token, params={"fields": "id,name"})


_LEADGEN_FORM_SKIP_STATUSES = frozenset({"DELETED", "ARCHIVED"})


async def fetch_page_leadgen_forms(
    page_id: str,
    access_token: str,
    *,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Live Lead Forms on a connected Facebook Page (Graph ``/{page-id}/leadgen_forms``)."""
    pid = str(page_id or "").strip()
    if not pid:
        return []
    rows = await _graph_get_paged(
        f"{pid}/leadgen_forms",
        access_token=access_token,
        params={"fields": "id,name,status,locale"},
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        form_id = str(row.get("id") or "").strip()
        if not form_id:
            continue
        status = str(row.get("status") or "").strip().upper()
        if status in _LEADGEN_FORM_SKIP_STATUSES:
            continue
        name = str(row.get("name") or "").strip() or None
        out.append(
            {
                "form_id": form_id,
                "name": name,
                "status": status or "ACTIVE",
                "page_id": pid,
            }
        )
    return out


async def fetch_ad_node(ad_id: str, access_token: str) -> dict[str, Any]:
    fields = "id,name,status,effective_status,campaign_id,adset_id"
    return await _graph_get(str(ad_id), access_token=access_token, params={"fields": fields})


async def fetch_campaign_node(campaign_id: str, access_token: str) -> dict[str, Any]:
    fields = "id,name,status,effective_status,objective"
    return await _graph_get(str(campaign_id), access_token=access_token, params={"fields": fields})


async def _graph_get_paged(
    path: str,
    *,
    access_token: str,
    params: Optional[dict[str, Any]] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    next_url: str | None = None
    first = True
    base_params = dict(params or {})
    base_params.setdefault("limit", str(min(limit, 100)))
    while first or next_url:
        if first:
            data = await _graph_get(path, access_token=access_token, params=base_params)
            first = False
        else:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.get(next_url or "")
                data = response.json()
            if response.status_code != 200:
                error = data.get("error", {}) if isinstance(data, dict) else {}
                raise RuntimeError(f"{error.get('code', 'GRAPH_ERROR')}:{error.get('message', 'Graph API error')}")
        for row in data.get("data") or []:
            if isinstance(row, dict):
                out.append(row)
        paging = data.get("paging") or {}
        nxt = paging.get("next")
        next_url = str(nxt).strip() if nxt else None
        if len(out) >= limit:
            break
    return out[:limit]


def _normalize_ad_account_id(ad_account_id: str) -> str:
    raw = str(ad_account_id or "").strip()
    if raw.startswith("act_"):
        return raw[4:]
    return raw


def _ad_account_path(ad_account_id: str) -> str:
    digits = _normalize_ad_account_id(ad_account_id)
    return f"act_{digits}"


async def fetch_user_ad_accounts(access_token: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = await _graph_get_paged(
        "me/adaccounts",
        access_token=access_token,
        params={"fields": "id,name,account_id,account_status,currency"},
        limit=limit,
    )
    return rows


async def fetch_ad_account_campaigns(ad_account_id: str, access_token: str, *, limit: int = 100) -> list[dict[str, Any]]:
    return await _graph_get_paged(
        f"{_ad_account_path(ad_account_id)}/campaigns",
        access_token=access_token,
        params={"fields": "id,name,status,effective_status,objective"},
        limit=limit,
    )


def _campaign_has_lead_ads(campaign: dict[str, Any]) -> bool:
    objective = str(campaign.get("objective") or "").upper()
    if "LEAD" in objective:
        return True
    if objective in {"OUTCOME_LEADS", "LEAD_GENERATION"}:
        return True
    return False


async def fetch_campaign_lead_ads(campaign_id: str, access_token: str, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = await _graph_get_paged(
        f"{campaign_id}/ads",
        access_token=access_token,
        params={
            "fields": "id,name,status,effective_status,creative{lead_gen_form_id,name,object_story_spec}",
        },
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        creative = row.get("creative") if isinstance(row.get("creative"), dict) else {}
        form_id = creative.get("lead_gen_form_id")
        if not form_id:
            continue
        out.append(
            {
                "ad_id": str(row.get("id") or "").strip(),
                "ad_name": str(row.get("name") or "").strip(),
                "lead_gen_form_id": str(form_id).strip(),
                "form_name": str(creative.get("name") or "").strip() or None,
            }
        )
    return out


async def fetch_ad_insights(
    ad_id: str,
    access_token: str,
    *,
    date_preset: str = "last_7d",
) -> dict[str, Any]:
    fields = "spend,impressions,clicks,ctr,cpc,actions,cost_per_action_type"
    data = await _graph_get(
        f"{ad_id}/insights",
        access_token=access_token,
        params={"fields": fields, "date_preset": date_preset},
    )
    rows = data.get("data")
    if isinstance(rows, list) and rows:
        row = rows[0]
        return row if isinstance(row, dict) else {}
    return {}


def _lead_count_from_actions(actions: Any) -> int:
    if not isinstance(actions, list):
        return 0
    total = 0
    for item in actions:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type") or "").lower()
        if "lead" in action_type:
            try:
                total += int(item.get("value") or 0)
            except (TypeError, ValueError):
                continue
    return total


def normalize_insights_row(row: dict[str, Any]) -> dict[str, Any]:
    spend = float(row.get("spend") or 0)
    impressions = int(float(row.get("impressions") or 0))
    clicks = int(float(row.get("clicks") or 0))
    ctr = float(row.get("ctr") or 0)
    cpc = float(row.get("cpc") or 0)
    leads = _lead_count_from_actions(row.get("actions"))
    cpl = round(spend / leads, 2) if leads > 0 else None
    return {
        "spend": round(spend, 2),
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(ctr, 4) if ctr else 0,
        "cpc": round(cpc, 2) if cpc else None,
        "leads": leads,
        "cpl": cpl,
    }
