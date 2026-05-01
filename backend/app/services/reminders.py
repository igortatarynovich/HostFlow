from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.services.pipeline_sync import sync_candidate_links
from backend.app.services.document_catalog import get_doc_type_defaults
from backend.app.services.document_workflow import iter_workflow_step_deadlines
from backend.app.services.notification_templates import (
    get_document_expiry_template,
    get_notification_template,
    iter_channel_templates,
)
from backend.app.observability.metrics import (
    increment_reminder_triggered,
    refresh_documents_overdue_metrics,
)
from .notifications import notify


DEFAULT_EXPIRY_OFFSET_HOURS: Tuple[int, ...] = (-48, -24, -4, 0, 24)
OVERDUE_REPEAT_INTERVAL_HOURS = 24
EXPIRY_LOOKAHEAD_DAYS = 60

REMINDER_TYPE_DOCUMENT_EXPIRY = "document_expiry"
REMINDER_TYPE_DOCUMENT_WORKFLOW_STEP = "document_workflow_step"
_DOCUMENT_WORKFLOW_TERMINAL_STATUSES = frozenset(
    {
        "approved",
        "completed",
        "delivered",
        "received",
        "verified",
        "issued",
        "registered",
        "active",
    }
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _plural_days(value: int) -> str:
    value = abs(value)
    if value % 10 == 1 and value % 100 != 11:
        return "день"
    if 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return "дня"
    return "дней"


def _expiry_offset_hours(document: Document) -> Tuple[List[int], Optional[int]]:
    defaults = get_doc_type_defaults(getattr(document, "doc_type", None))

    offsets: Set[int] = set(DEFAULT_EXPIRY_OFFSET_HOURS)

    doc_specific = getattr(document, "reminder_days_before", None)
    if doc_specific not in (None, ""):
        try:
            hours = -abs(int(doc_specific)) * 24
            offsets.add(hours)
        except (TypeError, ValueError):
            pass

    expiry_rule = getattr(defaults, "expiry_rule", {}) or {}
    rule_days = expiry_rule.get("reminders_days")
    if isinstance(rule_days, Iterable):
        for candidate in rule_days:
            try:
                day_value = int(candidate)
            except (TypeError, ValueError):
                continue
            offsets.add(-abs(day_value) * 24)

    offsets = {offset for offset in offsets if offset <= OVERDUE_REPEAT_INTERVAL_HOURS}
    offsets.add(OVERDUE_REPEAT_INTERVAL_HOURS)

    return sorted(offsets), OVERDUE_REPEAT_INTERVAL_HOURS


def _expiry_schedule_key(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    if not payload:
        return None
    key = payload.get("schedule_key")
    if key is not None:
        key_str = str(key).strip()
        if not key_str:
            return None
        if key_str.startswith("expiry:"):
            key_str = key_str.replace("expiry:", "document_expiry:", 1)
        elif not key_str.startswith("document_expiry:"):
            if key_str[0] in {"+", "-"} or key_str.isdigit():
                key_str = f"document_expiry:{key_str}"
        return key_str
    offset: Optional[int] = None
    if "offset_hours" in payload:
        try:
            offset = int(payload["offset_hours"])
        except (TypeError, ValueError):
            return None
    if offset is None and "offset_days" in payload:
        try:
            hours = int(payload["offset_days"]) * 24
            offset = hours
        except (TypeError, ValueError):
            return None
    if offset is None:
        return None
    if offset > 0:
        suffix = f"+{offset}"
    elif offset == 0:
        suffix = "0"
    else:
        suffix = str(offset)
    return f"document_expiry:{suffix}"


def _format_expiry_message(doc_label: str, expires_at: datetime, offset_hours: int) -> str:
    date_str = expires_at.date().isoformat()
    if offset_hours < 0:
        remaining_hours = -offset_hours
        if remaining_hours % 24 == 0:
            days = remaining_hours // 24
            return (
                f"Документ '{doc_label}' истекает {date_str} "
                f"(осталось {days} {_plural_days(days)})."
            )
        return (
            f"Документ '{doc_label}' истекает {date_str} "
            f"(осталось {remaining_hours} ч)."
        )
    if offset_hours == 0:
        return f"Документ '{doc_label}' истекает сегодня ({date_str})."
    overdue_hours = offset_hours
    if overdue_hours % 24 == 0:
        days = overdue_hours // 24
        return (
            f"Документ '{doc_label}' просрочен на {days} {_plural_days(days)} "
            f"(дата {date_str})."
        )
    return (
        f"Документ '{doc_label}' просрочен на {overdue_hours} ч "
        f"(дата {date_str})."
    )


async def cancel_entity_reminders(
    db: AsyncSession,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
) -> None:
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
            Reminder.status.notin_([ReminderStatus.cancelled, ReminderStatus.done]),
        )
    )
    now = _now_utc()
    for reminder in rows.scalars():
        reminder.status = ReminderStatus.done
        reminder.completed_at = now


async def cancel_document_step_reminders(
    db: AsyncSession,
    tenant_id: str,
    document_id: str,
) -> None:
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "document_step",
            Reminder.entity_id.like(f"{document_id}:%"),
            Reminder.status.notin_([ReminderStatus.cancelled, ReminderStatus.done]),
        )
    )
    now = _now_utc()
    for reminder in rows.scalars():
        reminder.status = ReminderStatus.done
        reminder.completed_at = now


async def schedule_document_expiry_reminders(
    db: AsyncSession,
    tenant_id: str,
    document: Document,
) -> None:
    if not getattr(document, "id", None):
        return

    existing_rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "document",
            Reminder.entity_id == str(document.id),
        )
    )
    existing: Dict[str, Reminder] = {}
    for reminder in existing_rows.scalars():
        key = _expiry_schedule_key(reminder.payload or {})
        if key:
            existing[key] = reminder

    expires_at = getattr(document, "expire_date", None)
    if not expires_at:
        expires_at = getattr(document, "expires_at", None)
    if expires_at is None:
        for reminder in existing.values():
            if reminder.status not in (ReminderStatus.cancelled, ReminderStatus.done):
                reminder.status = ReminderStatus.done
                reminder.completed_at = _now_utc()
        await _schedule_workflow_step_reminders(db, tenant_id, document)
        return

    if isinstance(expires_at, date) and not isinstance(expires_at, datetime):
        expires_dt = datetime.combine(expires_at, datetime.min.time(), tzinfo=timezone.utc)
    elif isinstance(expires_at, datetime):
        expires_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    else:
        await _schedule_workflow_step_reminders(db, tenant_id, document)
        return

    now = _now_utc()
    offset_hours_list, repeat_interval = _expiry_offset_hours(document)
    now = _now_utc()
    doc_label = (
        getattr(document, "custom_name", None)
        or getattr(document, "type", None)
        or getattr(document, "doc_type", None)
        or getattr(document, "key", "document")
    )
    interval_td = (
        timedelta(hours=int(repeat_interval))
        if repeat_interval and repeat_interval > 0
        else None
    )

    for offset_hours in offset_hours_list:
        due_at = expires_dt + timedelta(hours=offset_hours)
        if offset_hours < 0 and due_at < now:
            due_at = now
        if offset_hours == 0 and due_at < now:
            due_at = now
        if offset_hours > 0:
            if interval_td:
                while due_at < now:
                    due_at += interval_td
            elif due_at < now:
                continue

        if offset_hours > 0:
            key_suffix = f"+{offset_hours}"
        elif offset_hours == 0:
            key_suffix = "0"
        else:
            key_suffix = str(offset_hours)
        key = f"document_expiry:{key_suffix}"
        template = get_document_expiry_template(int(offset_hours))
        channel_templates: Dict[str, Dict[str, Any]] = {}
        locale_keys: Set[str] = set()
        for channel_def in iter_channel_templates(template):
            channel_templates[channel_def.channel] = {
                "template_key": channel_def.template_key,
                "subject_key": channel_def.subject_key,
                "body_key": channel_def.body_key,
                "default_subject": channel_def.default_subject,
                "default_body": channel_def.default_body,
            }
            for lk in (
                channel_def.template_key,
                channel_def.subject_key,
                channel_def.body_key,
            ):
                if lk:
                    locale_keys.add(lk)
        payload: Dict[str, Any] = {
            "document_id": str(document.id),
            "candidate_id": getattr(document, "candidate_id", None),
            "offset_hours": offset_hours,
            "schedule_key": key,
            "template_slug": template.slug,
            "event_type": template.event_type,
            "channel_templates": channel_templates,
            "template_metadata": dict(template.metadata or {}),
            "localization_keys": sorted(locale_keys),
        }
        payload["template_context"] = {
            "candidate_id": getattr(document, "candidate_id", None),
            "document_id": str(document.id),
            "document_name": doc_label,
        }
        if offset_hours % 24 == 0:
            payload["offset_days"] = offset_hours // 24
        if interval_td and offset_hours > 0:
            payload["repeat_interval_hours"] = int(interval_td.total_seconds() // 3600)

        msg = _format_expiry_message(doc_label, expires_dt, offset_hours)
        reminder = existing.pop(key, None)
        if reminder:
            reminder.due_at = due_at
            reminder.status = ReminderStatus.pending
            reminder.sent_at = None
            reminder.cancelled_at = None
            reminder.message = msg
            reminder.payload = payload
        else:
            db.add(
                Reminder(
                    tenant_id=tenant_id,
                    type=REMINDER_TYPE_DOCUMENT_EXPIRY,
                    entity_type="document",
                    entity_id=str(document.id),
                    due_at=due_at,
                    status=ReminderStatus.pending,
                    message=msg,
                    payload=payload,
                )
            )

    for reminder in existing.values():
        if reminder.status not in (ReminderStatus.cancelled, ReminderStatus.done):
            reminder.status = ReminderStatus.done
            reminder.completed_at = now

    await _schedule_workflow_step_reminders(db, tenant_id, document)


async def _schedule_workflow_step_reminders(
    db: AsyncSession,
    tenant_id: str,
    document: Document,
) -> None:
    document_id = str(getattr(document, "id", ""))
    if not document_id:
        return

    deadlines = list(iter_workflow_step_deadlines(getattr(document, "workflow", None)))
    existing_rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "document_step",
            Reminder.entity_id.like(f"{document_id}:%"),
        )
    )
    existing: Dict[str, Reminder] = {
        reminder.entity_id: reminder for reminder in existing_rows.scalars()
    }

    now = _now_utc()
    raw_status = getattr(document, "status", None)
    doc_status = (
        str(getattr(raw_status, "value", raw_status) or "").strip().lower()
    )
    if doc_status in _DOCUMENT_WORKFLOW_TERMINAL_STATUSES:
        for reminder in existing.values():
            if reminder.status not in (ReminderStatus.cancelled, ReminderStatus.done):
                reminder.status = ReminderStatus.done
                reminder.completed_at = now
        return

    doc_type = getattr(document, "type", None) or getattr(document, "doc_type", "document")
    workflow_payload = getattr(document, "workflow", {}) or {}
    steps_payload = workflow_payload.get("steps") if isinstance(workflow_payload, dict) else None
    for step_code, due_at in deadlines:
        entity_id = f"{document_id}:{step_code}"
        payload = {
            "document_id": document_id,
            "candidate_id": getattr(document, "candidate_id", None),
            "step_code": step_code,
        }
        step_title = step_code
        if isinstance(steps_payload, Iterable):
            for entry in steps_payload:
                if isinstance(entry, dict) and entry.get("code") == step_code:
                    step_title = entry.get("title") or step_code
                    break
        message = (
            f"Шаг '{step_title}' по документу '{doc_type}' "
            f"должен быть выполнен до {due_at.date()}."
        )
        reminder = existing.pop(entity_id, None)
        if reminder:
            reminder.due_at = due_at
            reminder.status = ReminderStatus.pending
            reminder.sent_at = None
            reminder.cancelled_at = None
            reminder.message = message
            reminder.payload = payload
        else:
            db.add(
                Reminder(
                    tenant_id=tenant_id,
                    type=REMINDER_TYPE_DOCUMENT_WORKFLOW_STEP,
                    entity_type="document_step",
                    entity_id=entity_id,
                    due_at=due_at,
                    status=ReminderStatus.pending,
                    message=message,
                    payload=payload,
                )
            )

    for reminder in existing.values():
        if reminder.status not in (ReminderStatus.cancelled, ReminderStatus.done):
            reminder.status = ReminderStatus.done
            reminder.completed_at = now


async def run_expiry_notifications(
    db: AsyncSession, tenant_id: str
) -> Tuple[int, int]:
    """
    Возвращает: (сколько документов просмотрено, сколько уведомлений отправлено)
    """
    await refresh_documents_overdue_metrics(db, tenant_id)
    now = _now_utc()
    horizon = now + timedelta(days=EXPIRY_LOOKAHEAD_DAYS)

    rows = await db.execute(
        select(Reminder, Document, Candidate)
        .join(
            Document,
            and_(
                Document.id == Reminder.entity_id,
                Document.tenant_id == Reminder.tenant_id,
                Reminder.entity_type == "document",
            ),
        )
        .join(Candidate, Candidate.id == Document.candidate_id)
        .where(
            and_(
                Reminder.tenant_id == tenant_id,
                Reminder.type == REMINDER_TYPE_DOCUMENT_EXPIRY,
                Reminder.status == ReminderStatus.pending,
                Reminder.due_at <= horizon,
                Candidate.deleted_at.is_(None),
            )
        )
        .order_by(Reminder.due_at.asc())
    )
    sent = 0
    seen = 0
    for reminder, doc, cand in rows.all():
        seen += 1
        expires_raw = (
            getattr(doc, "expire_date", None) or getattr(doc, "expires_at", None)
        )
        expires_dt: Optional[datetime] = None
        if isinstance(expires_raw, datetime):
            expires_dt = (
                expires_raw if expires_raw.tzinfo else expires_raw.replace(tzinfo=timezone.utc)
            )
        elif isinstance(expires_raw, date):
            expires_dt = datetime.combine(expires_raw, datetime.min.time(), tzinfo=timezone.utc)

        days_left: Optional[int] = None
        if expires_dt:
            days_left = (expires_dt.date() - date.today()).days

        payload = reminder.payload or {}
        offset_hours: Optional[int] = None
        if "offset_hours" in payload:
            try:
                offset_hours = int(payload["offset_hours"])
            except (TypeError, ValueError):
                offset_hours = None
        if offset_hours is None and "offset_days" in payload:
            try:
                offset_hours = int(payload["offset_days"]) * 24
            except (TypeError, ValueError):
                offset_hours = None
        if offset_hours is None and days_left is not None:
            offset_hours = days_left * 24

        template_slug = payload.get("template_slug")
        template = get_notification_template(template_slug) if template_slug else None
        if template is None and offset_hours is not None:
            template = get_document_expiry_template(offset_hours)
            payload["template_slug"] = template.slug
        if template:
            if not payload.get("channel_templates"):
                channel_templates: Dict[str, Dict[str, Any]] = {}
                locale_keys: Set[str] = set()
                for channel_def in iter_channel_templates(template):
                    channel_templates[channel_def.channel] = {
                        "template_key": channel_def.template_key,
                        "subject_key": channel_def.subject_key,
                        "body_key": channel_def.body_key,
                        "default_subject": channel_def.default_subject,
                        "default_body": channel_def.default_body,
                    }
                    for lk in (
                        channel_def.template_key,
                        channel_def.subject_key,
                        channel_def.body_key,
                    ):
                        if lk:
                            locale_keys.add(lk)
                payload["channel_templates"] = channel_templates
                payload["localization_keys"] = sorted(locale_keys)
            payload.setdefault("template_metadata", dict(template.metadata or {}))
            payload.setdefault("event_type", template.event_type)
        channel_templates_payload: Dict[str, Any] = payload.setdefault("channel_templates", {}) or {}

        doc_type = (
            getattr(doc, "custom_name", None)
            or getattr(doc, "type", None)
            or getattr(doc, "doc_type", None)
            or getattr(doc, "key", "document")
        )
        expires_for_message = expires_dt or reminder.due_at or now

        candidate_first = (getattr(cand, "first_name", None) or "").strip()
        candidate_last = (getattr(cand, "last_name", None) or "").strip()
        candidate_full_name = (f"{candidate_first} {candidate_last}").strip() or candidate_first or candidate_last
        template_context: Dict[str, Any] = {
            "candidate_name": candidate_full_name,
            "candidate_id": getattr(cand, "id", None),
            "document_name": doc_type,
            "document_id": getattr(doc, "id", None),
            "expires_at": expires_for_message.isoformat(),
        }
        if offset_hours is not None:
            template_context["offset_hours"] = offset_hours
            if offset_hours % 24 == 0:
                template_context["offset_days"] = offset_hours // 24
        payload["template_context"] = template_context

        subject: str
        if offset_hours is None:
            subject = f"📄 Напоминание по документу '{doc_type}'"
        elif offset_hours < 0:
            remaining = -offset_hours
            if remaining % 24 == 0:
                days = remaining // 24
                subject = f"📄 Документ '{doc_type}' истекает через {days} {_plural_days(days)}"
            else:
                subject = f"📄 Документ '{doc_type}' истекает через {remaining} ч"
        elif offset_hours == 0:
            subject = f"📄 Документ '{doc_type}' истекает сегодня"
        else:
            if offset_hours % 24 == 0:
                days = offset_hours // 24
                subject = f"⚠️ Документ '{doc_type}' просрочен на {days} {_plural_days(days)}"
            else:
                subject = f"⚠️ Документ '{doc_type}' просрочен на {offset_hours} ч"

        message_line = _format_expiry_message(doc_type, expires_for_message, offset_hours or 0)
        text_lines = [
            message_line,
            "",
            f"Кандидат: {candidate_full_name}",
            f"Документ: {doc_type}",
            f"Срок действия до: {expires_for_message.date().isoformat()}",
        ]
        if offset_hours is not None:
            text_lines.append(f"Сдвиг напоминания: {offset_hours} ч от даты истечения")
        text_lines.append("")
        text_lines.append(
            "Как продлить: см. справку (Документы → Детали) или обратитесь в отдел документооборота."
        )
        text = "\n".join(text_lines)

        if offset_hours == 0 and getattr(cand, "stage", None) != "docs_wait":
            try:
                await db.execute(
                    update(Candidate)
                    .where(Candidate.id == cand.id)
                    .values(stage="docs_wait", updated_at=datetime.utcnow())
                )
                await db.commit()
                cand.stage = "docs_wait"
                try:
                    await sync_candidate_links(
                        db=db,
                        tenant_id=UUID(tenant_id),
                        candidate_id=UUID(cand.id),
                        candidate_stage="docs_wait",
                    )
                except Exception:
                    # не валим процесс напоминаний из-за ошибок синка
                    pass
            except Exception:
                await db.rollback()

        # кому слать: менеджеру и самому кандидату, если у него есть email
        targets = []
        if getattr(cand, "manager", None):
            targets.append(str(cand.manager))
        if getattr(cand, "email", None):
            targets.append(str(cand.email))

        for to in targets:
            if not to:
                continue
            channel_key = "email" if "@" in to else "webhook"
            channel_info = {}
            if isinstance(channel_templates_payload, dict):
                channel_info = channel_templates_payload.get(channel_key) or {}
                if not channel_info and channel_key == "webhook":
                    channel_info = channel_templates_payload.get("webhook") or {}
            notify_channels: Optional[List[str]] = [channel_key] if channel_key else None
            template_key_for_target = None
            if isinstance(channel_info, dict):
                template_key_for_target = channel_info.get("template_key")
            try:
                await notify(
                    to=to,
                    subject=subject,
                    text=text,
                    template_key=template_key_for_target,
                    template_context=template_context,
                    channels=notify_channels,
                )
                sent += 1
            except Exception:
                # не валим всю процедуру
                continue

        reminder.status = ReminderStatus.sent
        reminder.sent_at = _now_utc()
        reminder.message = reminder.message or text
        reminder_payload = dict(payload)
        reminder_payload.setdefault("template_context", template_context)
        reminder.payload = reminder_payload
        severity_value = (
            ((payload.get("template_metadata") or {}).get("severity"))
            or payload.get("severity")
            or "info"
        )
        increment_reminder_triggered(tenant_id, reminder.type, str(severity_value))

    step_rows = await db.execute(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.type == REMINDER_TYPE_DOCUMENT_WORKFLOW_STEP,
            Reminder.status == ReminderStatus.pending,
            Reminder.due_at <= horizon,
        )
        .order_by(Reminder.due_at.asc())
    )
    step_reminders: List[Reminder] = step_rows.scalars().all()
    if step_reminders:
        doc_ids: Set[str] = set()
        for reminder in step_reminders:
            entity_id = reminder.entity_id or ""
            if ":" in entity_id:
                doc_ids.add(entity_id.split(":", 1)[0])

        docs_map: Dict[str, Document] = {}
        candidates_map: Dict[str, Candidate] = {}
        if doc_ids:
            documents_rows = await db.execute(
                select(Document).where(
                    Document.tenant_id == tenant_id,
                    Document.id.in_(doc_ids),
                    Document.deleted_at.is_(None),
                )
            )
            docs_map = {str(doc.id): doc for doc in documents_rows.scalars()}

            candidate_ids = {doc.candidate_id for doc in docs_map.values() if doc.candidate_id}
            if candidate_ids:
                candidates_rows = await db.execute(
                    select(Candidate).where(
                        Candidate.id.in_(candidate_ids),
                        Candidate.deleted_at.is_(None),
                    )
                )
                candidates_map = {str(cand.id): cand for cand in candidates_rows.scalars()}

        for reminder in step_reminders:
            entity_id = reminder.entity_id or ""
            if ":" not in entity_id:
                continue
            doc_id, step_code = entity_id.split(":", 1)
            doc = docs_map.get(doc_id)
            if not doc:
                continue
            cand = candidates_map.get(doc.candidate_id)
            if not cand:
                continue

            seen += 1

            workflow = getattr(doc, "workflow", {}) or {}
            step_title = step_code
            steps = workflow.get("steps")
            if isinstance(steps, Iterable):
                for step in steps:
                    if isinstance(step, dict) and step.get("code") == step_code:
                        step_title = step.get("title") or step_code
                        break

            due_date = reminder.due_at.date()
            days_left = (due_date - date.today()).days
            doc_type = getattr(doc, "doc_type", None) or getattr(doc, "type", "document")
            subject = f"⚙️ Шаг '{step_title}' по документу '{doc_type}' до {due_date}"
            text = (
                f"Кандидат: {cand.first_name} {cand.last_name}\n"
                f"Документ: {doc_type}\n"
                f"Шаг: {step_title}\n"
                f"Крайний срок: {due_date} (осталось {days_left} дн.)\n\n"
                "Проверьте детали workflow в карточке документов."
            )

            targets = []
            if getattr(cand, "manager", None):
                targets.append(str(cand.manager))
            if getattr(cand, "email", None):
                targets.append(str(cand.email))

            deliveries = 0
            for to in targets:
                try:
                    await notify(to=to, subject=subject, text=text)
                    sent += 1
                    deliveries += 1
                except Exception:
                    continue

            reminder.status = ReminderStatus.sent
            reminder.sent_at = _now_utc()
            reminder.message = reminder.message or text
            if deliveries == 0:
                reminder.message = text
            increment_reminder_triggered(tenant_id, reminder.type, "info")

    await db.commit()
    return seen, sent
