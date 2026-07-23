"""Search-scoped acquisition: activities, metrics history, advisor insights."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import MARKETING_NEW
from backend.app.constants.stages import STAGES_BY_GROUP
from backend.app.core.crypto import decrypt_secret
from backend.app.models.campaign import Campaign, CampaignTarget
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.vacancy import Vacancy
from backend.app.modules.leads import crud
from backend.app.modules.leads.meta_marketing_graph import (
    fetch_ad_insights,
    fetch_ad_node,
    fetch_campaign_node,
    normalize_insights_row,
)

logger = logging.getLogger(__name__)

# Acquisition UI Cutover C-2 — no new launches outside Campaign/Flight.
LEGACY_LAUNCH_DISABLED = True
LEGACY_LAUNCH_CODE = "legacy_launch_disabled"


class LegacyLaunchDisabledError(RuntimeError):
    """Raised when searchAcquisition tries to create/duplicate a launch."""

    def __init__(self, *, search_id: str, marketing_setup_path: str):
        self.search_id = search_id
        self.marketing_setup_path = marketing_setup_path
        super().__init__(LEGACY_LAUNCH_CODE)

ACQUISITION_EXTRA_KEY = "acquisition_v1"
SYNC_INTERVAL_MINUTES = 15
METRICS_HISTORY_MAX_DAYS = 90
EVENT_LOG_MAX = 150
STATIC_ACTIVITY_IDS = frozenset({"act_public_link", "act_qr"})

_EMPLOYED_STAGES = set(STAGES_BY_GROUP.get("employed", [])) | set(STAGES_BY_GROUP.get("probation", [])) | {"hired"}
_INTERVIEW_STAGES = set(STAGES_BY_GROUP.get("interview", []))
_HIRING_STAGES = set(STAGES_BY_GROUP.get("hiring", []))
_OFFER_STAGES = {"employment_pending", "at_client", "trip_plan", "permit_ordered", "permit_received", "visa", "red_paper"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _loads_extra(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _activity_visible_for_search(activity: dict[str, Any], search_id: str) -> bool:
    ids = activity.get("search_ids")
    if isinstance(ids, list) and ids:
        return search_id in [str(x) for x in ids]
    return True


def _migrate_stored_activities(stored_block: dict[str, Any], search_id: str) -> list[dict[str, Any]]:
    activities = stored_block.get("activities")
    if isinstance(activities, list) and activities:
        return [a for a in activities if isinstance(a, dict)]
    legacy = stored_block.get("channels")
    if not isinstance(legacy, list):
        return []
    migrated: list[dict[str, Any]] = []
    for row in legacy:
        if not isinstance(row, dict):
            continue
        act = dict(row)
        act.setdefault("search_ids", [search_id])
        if "channel_type" not in act:
            act["channel_type"] = act.get("type", "meta")
        if act.get("name", "").startswith("Meta • "):
            act["name"] = act["name"][7:]
        act.setdefault("metrics_history", [])
        act.setdefault("audience", {})
        migrated.append(act)
    return migrated


def _count_candidates_funnel_sync(rows: list[tuple[Any, int]]) -> dict[str, int]:
    hired = offers = interviews = candidates = 0
    for stage, count in rows:
        n = int(count or 0)
        code = str(stage or "new").strip().lower() or "new"
        if code in {"rejected", "declined"}:
            continue
        candidates += n
        if code in _EMPLOYED_STAGES:
            hired += n
        elif code in _OFFER_STAGES or code in _HIRING_STAGES:
            offers += n
        elif code in _INTERVIEW_STAGES:
            interviews += n
    interviews += offers + hired
    return {"candidates": candidates, "interviews": interviews, "offers": offers, "hired": hired}


async def _count_candidates_funnel(db: AsyncSession, tenant_id: str, vacancy_id: str) -> dict[str, int]:
    rows = (
        await db.execute(
            select(Candidate.stage, func.count())
            .where(Candidate.tenant_id == tenant_id, Candidate.vacancy_id == vacancy_id)
            .group_by(Candidate.stage)
        )
    ).all()
    return _count_candidates_funnel_sync(list(rows))


async def _count_leads(db: AsyncSession, tenant_id: str, vacancy_id: str) -> int:
    total = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(Lead.tenant_id == tenant_id, Lead.vacancy_id == vacancy_id)
        )
    ).scalar_one()
    return int(total or 0)


async def _search_titles(db: AsyncSession, tenant_id: str, search_ids: list[str]) -> dict[str, str]:
    if not search_ids:
        return {}
    rows = (
        await db.execute(
            select(Vacancy.id, Vacancy.title).where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.id.in_(search_ids),
            )
        )
    ).all()
    return {str(rid): str(title or rid) for rid, title in rows}


async def _resolve_access_token(db: AsyncSession, tenant_id: str) -> tuple[Optional[str], Optional[str]]:
    entries = await crud.list_meta_credentials(db, tenant_id=tenant_id)
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
        token = decrypt_secret(entry.encrypted_access_token)
        ad_account = decrypt_secret(entry.encrypted_ad_account_id)
        page_id = decrypt_secret(entry.encrypted_page_id)
        if token:
            return token, ad_account or page_id
    return None, None


def _activity_status(*, meta_connected: bool, has_activity: bool, graph_errors: int) -> tuple[str, str]:
    if graph_errors > 0 and has_activity:
        return "needs_attention", "Реклама требует внимания"
    if not meta_connected and not has_activity:
        return "draft", "Черновик"
    if has_activity:
        return "active", "Активна"
    return "paused", "Нет откликов"


def _next_action_from_metrics(metrics_7d: dict[str, Any], metrics_today: dict[str, Any]) -> Optional[dict[str, Any]]:
    cpl_7d = metrics_7d.get("cpl")
    cpl_today = metrics_today.get("cpl")
    if cpl_7d and cpl_today and float(cpl_7d) > 0:
        delta = (float(cpl_today) - float(cpl_7d)) / float(cpl_7d)
        if delta >= 0.2:
            return {"kind": "cost_increase", "title": f"Стоимость выросла на {int(round(delta * 100))}%", "severity": "warning"}
    if int(metrics_7d.get("leads") or 0) == 0 and float(metrics_7d.get("spend") or 0) > 0:
        return {
            "kind": "no_leads",
            "title": "Расход есть, откликов нет — проверьте форму и объявление",
            "severity": "warning",
        }
    return None


def _record_metrics_history(activity: dict[str, Any], metrics_today: dict[str, Any], funnel: dict[str, Any]) -> None:
    history = activity.get("metrics_history")
    if not isinstance(history, list):
        history = []
    row = {
        "date": _today_utc(),
        "spend": float(metrics_today.get("spend") or 0),
        "leads": int(metrics_today.get("leads") or metrics_today.get("responses") or 0),
        "cpl": metrics_today.get("cpl"),
        "ctr": metrics_today.get("ctr"),
        "candidates": int(funnel.get("candidates") or 0),
        "hired": int(funnel.get("hired") or 0),
    }
    replaced = False
    for i, existing in enumerate(history):
        if isinstance(existing, dict) and existing.get("date") == row["date"]:
            history[i] = row
            replaced = True
            break
    if not replaced:
        history.append(row)
    history.sort(key=lambda x: str((x or {}).get("date") or ""))
    activity["metrics_history"] = history[-METRICS_HISTORY_MAX_DAYS:]


def _sum_history(history: list[dict[str, Any]], days: int) -> dict[str, Any]:
    slice_rows = history[-days:] if days else history
    spend = sum(float(r.get("spend") or 0) for r in slice_rows if isinstance(r, dict))
    leads = sum(int(r.get("leads") or 0) for r in slice_rows if isinstance(r, dict))
    return {
        "spend": round(spend, 2),
        "leads": leads,
        "cpl": round(spend / leads, 2) if leads > 0 else None,
    }


def _get_event_log(block: dict[str, Any]) -> list[dict[str, Any]]:
    raw = block.get("event_log")
    if not isinstance(raw, list):
        return []
    return [e for e in raw if isinstance(e, dict)]


def _append_event(block: dict[str, Any], *, kind: str, title: str, activity_id: Optional[str] = None) -> None:
    log = _get_event_log(block)
    log.insert(
        0,
        {
            "id": f"evt_{uuid.uuid4().hex[:10]}",
            "at": _utc_now_iso(),
            "kind": kind,
            "title": title,
            "activity_id": activity_id,
        },
    )
    block["event_log"] = log[:EVENT_LOG_MAX]


def _days_without_leads(history: list[dict[str, Any]]) -> Optional[int]:
    if not history:
        return None
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    for offset in range(1, 31):
        day = (today - timedelta(days=offset)).isoformat()
        for row in reversed(history):
            if isinstance(row, dict) and row.get("date") == day:
                if int(row.get("leads") or 0) > 0:
                    return offset - 1 if offset > 1 else 0
                break
    return None


def _meta_external_url(activity: dict[str, Any]) -> Optional[str]:
    campaign_id = str((activity.get("provider") or {}).get("meta", {}).get("campaign_id") or "").strip()
    if not campaign_id or campaign_id == "unmapped":
        return None
    return f"https://www.facebook.com/adsmanager/manage/campaigns?selected_campaign_ids={campaign_id}"


def _build_attention_items(
    activities: list[dict[str, Any]],
    search_fill: dict[str, Any],
    *,
    search_title: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    headcount = int(search_fill.get("headcount_target") or 0)
    hired = int(search_fill.get("hired") or 0)
    pct = int(search_fill.get("pct") or 0)

    if headcount > 0:
        remaining = max(0, headcount - hired)
        if remaining > 0 and remaining <= 3 and pct >= 60:
            items.append(
                {
                    "id": "search_near_goal",
                    "severity": "success",
                    "headline": f"Подбор {search_title}",
                    "message": f"Цель почти достигнута. Осталось {remaining} человек.",
                    "kind": "search_near_goal",
                }
            )
        elif pct >= 100:
            items.append(
                {
                    "id": "search_filled",
                    "severity": "success",
                    "headline": f"Подбор {search_title}",
                    "message": "Подбор закрыт — часть рекламы можно остановить.",
                    "kind": "search_filled",
                }
            )

    for act in activities:
        if act.get("lifecycle") == "archived":
            continue
        name = str(act.get("name") or "Активность")
        act_id = str(act.get("id") or "")
        history = [h for h in (act.get("metrics_history") or []) if isinstance(h, dict)]
        metrics_7d = (act.get("metrics") or {}).get("period_7d") or {}

        if len(history) >= 14:
            recent = _sum_history(history, 7)
            prev = _sum_history(history[:-7], 7)
            rcpl = recent.get("cpl")
            pcpl = prev.get("cpl")
            if rcpl and pcpl and float(pcpl) > 0:
                delta = (float(rcpl) - float(pcpl)) / float(pcpl)
                if delta >= 0.25:
                    items.append(
                        {
                            "id": f"cpl_up_{act_id}",
                            "severity": "error",
                            "headline": f"Кампания «{name}»",
                            "message": f"Стоимость лида выросла на {int(round(delta * 100))}%.",
                            "kind": "cpl_up",
                            "activity_id": act_id,
                        }
                    )

        days_idle = _days_without_leads(history)
        if days_idle is not None and days_idle >= 4:
            items.append(
                {
                    "id": f"no_leads_{act_id}",
                    "severity": "warning",
                    "headline": f"Кампания «{name}»",
                    "message": f"Нет новых откликов {days_idle} дн.",
                    "kind": "no_recent_leads",
                    "activity_id": act_id,
                }
            )
        elif int(metrics_7d.get("leads") or 0) == 0 and float(metrics_7d.get("spend") or 0) > 20:
            items.append(
                {
                    "id": f"spend_no_leads_{act_id}",
                    "severity": "error",
                    "headline": f"Кампания «{name}»",
                    "message": "Расход есть, откликов нет — проверьте объявление и форму.",
                    "kind": "spend_no_leads",
                    "activity_id": act_id,
                }
            )

    order = {"error": 0, "warning": 1, "success": 2}
    items.sort(key=lambda x: order.get(str(x.get("severity")), 9))
    return items[:8]


def _enrich_activity_controls(activity: dict[str, Any], sync_state: dict[str, Any]) -> None:
    activity["lifecycle"] = activity.get("lifecycle") or "active"
    activity["meta_external_url"] = _meta_external_url(activity)
    activity["last_sync_at"] = sync_state.get("last_sync_ok_at") or sync_state.get("last_sync_at")
    is_static = str(activity.get("id") or "") in STATIC_ACTIVITY_IDS
    activity["actions"] = {
        "open_meta": bool(activity.get("meta_external_url")),
        "update_bindings": not is_static,
        "pause": not is_static and activity["lifecycle"] == "active",
        "resume": not is_static and activity["lifecycle"] == "paused",
        # C-2: duplicate creates a new launch — disabled (Campaign/Flight only).
        "duplicate": False,
        "archive": not is_static,
    }


def marketing_setup_path_for_search(search_id: str, *, name: str | None = None) -> str:
    from urllib.parse import quote, urlencode

    q = {"target_type": "vacancy", "target_id": str(search_id), "flow": "candidates"}
    if name and str(name).strip():
        q["name"] = str(name).strip()[:160]
    return f"{MARKETING_NEW}?{urlencode(q, quote_via=quote)}"


async def resolve_search_campaign_reconciliation(
    db: AsyncSession,
    *,
    tenant_id: str,
    search_id: str,
) -> dict[str, Any]:
    """Link Подбор/vacancy to Campaign when exactly one vacancy target matches."""
    rows = (
        await db.execute(
            select(Campaign.id, Campaign.name, Campaign.status)
            .join(CampaignTarget, CampaignTarget.campaign_id == Campaign.id)
            .where(
                Campaign.tenant_id == str(tenant_id),
                CampaignTarget.tenant_id == str(tenant_id),
                CampaignTarget.target_type == "vacancy",
                CampaignTarget.target_id == str(search_id),
                Campaign.status != "archived",
            )
            .order_by(Campaign.created_at.asc())
        )
    ).all()
    if not rows:
        return {
            "status": "unresolved",
            "linked_campaign_id": None,
            "linked_campaign_name": None,
            "linked_campaign_status": None,
            "candidate_campaign_ids": [],
            "reason": "no_campaign_with_vacancy_target",
        }
    if len(rows) == 1:
        cid, cname, cstatus = rows[0]
        return {
            "status": "linked",
            "linked_campaign_id": str(cid),
            "linked_campaign_name": str(cname or ""),
            "linked_campaign_status": str(cstatus or ""),
            "candidate_campaign_ids": [str(cid)],
            "reason": "unique_vacancy_target",
        }
    ids = [str(r[0]) for r in rows]
    return {
        "status": "unresolved",
        "linked_campaign_id": None,
        "linked_campaign_name": None,
        "linked_campaign_status": None,
        "candidate_campaign_ids": ids,
        "reason": "multiple_campaigns_for_vacancy",
    }


def _persistable_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in activities if isinstance(a, dict) and str(a.get("id") or "") not in STATIC_ACTIVITY_IDS]


def _record_sync_journal_events(
    block: dict[str, Any],
    *,
    sync_meta: bool,
    sync_error: Optional[str],
    activities: list[dict[str, Any]],
    funnel: dict[str, Any],
) -> None:
    if not sync_meta:
        return
    watch = block.get("watch_state")
    if not isinstance(watch, dict):
        watch = {}
    leads_now = int(funnel.get("leads") or 0)
    spend = sum(float((a.get("metrics") or {}).get("period_7d", {}).get("spend") or 0) for a in activities)
    leads_7d = sum(int((a.get("metrics") or {}).get("period_7d", {}).get("leads") or 0) for a in activities)
    cpl_now = round(spend / leads_7d, 2) if leads_7d > 0 else None

    if sync_error:
        _append_event(block, kind="sync_failed", title="Не удалось синхронизировать Meta.")
    else:
        _append_event(block, kind="sync_ok", title="Meta синхронизирована.")
        prev_leads = watch.get("leads_total")
        if isinstance(prev_leads, int) and leads_now > prev_leads:
            delta = leads_now - prev_leads
            _append_event(block, kind="leads_received", title=f"Получено {delta} новых откликов.")
        prev_cpl = watch.get("cpl_7d")
        if cpl_now and prev_cpl and float(prev_cpl) > 0:
            delta = (float(cpl_now) - float(prev_cpl)) / float(prev_cpl)
            if abs(delta) >= 0.1:
                direction = "выросла" if delta > 0 else "снизилась"
                _append_event(
                    block,
                    kind="cpl_changed",
                    title=f"Стоимость лида {direction} на {int(round(abs(delta) * 100))}%.",
                )

    block["watch_state"] = {"leads_total": leads_now, "cpl_7d": cpl_now}


def _apply_lifecycle_status(activity: dict[str, Any]) -> None:
    lifecycle = str(activity.get("lifecycle") or "active")
    if lifecycle == "paused":
        activity["status"] = "paused"
        activity["status_label"] = "Приостановлена"
    elif lifecycle == "archived":
        activity["status"] = "archived"
        activity["status_label"] = "В архиве"


def _find_stored_activity(block: dict[str, Any], activity_id: str, search_id: str) -> Optional[dict[str, Any]]:
    for act in _migrate_stored_activities(block, search_id):
        if str(act.get("id")) == activity_id:
            return act
    return None


def _build_recommendations(activities: list[dict[str, Any]], search_fill: dict[str, Any]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if int(search_fill.get("pct") or 0) >= 100:
        recs.append(
            {
                "kind": "search_filled",
                "title": "Подбор закрыт — часть рекламы можно остановить",
                "severity": "info",
            }
        )
    for act in activities:
        name = str(act.get("name") or "Активность")
        history = [h for h in (act.get("metrics_history") or []) if isinstance(h, dict)]
        if len(history) >= 14:
            recent = _sum_history(history, 7)
            prev = _sum_history(history[:-7], 7)
            if prev.get("leads", 0) > 0 and recent.get("leads", 0) == 0:
                recs.append(
                    {
                        "kind": "no_recent_leads",
                        "activity_id": act.get("id"),
                        "title": f"«{name}» перестала давать отклики за последние 7 дней",
                        "severity": "warning",
                    }
                )
            rcpl = recent.get("cpl")
            pcpl = prev.get("cpl")
            if rcpl and pcpl and float(pcpl) > 0:
                delta = (float(rcpl) - float(pcpl)) / float(pcpl)
                if delta >= 0.25:
                    recs.append(
                        {
                            "kind": "cpl_up",
                            "activity_id": act.get("id"),
                            "title": f"«{name}»: CPL вырос на {int(round(delta * 100))}% за неделю",
                            "severity": "warning",
                        }
                    )
        cph = (act.get("funnel") or {}).get("cost_per_hire")
        cpl = (act.get("metrics") or {}).get("period_7d", {}).get("cpl")
        if cph and cpl and float(cpl) > float(cph) * 1.3:
            recs.append(
                {
                    "kind": "cpl_vs_hire",
                    "activity_id": act.get("id"),
                    "title": f"«{name}»: CPL высокий, но стоимость трудоустройства всё ещё приемлема — смотрите воронку",
                    "severity": "info",
                }
            )
    return recs[:6]


async def _sync_meta_activities(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    *,
    stored_activities: list[dict[str, Any]],
    funnel: dict[str, Any],
    record_history: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    token, _ = await _resolve_access_token(db, tenant_id)
    ads_map = await crud.list_meta_ads_map(db, tenant_id=tenant_id, search=None, limit=500)
    vacancy_ads = [row for row in ads_map if str(row.vacancy_id) == vacancy_id]

    by_campaign: dict[str, dict[str, Any]] = {}
    graph_errors = 0

    for row in vacancy_ads:
        ad_id = str(row.ad_id)
        campaign_id = "unmapped"
        campaign_name = (row.note or "").strip() or f"Объявление {ad_id}"
        insights_7d: dict[str, Any] = {}
        insights_today: dict[str, Any] = {}

        if token:
            try:
                ad_node = await fetch_ad_node(ad_id, token)
                campaign_id = str(ad_node.get("campaign_id") or campaign_id)
                if campaign_id != "unmapped":
                    camp = await fetch_campaign_node(campaign_id, token)
                    campaign_name = str(camp.get("name") or campaign_name)
                insights_7d = normalize_insights_row(await fetch_ad_insights(ad_id, token, date_preset="last_7d"))
                insights_today = normalize_insights_row(await fetch_ad_insights(ad_id, token, date_preset="today"))
            except Exception as exc:
                graph_errors += 1
                warnings.append(f"ad_{ad_id}:{exc}")

        bucket = by_campaign.setdefault(
            campaign_id,
            {
                "metrics": {"today": {}, "period_7d": {}},
                "provider": {"meta": {"campaign_id": campaign_id, "ad_ids": []}},
            },
        )
        bucket["provider"]["meta"]["ad_ids"].append(ad_id)
        bucket["_campaign_name"] = campaign_name
        for period, src in (("period_7d", insights_7d), ("today", insights_today)):
            dest = bucket["metrics"][period]
            for key in ("spend", "impressions", "clicks", "leads", "ctr"):
                if key in src:
                    dest[key] = round(float(dest.get(key) or 0) + float(src.get(key) or 0), 4 if key == "ctr" else 2)
            if dest.get("leads"):
                dest["cpl"] = round(float(dest.get("spend") or 0) / float(dest["leads"]), 2)

    # Match user activities by meta campaign_id or create auto activities
    user_by_campaign: dict[str, dict[str, Any]] = {}
    for act in stored_activities:
        if act.get("channel_type") != "meta" and act.get("type") != "meta":
            continue
        cid = str((act.get("provider") or {}).get("meta", {}).get("campaign_id") or "")
        if cid:
            user_by_campaign[cid] = act

    meta_activities: list[dict[str, Any]] = []
    for campaign_id, bucket in by_campaign.items():
        campaign_name = bucket.get("_campaign_name", campaign_id)
        existing = user_by_campaign.get(campaign_id)
        if existing:
            act = existing
        else:
            # Auto activity from Meta — user can rename later
            act = {
                "id": f"act_meta_{campaign_id}",
                "channel_type": "meta",
                "type": "meta",
                "name": campaign_name,
                "search_ids": [vacancy_id],
                "status": "draft",
                "audience": {},
                "metrics_history": [],
                "created_at": _utc_now_iso(),
            }
        act["provider"] = bucket["provider"]
        act["metrics"] = bucket["metrics"]
        act.setdefault("search_ids", [vacancy_id])
        if vacancy_id not in [str(x) for x in act["search_ids"]]:
            act["search_ids"] = list(act["search_ids"]) + [vacancy_id]
        metrics_7d = act["metrics"]["period_7d"]
        metrics_today = act["metrics"]["today"]
        act["funnel"] = dict(funnel)
        has_activity = int(metrics_7d.get("leads") or 0) > 0
        status, status_label = _activity_status(meta_connected=bool(token), has_activity=has_activity, graph_errors=graph_errors)
        act["status"] = status
        act["status_label"] = status_label
        act["next_action"] = _next_action_from_metrics(metrics_7d, metrics_today)
        if record_history:
            _record_metrics_history(act, metrics_today, funnel)
        _apply_lifecycle_status(act)
        meta_activities.append(act)

    # User draft meta activities without ads yet
    for act in stored_activities:
        if act.get("channel_type") != "meta" and act.get("type") != "meta":
            continue
        if act.get("status") == "archived":
            continue
        if any(a.get("id") == act.get("id") for a in meta_activities):
            continue
        act.setdefault("search_ids", [vacancy_id])
        act.setdefault("metrics_history", [])
        act.setdefault("audience", {})
        _apply_lifecycle_status(act)
        meta_activities.append(act)

    return meta_activities, warnings


def _static_activities(*, public_url: str, search_id: str, funnel: dict[str, Any]) -> list[dict[str, Any]]:
    if not public_url:
        return []
    responses = int(funnel.get("leads") or funnel.get("candidates") or 0)
    base = {
        "search_ids": [search_id],
        "status": "active",
        "status_label": "Активна",
        "funnel": dict(funnel),
        "metrics": {"today": {}, "period_7d": {"responses": responses}},
        "metrics_history": [],
        "audience": {},
    }
    return [
        {**base, "id": "act_public_link", "channel_type": "public_link", "type": "public_link", "name": "Публичная ссылка", "public_url": public_url},
        {**base, "id": "act_qr", "channel_type": "qr", "type": "qr", "name": "QR-код", "public_url": public_url},
    ]


def _aggregate_overview(activities: list[dict[str, Any]], funnel: dict[str, Any]) -> dict[str, Any]:
    spend = 0.0
    leads = 0
    for act in activities:
        m = (act.get("metrics") or {}).get("period_7d") or {}
        spend += float(m.get("spend") or 0)
        leads += int(m.get("leads") or m.get("responses") or 0)
    return {
        "spend_7d": round(spend, 2),
        "leads_7d": leads,
        "cpl_7d": round(spend / leads, 2) if leads > 0 else None,
        "funnel": funnel,
    }


def _aggregate_analytics(activities: list[dict[str, Any]]) -> dict[str, Any]:
    merged_history: dict[str, dict[str, Any]] = {}
    for act in activities:
        for row in act.get("metrics_history") or []:
            if not isinstance(row, dict):
                continue
            d = str(row.get("date") or "")
            if not d:
                continue
            bucket = merged_history.setdefault(
                d,
                {"date": d, "spend": 0.0, "leads": 0, "candidates": 0, "hired": 0},
            )
            bucket["spend"] = round(bucket["spend"] + float(row.get("spend") or 0), 2)
            bucket["leads"] += int(row.get("leads") or 0)
            bucket["candidates"] = max(bucket["candidates"], int(row.get("candidates") or 0))
            bucket["hired"] = max(bucket["hired"], int(row.get("hired") or 0))
    history = sorted(merged_history.values(), key=lambda x: x["date"])
    for row in history:
        if row["leads"] > 0:
            row["cpl"] = round(row["spend"] / row["leads"], 2)
    return {"history": history[-METRICS_HISTORY_MAX_DAYS:]}


def _merge_audience(activities: list[dict[str, Any]], stored_block: dict[str, Any]) -> dict[str, Any]:
    default = stored_block.get("audience_default")
    if isinstance(default, dict):
        return default
    for act in activities:
        aud = act.get("audience")
        if isinstance(aud, dict) and aud:
            return aud
    return {}


async def build_acquisition_snapshot(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Vacancy,
    *,
    sync_meta: bool = False,
    sync_error: Optional[str] = None,
) -> dict[str, Any]:
    search_id = str(vacancy.id)
    extra = _loads_extra(vacancy.extra)
    stored_block = extra.get(ACQUISITION_EXTRA_KEY)
    if not isinstance(stored_block, dict):
        stored_block = {}

    stored_activities = _migrate_stored_activities(stored_block, search_id)
    stored_activities = [a for a in stored_activities if _activity_visible_for_search(a, search_id)]

    funnel_counts = await _count_candidates_funnel(db, tenant_id, search_id)
    leads_total = await _count_leads(db, tenant_id, search_id)
    funnel = {
        "leads": leads_total,
        "candidates": funnel_counts["candidates"],
        "interviews": funnel_counts["interviews"],
        "offers": funnel_counts["offers"],
        "hired": funnel_counts["hired"],
        "cost_per_hire": None,
    }

    headcount = int(getattr(vacancy, "headcount_target", 0) or 0)
    hired = int(funnel_counts["hired"])
    fill_pct = int(round((hired / headcount) * 100)) if headcount > 0 else None
    search_fill = {"headcount_target": headcount or None, "hired": hired, "pct": fill_pct}

    slug = str(extra.get("lead_form_slug") or "").strip()
    public_url = f"/public/intake/{slug}?vacancy_id={vacancy.id}" if slug else ""

    warnings: list[str] = []
    non_meta = [
        a
        for a in stored_activities
        if a.get("channel_type") not in ("meta",) and a.get("type") != "meta" and str(a.get("lifecycle") or "active") != "archived"
    ]

    if sync_meta:
        meta_activities, warnings = await _sync_meta_activities(
            db, tenant_id, search_id, stored_activities=stored_activities, funnel=funnel, record_history=True
        )
    else:
        meta_activities = [a for a in stored_activities if a.get("channel_type") == "meta" or a.get("type") == "meta"]
        if not meta_activities:
            meta_activities, warnings = await _sync_meta_activities(
                db, tenant_id, search_id, stored_activities=[], funnel=funnel, record_history=False
            )

    activities = _static_activities(public_url=public_url, search_id=search_id, funnel=funnel) + non_meta + meta_activities
    activities = [a for a in activities if str(a.get("lifecycle") or "active") != "archived"]

    total_spend = sum(float((a.get("metrics") or {}).get("period_7d", {}).get("spend") or 0) for a in meta_activities)
    if hired > 0 and total_spend > 0:
        funnel["cost_per_hire"] = round(total_spend / hired, 2)
        for act in activities:
            if act.get("funnel"):
                act["funnel"]["cost_per_hire"] = funnel["cost_per_hire"]

    all_search_ids: set[str] = set()
    for act in activities:
        for sid in act.get("search_ids") or []:
            all_search_ids.add(str(sid))
    titles = await _search_titles(db, tenant_id, list(all_search_ids))
    for act in activities:
        act["search_titles"] = [titles.get(str(sid), str(sid)) for sid in (act.get("search_ids") or [])]

    prev_sync = stored_block.get("sync") if isinstance(stored_block.get("sync"), dict) else {}
    now = _utc_now_iso()
    sync_state = {
        "last_sync_at": now if sync_meta else prev_sync.get("last_sync_at"),
        "last_sync_ok_at": now if sync_meta and not sync_error else prev_sync.get("last_sync_ok_at"),
        "last_sync_error": sync_error if sync_meta else prev_sync.get("last_sync_error"),
        "sync_interval_minutes": SYNC_INTERVAL_MINUTES,
    }

    _record_sync_journal_events(
        stored_block,
        sync_meta=sync_meta,
        sync_error=sync_error,
        activities=activities,
        funnel=funnel,
    )
    for act in activities:
        _enrich_activity_controls(act, sync_state)

    search_title = str(getattr(vacancy, "title", None) or search_id)
    attention = _build_attention_items(activities, search_fill, search_title=search_title)
    recommendations = _build_recommendations(activities, search_fill)
    journal = _get_event_log(stored_block)

    reconciliation = await resolve_search_campaign_reconciliation(
        db, tenant_id=tenant_id, search_id=search_id
    )
    snapshot = {
        "version": 2,
        "synced_at": now,
        "search_fill": search_fill,
        "activities": activities,
        "channels": activities,
        "attention": attention,
        "journal": journal,
        "overview": {
            **_aggregate_overview(activities, funnel),
            "recommendations": recommendations,
        },
        "audience": _merge_audience(activities, stored_block),
        "analytics": _aggregate_analytics(activities),
        "sync": sync_state,
        "watch_state": stored_block.get("watch_state") if isinstance(stored_block.get("watch_state"), dict) else {},
        "warnings": warnings,
        "legacy_mode": True,
        "reconciliation": reconciliation,
        "marketing_setup_path": marketing_setup_path_for_search(search_id, name=search_title),
    }
    return snapshot


async def persist_acquisition_snapshot(db: AsyncSession, vacancy: Vacancy, snapshot: dict[str, Any]) -> dict[str, Any]:
    extra = _loads_extra(vacancy.extra)
    block = extra.get(ACQUISITION_EXTRA_KEY)
    if not isinstance(block, dict):
        block = {}
    block["activities"] = _persistable_activities(snapshot.get("activities") or [])
    block["channels"] = block["activities"]
    block["sync"] = snapshot.get("sync")
    if isinstance(snapshot.get("audience"), dict):
        block["audience_default"] = snapshot["audience"]
    if isinstance(snapshot.get("journal"), list):
        block["event_log"] = snapshot["journal"]
    if isinstance(snapshot.get("watch_state"), dict):
        block["watch_state"] = snapshot["watch_state"]
    block["version"] = snapshot.get("version", 2)
    extra[ACQUISITION_EXTRA_KEY] = block
    vacancy.extra = json.dumps(extra, ensure_ascii=False)
    await db.flush()
    return snapshot


async def add_acquisition_activity(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Vacancy,
    *,
    channel_type: str,
    name: str,
) -> dict[str, Any]:
    search_id = str(vacancy.id)
    if LEGACY_LAUNCH_DISABLED:
        raise LegacyLaunchDisabledError(
            search_id=search_id,
            marketing_setup_path=marketing_setup_path_for_search(
                search_id, name=str(getattr(vacancy, "title", None) or name)
            ),
        )
    extra = _loads_extra(vacancy.extra)
    block = extra.get(ACQUISITION_EXTRA_KEY)
    if not isinstance(block, dict):
        block = {}
    activities = _migrate_stored_activities(block, search_id)

    activity = {
        "id": f"act_{channel_type}_{uuid.uuid4().hex[:8]}",
        "channel_type": channel_type,
        "type": channel_type,
        "name": name.strip(),
        "search_ids": [search_id],
        "lifecycle": "active",
        "status": "draft",
        "status_label": "Настройка",
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "metrics": {"today": {}, "period_7d": {}},
        "metrics_history": [],
        "audience": {},
        "funnel": {},
        "next_action": {"kind": "setup", "title": "Завершите настройку активности", "severity": "info"},
    }
    activities.append(activity)
    block["activities"] = activities
    block["channels"] = activities
    _append_event(block, kind="activity_created", title=f'Создана новая активность «{name.strip()}».', activity_id=activity["id"])
    extra[ACQUISITION_EXTRA_KEY] = block
    vacancy.extra = json.dumps(extra, ensure_ascii=False)
    await db.flush()
    snapshot = await build_acquisition_snapshot(db, tenant_id, vacancy, sync_meta=False)
    snapshot["journal"] = _get_event_log(block)
    await persist_acquisition_snapshot(db, vacancy, snapshot)
    return activity


async def update_acquisition_audience(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Vacancy,
    audience: dict[str, Any],
) -> dict[str, Any]:
    extra = _loads_extra(vacancy.extra)
    block = extra.get(ACQUISITION_EXTRA_KEY)
    if not isinstance(block, dict):
        block = {}
    block["audience_default"] = audience
    extra[ACQUISITION_EXTRA_KEY] = block
    vacancy.extra = json.dumps(extra, ensure_ascii=False)
    await db.flush()
    snapshot = await build_acquisition_snapshot(db, tenant_id, vacancy, sync_meta=False)
    snapshot["journal"] = _get_event_log(block)
    await persist_acquisition_snapshot(db, vacancy, snapshot)
    return audience


async def perform_acquisition_activity_action(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Vacancy,
    activity_id: str,
    action: str,
    *,
    search_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    if activity_id in STATIC_ACTIVITY_IDS:
        raise ValueError("static_activity")

    search_id = str(vacancy.id)
    extra = _loads_extra(vacancy.extra)
    block = extra.get(ACQUISITION_EXTRA_KEY)
    if not isinstance(block, dict):
        block = {}
    activities = _migrate_stored_activities(block, search_id)
    target = _find_stored_activity(block, activity_id, search_id)
    if not target:
        raise LookupError("activity_not_found")

    name = str(target.get("name") or "Активность")
    now = _utc_now_iso()

    if action == "pause":
        target["lifecycle"] = "paused"
        target["updated_at"] = now
        _append_event(block, kind="activity_paused", title=f"Активность «{name}» приостановлена.", activity_id=activity_id)
    elif action == "resume":
        target["lifecycle"] = "active"
        target["updated_at"] = now
        _append_event(block, kind="activity_resumed", title=f"Активность «{name}» возобновлена.", activity_id=activity_id)
    elif action == "archive":
        target["lifecycle"] = "archived"
        target["updated_at"] = now
        _append_event(block, kind="activity_archived", title=f"Активность «{name}» архивирована.", activity_id=activity_id)
    elif action == "duplicate":
        if LEGACY_LAUNCH_DISABLED:
            raise LegacyLaunchDisabledError(
                search_id=search_id,
                marketing_setup_path=marketing_setup_path_for_search(
                    search_id, name=str(getattr(vacancy, "title", None) or name)
                ),
            )
        clone = dict(target)
        clone["id"] = f"act_{target.get('channel_type', 'meta')}_{uuid.uuid4().hex[:8]}"
        clone["name"] = f"{name} (копия)"
        clone["lifecycle"] = "active"
        clone["created_at"] = now
        clone["updated_at"] = now
        clone["metrics"] = {"today": {}, "period_7d": {}}
        clone["metrics_history"] = []
        clone.pop("provider", None)
        activities.append(clone)
        _append_event(block, kind="activity_duplicated", title=f"Создана копия активности «{name}».", activity_id=clone["id"])
        target = clone
    elif action == "update_bindings":
        if not search_ids:
            raise ValueError("search_ids_required")
        normalized = list(dict.fromkeys(str(s) for s in search_ids))
        if search_id not in normalized:
            normalized.insert(0, search_id)
        target["search_ids"] = normalized
        target["updated_at"] = now
        titles = await _search_titles(db, tenant_id, normalized)
        label = ", ".join(titles.get(sid, sid) for sid in normalized)
        _append_event(
            block,
            kind="bindings_updated",
            title=f"Обновлена привязка «{name}»: {label}.",
            activity_id=activity_id,
        )
    else:
        raise ValueError("unknown_action")

    block["activities"] = activities
    block["channels"] = activities
    extra[ACQUISITION_EXTRA_KEY] = block
    vacancy.extra = json.dumps(extra, ensure_ascii=False)
    await db.flush()

    snapshot = await build_acquisition_snapshot(db, tenant_id, vacancy, sync_meta=False)
    snapshot["journal"] = _get_event_log(block)
    await persist_acquisition_snapshot(db, vacancy, snapshot)
    return {"activity": target, "snapshot": snapshot}


async def get_vacancy_or_raise(db: AsyncSession, tenant_id: str, vacancy_id: str) -> Vacancy:
    row = (
        await db.execute(select(Vacancy).where(Vacancy.tenant_id == tenant_id, Vacancy.id == vacancy_id))
    ).scalar_one_or_none()
    if not row:
        raise LookupError("vacancy_not_found")
    return row


# Backward-compatible alias
add_acquisition_channel = add_acquisition_activity
