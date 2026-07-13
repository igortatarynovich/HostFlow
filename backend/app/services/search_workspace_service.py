"""Search (подбор) day plan — cross-section «Сегодня» / «Потом»."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import STAGES_BY_GROUP
from backend.app.constants.spa_paths import CANDIDATES
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.services.search_acquisition_service import (
    build_acquisition_snapshot,
    get_vacancy_or_raise,
)

_RECRUITMENT_SEARCH_BASE = "/app/recruitment/searches"
_PRE_CONTACT_STAGES = frozenset({"", "new", "no_answer", "to_call", "to_contact"})
_INTERVIEW_STAGES = frozenset(STAGES_BY_GROUP.get("interview", []))
_DOCS_WAIT_STAGES = frozenset({"docs_wait"})

DayMode = Literal["operate", "wait_leads", "near_goal", "filled", "idle"]


def _utc_cutoff_naive(*, days: int = 0) -> datetime:
    """Naive UTC timestamp for columns stored as timestamp without time zone."""
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _search_path(search_id: str, suffix: str = "") -> str:
    base = f"{_RECRUITMENT_SEARCH_BASE}/{search_id}"
    return f"{base}{suffix}" if suffix else base


def _item(
    *,
    id: str,
    severity: str,
    headline: str,
    message: str,
    action_label: str,
    target: str,
    href: str,
    bucket: Literal["today", "later"] = "today",
    activity_id: str | None = None,
    icon: str = "",
    kind: str = "",
    work_kind: str | None = None,
    queue: list[str] | None = None,
    count: int | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "severity": severity,
        "headline": headline,
        "message": message,
        "action_label": action_label,
        "target": target,
        "href": href,
        "bucket": bucket,
        "activity_id": activity_id,
        "icon": icon,
        "kind": kind or id,
        "work_kind": work_kind,
        "queue": queue or [],
        "count": count,
    }


_REASON_BY_KIND: dict[str, str] = {
    "candidates_awaiting_call": "Это сейчас самое важное для закрытия подбора.",
    "candidates_missing_docs": "Без документов кандидаты не двигаются дальше.",
    "candidates_stale_interview": "Интервью — следующий шаг к трудоустройству.",
    "acquisition_launch": "Нужен приток новых откликов.",
    "wait_leads": "Новые отклики обрабатываются в разделе «Отклики», не здесь.",
    "search_near_goal": "Финальный рывок до закрытия подбора.",
    "search_filled": "Подбор достиг цели.",
}


def _with_next_action_fields(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)
    kind = str(row.get("kind") or row.get("id") or "")
    row["reason"] = _REASON_BY_KIND.get(kind, "Это сейчас самое важное для закрытия подбора.")
    if row.get("queue"):
        row["action_label"] = "Начать"
    return row


def _has_running_ads(activities: list[dict[str, Any]]) -> bool:
    for act in activities:
        if str(act.get("lifecycle") or "active") == "archived":
            continue
        ch = act.get("channel_type") or act.get("type")
        if ch not in ("meta", "google", "tiktok"):
            continue
        status = str(act.get("status") or "")
        spend = float((act.get("metrics") or {}).get("period_7d", {}).get("spend") or 0)
        if status in ("active", "needs_attention") or spend > 0:
            return True
    return False


def _draft_setup_later(activities: list[dict[str, Any]], search_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for act in activities:
        if str(act.get("lifecycle") or "active") == "archived":
            continue
        if str(act.get("status") or "") != "draft":
            continue
        name = str(act.get("name") or "Активность")
        ch = str(act.get("channel_type") or act.get("type") or "")
        if ch == "meta":
            items.append(
                _item(
                    id=f"later_setup_{act.get('id')}",
                    severity="info",
                    headline=f"Настроить «{name}»",
                    message="Подключите Meta и привяжите объявления.",
                    action_label="Настроить",
                    target="acquisition",
                    href=_search_path(search_id, "/acquisition/meta"),
                    bucket="later",
                    activity_id=str(act.get("id") or ""),
                )
            )
        elif ch in ("google", "tiktok", "telegram", "referral"):
            label = {"google": "Google", "tiktok": "TikTok", "telegram": "Telegram", "referral": "Referral"}.get(ch, ch)
            items.append(
                _item(
                    id=f"later_channel_{act.get('id')}",
                    severity="info",
                    headline=f"Подключить {label}",
                    message=f"Активность «{name}» ждёт настройки.",
                    action_label="Открыть",
                    target="acquisition",
                    href=_search_path(search_id, "/acquisition/activities"),
                    bucket="later",
                    activity_id=str(act.get("id") or ""),
                )
            )
    return items


def _build_day_plan(
    *,
    search_id: str,
    search_title: str,
    search_fill: dict[str, Any],
    acquisition_attention: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    audience: dict[str, Any],
    awaiting_call: int,
    docs_wait: int,
    stale_interviews: int,
    active_candidates: int,
    leads_7d: int,
    call_queue: list[str],
    docs_queue: list[str],
    interview_queue: list[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], DayMode]:
    today: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []

    headcount = int(search_fill.get("headcount_target") or 0)
    hired = int(search_fill.get("hired") or 0)
    remaining = max(0, headcount - hired) if headcount > 0 else 0
    pct = int(search_fill.get("pct") or 0)
    running_ads = _has_running_ads(activities)
    filled = headcount > 0 and remaining == 0

    candidates_href = f"{CANDIDATES}?vacancy_id={search_id}"

    if awaiting_call > 0:
        if awaiting_call == 1:
            headline = "Свяжитесь с новым кандидатом"
            message = "1 кандидат ждёт первого контакта."
        else:
            headline = f"Позвонить {awaiting_call} новым кандидатам"
            message = f"{awaiting_call} кандидатов ждут первого контакта."
        today.append(
            _item(
                id="candidates_awaiting_call",
                severity="error",
                headline=headline,
                message=message,
                action_label="Начать",
                target="candidates",
                href=f"{candidates_href}&attention=call",
                icon="📞",
                kind="candidates_awaiting_call",
                work_kind="call",
                queue=call_queue,
                count=awaiting_call,
            )
        )

    if docs_wait > 0:
        docs_label = "одного кандидата" if docs_wait == 1 else f"{docs_wait} кандидатов"
        today.append(
            _item(
                id="candidates_missing_docs",
                severity="warning" if docs_wait <= 2 else "error",
                headline="Проверить документы",
                message=f"У {docs_label} не хватает документов.",
                action_label="Начать",
                target="documents",
                href=f"{candidates_href}&attention=docs",
                icon="📄",
                kind="candidates_missing_docs",
                work_kind="docs",
                queue=docs_queue,
                count=docs_wait,
            )
        )

    if stale_interviews > 0:
        today.append(
            _item(
                id="candidates_stale_interview",
                severity="warning",
                headline="Провести интервью",
                message=f"По {stale_interviews} кандидатам не было движения более 4 дней.",
                action_label="Начать",
                target="candidates",
                href=f"{candidates_href}&attention=interview",
                icon="🤝",
                kind="candidates_stale_interview",
                work_kind="interview",
                queue=interview_queue,
                count=stale_interviews,
            )
        )

    need_ads = not filled and (remaining > 0 or headcount == 0) and leads_7d == 0 and active_candidates <= max(3, remaining or 3)
    if need_ads and not running_ads:
        today.append(
            _item(
                id="acquisition_launch",
                severity="error",
                headline="Запустить рекламу",
                message=f"Поток откликов слабый — нужна реклама для «{search_title}».",
                action_label="Запустить",
                target="acquisition",
                href=_search_path(search_id, "/acquisition/new"),
                icon="🚀",
                kind="acquisition_launch",
            )
        )
    elif need_ads and running_ads:
        later.append(
            _item(
                id="acquisition_expand",
                severity="info",
                headline="Расширить рекламу",
                message="Можно добавить активность в другой стране или канале.",
                action_label="Новая активность",
                target="acquisition",
                href=_search_path(search_id, "/acquisition/new"),
                bucket="later",
            )
        )

    for row in acquisition_attention:
        kind = str(row.get("kind") or row.get("id") or "")
        if kind in {"search_near_goal", "search_filled"}:
            continue
        act_id = row.get("activity_id")
        href = _search_path(search_id, "/acquisition/activities")
        if act_id:
            href = f"{href}?highlight={act_id}"
        acq_item = _item(
            id=f"acq_{row.get('id') or kind}",
            severity=str(row.get("severity") or "warning"),
            headline=str(row.get("headline") or "Реклама"),
            message=str(row.get("message") or ""),
            action_label="Посмотреть",
            target="acquisition",
            href=href,
            activity_id=str(act_id) if act_id else None,
        )
        if str(row.get("severity")) == "error":
            today.append(acq_item)
        else:
            acq_item["bucket"] = "later"
            later.append(acq_item)

    if filled:
        today.append(
            _item(
                id="search_filled",
                severity="success",
                headline="Подбор закрыт",
                message="Часть рекламы можно остановить.",
                action_label="Привлечение",
                target="acquisition",
                href=_search_path(search_id, "/acquisition/activities"),
                icon="🎉",
                kind="search_filled",
            )
        )
    elif headcount > 0 and 0 < remaining <= 3 and pct >= 60:
        pass  # near_goal promoted to today when blocking queue is empty

    audience_empty = not any(
        audience.get(k)
        for k in ("countries", "languages", "experience", "interests")
        if isinstance(audience.get(k), list) and audience.get(k) or audience.get(k)
    )
    if audience_empty:
        later.append(
            _item(
                id="audience_setup",
                severity="info",
                headline="Настроить аудиторию",
                message="Опишите, кого ищете — позже это поможет с таргетингом.",
                action_label="Аудитория",
                target="acquisition",
                href=_search_path(search_id, "/acquisition/audience"),
                bucket="later",
            )
        )

    later.extend(_draft_setup_later(activities, search_id))

    blocking_today = [i for i in today if i.get("id") not in {"search_filled"}]
    if not blocking_today and running_ads and awaiting_call == 0:
        today.append(
            _item(
                id="wait_leads",
                severity="success",
                headline="Ждём новые отклики",
                message="Реклама работает. Новые необработанные отклики — в разделе «Отклики».",
                action_label="Открыть отклики",
                target="recruitment_inbox",
                href="/app/recruitment/inbox",
                icon="⏳",
                kind="wait_leads",
            )
        )

    if (
        not blocking_today
        and headcount > 0
        and 0 < remaining <= 3
        and pct >= 60
        and not filled
    ):
        today.insert(
            0,
            _item(
                id="search_near_goal",
                severity="success",
                headline="Подбор почти закрыт",
                message=f"Осталось найти ещё {remaining} человек.",
                action_label="Кандидаты",
                target="candidates",
                href=candidates_href,
                icon="🎉",
                kind="search_near_goal",
            ),
        )
        later = [i for i in later if i.get("id") != "search_near_goal"]

    blocking_today = [i for i in today if i.get("id") not in {"search_filled", "wait_leads"}]

    if filled:
        mode: DayMode = "filled"
    elif headcount > 0 and 0 < remaining <= 3 and pct >= 60 and not blocking_today:
        mode = "near_goal"
    elif blocking_today:
        mode = "operate"
    elif running_ads and awaiting_call == 0:
        mode = "wait_leads"
    elif not today and not later:
        mode = "idle"
    else:
        mode = "operate"

    severity_order = {"error": 0, "warning": 1, "success": 2, "info": 3}
    kind_order = [
        "candidates_awaiting_call",
        "candidates_missing_docs",
        "candidates_stale_interview",
        "acquisition_launch",
        "search_near_goal",
        "wait_leads",
        "search_filled",
    ]
    today.sort(
        key=lambda x: (
            kind_order.index(str(x.get("id")))
            if str(x.get("id")) in kind_order
            else 50,
            severity_order.get(str(x.get("severity")), 9),
        )
    )
    later.sort(key=lambda x: severity_order.get(str(x.get("severity")), 9))

    next_action = _with_next_action_fields(today[0]) if today else None
    after_that = today[1:6]
    return next_action, after_that, later[:8], mode


async def _count_candidates_by_stages(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    stages: frozenset[str],
) -> int:
    if not stages:
        return 0
    total = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.vacancy_id == vacancy_id,
                Candidate.deleted_at.is_(None),
                Candidate.stage.in_(list(stages)),
            )
        )
    ).scalar_one()
    return int(total or 0)


async def _list_candidate_ids_by_stages(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    stages: frozenset[str],
    *,
    limit: int = 50,
) -> list[str]:
    if not stages:
        return []
    rows = (
        await db.execute(
            select(Candidate.id)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.vacancy_id == vacancy_id,
                Candidate.deleted_at.is_(None),
                Candidate.stage.in_(list(stages)),
            )
            .order_by(Candidate.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [str(r) for r in rows]


async def _list_stale_interview_ids(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    *,
    idle_days: int = 4,
    limit: int = 50,
) -> list[str]:
    if not _INTERVIEW_STAGES:
        return []
    cutoff = _utc_cutoff_naive(days=idle_days)
    rows = (
        await db.execute(
            select(Candidate.id)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.vacancy_id == vacancy_id,
                Candidate.deleted_at.is_(None),
                Candidate.stage.in_(list(_INTERVIEW_STAGES)),
                Candidate.updated_at <= cutoff,
            )
            .order_by(Candidate.updated_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [str(r) for r in rows]


async def _count_stale_interview_candidates(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    *,
    idle_days: int = 4,
) -> int:
    if not _INTERVIEW_STAGES:
        return 0
    cutoff = _utc_cutoff_naive(days=idle_days)
    total = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.vacancy_id == vacancy_id,
                Candidate.deleted_at.is_(None),
                Candidate.stage.in_(list(_INTERVIEW_STAGES)),
                Candidate.updated_at <= cutoff,
            )
        )
    ).scalar_one()
    return int(total or 0)


async def _count_active_pipeline_candidates(db: AsyncSession, tenant_id: str, vacancy_id: str) -> int:
    terminal = set(STAGES_BY_GROUP.get("rejected", [])) | {"employed", "hired", "declined", "probation_ok"}
    total = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.vacancy_id == vacancy_id,
                Candidate.deleted_at.is_(None),
                Candidate.stage.notin_(list(terminal)),
            )
        )
    ).scalar_one()
    return int(total or 0)


async def build_search_workspace_pulse(
    db: AsyncSession,
    tenant_id: str,
    vacancy: Vacancy,
) -> dict[str, Any]:
    search_id = str(vacancy.id)
    search_title = str(getattr(vacancy, "title", None) or search_id)

    acquisition = await build_acquisition_snapshot(db, tenant_id, vacancy, sync_meta=False)
    search_fill = acquisition.get("search_fill") or {}
    overview = acquisition.get("overview") or {}
    acquisition_attention = acquisition.get("attention") or []
    activities = acquisition.get("activities") or []
    audience = acquisition.get("audience") or {}

    awaiting_call = await _count_candidates_by_stages(db, tenant_id, search_id, _PRE_CONTACT_STAGES)
    docs_wait = await _count_candidates_by_stages(db, tenant_id, search_id, _DOCS_WAIT_STAGES)
    stale_interviews = await _count_stale_interview_candidates(db, tenant_id, search_id)
    call_queue = await _list_candidate_ids_by_stages(db, tenant_id, search_id, _PRE_CONTACT_STAGES)
    docs_queue = await _list_candidate_ids_by_stages(db, tenant_id, search_id, _DOCS_WAIT_STAGES)
    interview_queue = await _list_stale_interview_ids(db, tenant_id, search_id)
    active_candidates = await _count_active_pipeline_candidates(db, tenant_id, search_id)
    leads_7d = int(overview.get("leads_7d") or 0)

    next_action, after_that, later, mode = _build_day_plan(
        search_id=search_id,
        search_title=search_title,
        search_fill=search_fill,
        acquisition_attention=acquisition_attention,
        activities=activities,
        audience=audience if isinstance(audience, dict) else {},
        awaiting_call=awaiting_call,
        docs_wait=docs_wait,
        stale_interviews=stale_interviews,
        active_candidates=active_candidates,
        leads_7d=leads_7d,
        call_queue=call_queue,
        docs_queue=docs_queue,
        interview_queue=interview_queue,
    )

    status_label = "Активен"
    vacancy_status = str(getattr(vacancy, "status", "") or "").strip().lower()
    if bool(getattr(vacancy, "is_archived", False)):
        status_label = "В архиве"
    elif vacancy_status in {"closed", "filled", "cancelled"}:
        status_label = "Закрыт"
    elif vacancy_status in {"on_hold", "paused"}:
        status_label = "На паузе"

    mode_labels = {
        "operate": "Работаем",
        "wait_leads": "Ждём отклики",
        "near_goal": "Финиш близко",
        "filled": "Закрыт",
        "idle": "Всё спокойно",
    }

    return {
        "search_id": search_id,
        "mode": mode,
        "mode_label": mode_labels.get(mode, mode_labels["operate"]),
        "next_action": next_action,
        "after_that": after_that,
        "today": [next_action, *after_that] if next_action else after_that,
        "later": later,
        "attention": ([next_action] if next_action else []) + after_that + later,
        "status": {
            "label": status_label,
            "fill_pct": search_fill.get("pct"),
            "hired": search_fill.get("hired"),
            "headcount_target": search_fill.get("headcount_target"),
            "active_candidates": active_candidates,
            "awaiting_call": awaiting_call,
            "leads_7d": leads_7d,
        },
    }


async def get_search_workspace_pulse(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
) -> dict[str, Any]:
    vacancy = await get_vacancy_or_raise(db, tenant_id, vacancy_id)
    return await build_search_workspace_pulse(db, tenant_id, vacancy)
