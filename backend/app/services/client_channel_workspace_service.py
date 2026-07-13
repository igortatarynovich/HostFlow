"""Client channel (Sales) day plan — cross-section «Следующее действие»."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.intake_routing_enums import IntakeProvider, RouteIntent
from backend.app.models.lead import Lead

_CLIENT_CHANNEL_BASE = "/app/client-acquisition/channels"

DayMode = Literal["operate", "wait_inquiries", "idle"]


def _inquiry_path(channel_id: str, lead_id: str) -> str:
    return f"/app/client-acquisition/channels/{channel_id}/inquiries/{lead_id}"


def _channel_path(channel_id: str, suffix: str = "") -> str:
    base = f"{_CLIENT_CHANNEL_BASE}/{channel_id}"
    return f"{base}{suffix}" if suffix else base


def _lead_path(channel_id: str, lead_id: str) -> str:
    return _inquiry_path(channel_id, lead_id)


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
        "icon": icon,
        "kind": kind or id,
        "work_kind": work_kind,
        "queue": queue or [],
        "count": count,
    }


_REASON_BY_KIND: dict[str, str] = {
    "inquiries_awaiting_call": "Новые запросы компаний ждут первого звонка.",
    "inquiries_ready_to_convert": "Компании заинтересованы — оформите клиента.",
    "share_channel_link": "Без ссылки компании не смогут оставить заявку.",
    "wait_inquiries": "Канал работает — следите за новыми запросами.",
}


def _with_next_action_fields(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)
    kind = str(row.get("kind") or row.get("id") or "")
    row["reason"] = _REASON_BY_KIND.get(kind, "Это сейчас самое важное для привлечения клиентов.")
    if row.get("queue"):
        row["action_label"] = "Начать"
    return row


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _source_profile_id(lead: Lead) -> str | None:
    norm = _record(lead.normalized)
    meta = _record(norm.get("meta"))
    sp = _record(meta.get("source_profile"))
    pid = str(sp.get("id") or "").strip()
    return pid or None


def _is_open_inquiry(lead: Lead) -> bool:
    if getattr(lead, "converted_client_id", None):
        return False
    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    if stage in {"converted", "lost"}:
        return False
    target = str(getattr(lead, "lead_target_type", "") or "").strip().lower()
    if target and target != "client_lead":
        return False
    return True


def _needs_call(lead: Lead) -> bool:
    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    return stage not in {"contacted", "qualified", "converted", "lost"}


def _needs_conversion(lead: Lead) -> bool:
    stage = str(getattr(lead, "stage", "") or "").strip().lower()
    return stage in {"contacted", "qualified"} and not getattr(lead, "converted_client_id", None)


def _is_today(iso: datetime | None) -> bool:
    if iso is None:
        return False
    if iso.tzinfo is None:
        iso = iso.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return iso.date() == now.date()


async def _load_channel_leads(
    db: AsyncSession,
    tenant_id: str,
    channel_id: str,
    *,
    limit: int = 200,
) -> list[Lead]:
    rows = (
        await db.execute(
            select(Lead)
            .where(
                Lead.tenant_id == tenant_id,
                Lead.lead_type == "client",
                Lead.lead_target_type == "client_lead",
            )
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    out: list[Lead] = []
    for lead in rows:
        if _source_profile_id(lead) != channel_id:
            continue
        if not _is_open_inquiry(lead):
            continue
        out.append(lead)
    return out


def _build_day_plan(
    *,
    channel_id: str,
    channel_name: str,
    public_url: str | None,
    open_inquiries: list[Lead],
    today_count: int,
    converted_count: int,
    call_queue: list[str],
    convert_queue: list[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], DayMode]:
    today: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []

    awaiting_call = len(call_queue)
    ready_convert = len(convert_queue)

    if awaiting_call > 0:
        if awaiting_call == 1:
            headline = "Позвоните новой компании"
            message = "1 запрос компании ждёт первого контакта."
        else:
            headline = f"Позвоните {awaiting_call} компаниям"
            message = f"{awaiting_call} запросов ждут первого контакта."
        today.append(
            _item(
                id="inquiries_awaiting_call",
                severity="error",
                headline=headline,
                message=message,
                action_label="Начать",
                target="inquiries",
                href=_lead_path(channel_id, call_queue[0]),
                icon="📞",
                kind="inquiries_awaiting_call",
                work_kind="call",
                queue=call_queue,
                count=awaiting_call,
            )
        )

    if ready_convert > 0:
        label = "одной компании" if ready_convert == 1 else f"{ready_convert} компаниям"
        today.append(
            _item(
                id="inquiries_ready_to_convert",
                severity="warning" if awaiting_call == 0 else "info",
                headline="Оформить клиента",
                message=f"По {label} уже есть интерес — сохраните клиента в CRM.",
                action_label="Начать" if awaiting_call == 0 else "Открыть",
                target="inquiries",
                href=_lead_path(channel_id, convert_queue[0]),
                icon="✓",
                kind="inquiries_ready_to_convert",
                work_kind="convert",
                queue=convert_queue,
                count=ready_convert,
            )
        )

    if not open_inquiries and public_url:
        today.append(
            _item(
                id="share_channel_link",
                severity="error",
                headline="Запустите привлечение",
                message=f"Скопируйте ссылку или QR для «{channel_name}» и запустите рекламу.",
                action_label="Копировать ссылку",
                target="channel",
                href=_channel_path(channel_id),
                icon="🔗",
                kind="share_channel_link",
                work_kind="share",
            )
        )
    elif not open_inquiries and not public_url:
        today.append(
            _item(
                id="channel_link_missing",
                severity="warning",
                headline="Ссылка недоступна",
                message="Не удалось восстановить публичную ссылку канала.",
                action_label="Открыть",
                target="channel",
                href=_channel_path(channel_id),
                kind="channel_link_missing",
            )
        )

    blocking = [i for i in today if i.get("kind") not in {"wait_inquiries"}]
    if not blocking and open_inquiries:
        today.append(
            _item(
                id="wait_inquiries",
                severity="success",
                headline="Ждём новые запросы",
                message="Канал активен — новые компании появятся здесь автоматически.",
                action_label="Обновить",
                target="channel",
                href=_channel_path(channel_id),
                icon="⏳",
                kind="wait_inquiries",
            )
        )

    severity_order = {"error": 0, "warning": 1, "success": 2, "info": 3}
    kind_order = [
        "inquiries_awaiting_call",
        "inquiries_ready_to_convert",
        "share_channel_link",
        "channel_link_missing",
        "wait_inquiries",
    ]
    today.sort(
        key=lambda x: (
            kind_order.index(str(x.get("kind")))
            if str(x.get("kind")) in kind_order
            else 50,
            severity_order.get(str(x.get("severity")), 9),
        )
    )
    later.sort(key=lambda x: severity_order.get(str(x.get("severity")), 9))

    next_action = _with_next_action_fields(today[0]) if today else None
    after_that = today[1:6]

    if next_action and next_action.get("kind") == "wait_inquiries":
        mode: DayMode = "wait_inquiries"
    elif blocking:
        mode = "operate"
    elif not today and not later:
        mode = "idle"
    else:
        mode = "wait_inquiries" if open_inquiries else "idle"

    return next_action, after_that, later[:8], mode


async def get_client_channel_or_raise(
    db: AsyncSession,
    tenant_id: str,
    channel_id: str,
) -> IntakeSourceProfile:
    sales_channel_filter = or_(
        (
            (IntakeSourceProfile.form_type == "company_intake")
            & (IntakeSourceProfile.lead_type == "client")
            & (IntakeSourceProfile.lead_target_type == "client_lead")
        ),
        (
            (IntakeSourceProfile.provider == IntakeProvider.meta.value)
            & (IntakeSourceProfile.route_intent == RouteIntent.sales_inquiry.value)
            & (IntakeSourceProfile.lead_target_type == "client_lead")
        ),
    )
    row = await db.scalar(
        select(IntakeSourceProfile).where(
            IntakeSourceProfile.tenant_id == tenant_id,
            IntakeSourceProfile.id == channel_id,
            sales_channel_filter,
        )
    )
    if row is None:
        raise LookupError("Client channel not found")
    return row


async def build_client_channel_workspace_pulse(
    db: AsyncSession,
    tenant_id: str,
    channel: IntakeSourceProfile,
) -> dict[str, Any]:
    channel_id = str(channel.id)
    channel_name = str(getattr(channel, "name", None) or channel_id)
    public_slug = str(getattr(channel, "public_slug", "") or "").strip()
    public_url = f"/forms/client-inquiry/{public_slug}" if public_slug else None

    open_inquiries = await _load_channel_leads(db, tenant_id, channel_id)
    today_count = sum(1 for lead in open_inquiries if _is_today(getattr(lead, "created_at", None)))

    all_channel_leads = (
        await db.execute(
            select(Lead)
            .where(
                Lead.tenant_id == tenant_id,
                Lead.lead_type == "client",
                Lead.lead_target_type == "client_lead",
            )
            .order_by(Lead.created_at.desc())
            .limit(300)
        )
    ).scalars().all()
    converted_count = sum(
        1
        for lead in all_channel_leads
        if _source_profile_id(lead) == channel_id and getattr(lead, "converted_client_id", None)
    )

    call_queue = [str(lead.id) for lead in reversed(open_inquiries) if _needs_call(lead)]
    convert_queue = [str(lead.id) for lead in open_inquiries if _needs_conversion(lead)]

    next_action, after_that, later, mode = _build_day_plan(
        channel_id=channel_id,
        channel_name=channel_name,
        public_url=public_url,
        open_inquiries=open_inquiries,
        today_count=today_count,
        converted_count=converted_count,
        call_queue=call_queue,
        convert_queue=convert_queue,
    )

    mode_labels = {
        "operate": "Работаем",
        "wait_inquiries": "Ждём запросы",
        "idle": "Всё спокойно",
    }

    status_label = "Активен" if bool(getattr(channel, "is_active", True)) else "На паузе"

    return {
        "channel_id": channel_id,
        "mode": mode,
        "mode_label": mode_labels.get(mode, mode_labels["operate"]),
        "next_action": next_action,
        "after_that": after_that,
        "today": [next_action, *after_that] if next_action else after_that,
        "later": later,
        "attention": ([next_action] if next_action else []) + after_that + later,
        "status": {
            "label": status_label,
            "open_inquiries": len(open_inquiries),
            "today_inquiries": today_count,
            "converted_clients": converted_count,
            "public_slug": public_slug or None,
            "public_url_path": public_url,
        },
    }


async def get_client_channel_workspace_pulse(
    db: AsyncSession,
    tenant_id: str,
    channel_id: str,
) -> dict[str, Any]:
    channel = await get_client_channel_or_raise(db, tenant_id, channel_id)
    return await build_client_channel_workspace_pulse(db, tenant_id, channel)
