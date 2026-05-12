# Reminders/Notifications Rework (MVP → Full)

> **STATUS: SUPERSEDED** by [`../architecture/ADR-012-activity-notification-operating-layer.md`](../architecture/ADR-012-activity-notification-operating-layer.md) и [`../architecture/activity-notification-operating-layer.md`](../architecture/activity-notification-operating-layer.md). Целевая архитектура «один operational layer» (Activity + Notification) заменяет предложения этого документа: `Reminder` — поведение Activity (поле `reminder_at`), а не отдельная таблица; CRUD ушёл на `/api/v1/activities`. Phase 2.1 (2026-05-09) поглотила `candidate_tasks` и `communication_planner_events`. Сохранено как археология решения; **не использовать** как источник истины.

Цель: полноценные персональные напоминания/уведомления с понятным текстом, временем, контекстом (кандидат/документ/вакансия), ACL и доставкой во внутреннюю ленту (+ pop-up), с дефолтным смещением 15 минут и закладкой recurrence/snooze.

## Данные
- `reminders` (расширить существующую таблицу):
  - id, tenant_id, owner_id (creator), assignee_id, title, description, type, priority (low/normal/high), channel (`internal` на первом этапе), status (`new/pending/done/overdue/cancelled`), due_at, remind_at, snoozed_until, completed_at, recurrence_json (RRULE light), entity_type (`candidate/document/vacancy/custom`), entity_id, payload (context), created_at, updated_at, cancelled_at.
  - Индексы: (tenant_id, assignee_id, remind_at), (tenant_id, assignee_id, due_at), (tenant_id, entity_type, entity_id), (tenant_id, status, due_at).
- `reminder_events`: id, reminder_id, tenant_id, event_type (`created/assigned/updated/sent/overdue/snoozed/completed/read`), payload JSON, created_at.
- `user_notifications` (уже есть) использовать как ленту доставки. Типы событий: `reminder_due`, `reminder_overdue`, `reminder_assigned`, `reminder_updated`.

## ACL / RLS
- Видимость: автор, ассайн, их руководитель, админ tenant. Всегда фильтруем по tenant_id.
- Операции: создавать/редактировать/завершать может автор или ассайн; админ/руководитель могут reasssign/complete/snooze.

## API v1 (новые/расширенные)
- `POST /api/v1/reminders` — создать (title, description?, due_at, remind_at?, assignee_id?, priority?, channel=internal, entity_type/id?, recurrence_json?).
- `GET /api/v1/reminders` — фильтры: status, due_from/to, assignee_id, entity_type/id, overdue_only, mine_only.
- `PATCH /api/v1/reminders/{id}` — изменить времена/текст/assignee/priority/channel.
- `POST /api/v1/reminders/{id}/complete` — пометить выполненным (опц. completed_at).
- `POST /api/v1/reminders/{id}/snooze` — тело: minutes или new_remind_at; сдвигает remind_at, ставит status=pending, пишет event.
- `GET /api/v1/notifications` — как сейчас, но добавляем фильтр по `type in [reminder_*]` и `unread_only`.
- `POST /api/v1/notifications/read` — помечает прочитанными (есть).

## Бизнес-правила
- Создание: если remind_at не задан → `due_at - 15m` (но не в прошлом, тогда now). owner=actor; assignee=body.assignee_id or actor.
- Доставка: worker берёт pending/new где `remind_at <= now`, создаёт `user_notifications` (event_type в зависимости от статуса: due/assigned/updated), не меняет status (остается pending) пока не complete/overdue.
- Overdue: отдельный worker помечает `overdue` если `now > due_at` и не done/cancelled; создаёт `user_notification` (`reminder_overdue`), событие в `reminder_events`.
- Snooze: переносит `remind_at` и `snoozed_until`, статус → pending, event `snoozed`.
- Recurrence: храним RRULE light (`{"freq":"daily|weekly|custom","interval":1,"byweekday":[1,3], "count":null}`); при `complete` создаём следующий reminder с пересчитанными due/remind (remind_at = due_at - offset, offset по умолчанию 15m).
- Quiet hours: предусмотреть поля в профиле (пока опущено, но код воркера должен уважать "не раньше X / не позже Y" если появится).

## Workers / задачи
- `reminder_delivery`: каждые N минут, берёт pending/new `remind_at <= now`, пишет `user_notifications`, логирует `reminder_events`.
- `reminder_overdue`: каждые N минут, помечает overdue, шлёт `user_notifications`.
- Планировщик recurrence: при `complete` создаёт следующую — без отдельного cron.

## UI (первый этап, без email)
- Глобальный колокольчик: лента `user_notifications` с группировкой по типу, быстрые действия: mark read, go-to entity, snooze +15m, complete.
- Страница “Мои напоминания”: фильтры (status, due range, entity, assignee=me/all), представления список + календарь. Карточка напоминания: title, due/remind, entity chips, priority, assignee, actions (complete/snooze/edit).
- Карточка кандидата/документа: секция “Напоминания” со списком связанных; форма создания (title/description, due/remind picker, assignee selector, priority, recurrence dropdown daily/weekly/none). Бейджи статуса (pending/overdue/done).
- Pop-up: на доставку `reminder_due|overdue` показываем toasts с CTA (open/complete/snooze 15m).

## Минимальная реализация (MVP)
1) Миграция `reminders` (+ поля, индексы) и создание `reminder_events`.
2) Сервис `reminders.py`: CRUD, расчет remind_at (default 15m), snooze, complete, recurrence (daily/weekly/custom), ACL guard.
3) Worker-процедуры: delivery → `user_notifications`, overdue marker.
4) API слой v1 под контракты выше.
5) UI: обновить RemindersPage → “My reminders” с фильтрами/действиями; секции в Candidate/Document карточках (список + create inline); колокольчик/тосты.

## Вопросы закрыты
- Каналы на старт: только `internal` (feed + pop-up).
- Дефолтное смещение: 15 минут до due_at (можно задать своё).
- Recurrence/snooze: закладываем сразу (RRULE light, snooze endpoint).
